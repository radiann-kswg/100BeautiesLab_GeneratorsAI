"""
sdxl/prompt_map.py — Stage 1 プロンプト / DB レコード → SDXL タグ列変換
Copyright © RadianN_kswg — CC BY-NC 4.0

作風LoRA (nt-corefolder) は WD14 タグで学習されているため、
自然文プロンプトではなく「trigger word + タグ列」に変換して渡す。
定義色 (DB の color_palette) は hex → 基本色タグへ近似変換して自動注入する。
"""

from __future__ import annotations

# LoRA 学習時のトリガーワード (形態別)。v1 はコアフォルダのみ。
TRIGGER_WORDS: dict[str, str] = {
    "corefolder": "nt-corefolder",
}

# 学習データセットのタグ体系に合わせた既定タグ (assets/lora/samples/prompts.txt 準拠)
_DEFAULT_POSITIVE = [
    "solo",
    "animalization",
    "fox ears",
    "multiple tails",
    "full body",
    "flat color",
    "simple background",
    "white background",
]

DEFAULT_NEGATIVE = (
    "lowres, bad anatomy, worst quality, low quality, jpeg artifacts, "
    "signature, watermark, text, blurry"
)

# hex → WD14 系基本色語への近似マップ用アンカー (hue ベース)
_COLOR_ANCHORS: list[tuple[str, tuple[int, int, int]]] = [
    ("black", (25, 25, 25)),
    ("white", (240, 240, 240)),
    ("grey", (128, 128, 128)),
    ("red", (210, 40, 40)),
    ("orange", (235, 130, 40)),
    ("yellow", (235, 210, 60)),
    ("blonde", (240, 214, 128)),
    ("green", (60, 170, 80)),
    ("blue", (60, 100, 210)),
    ("purple", (140, 70, 190)),
    ("pink", (240, 140, 180)),
    ("brown", (130, 85, 50)),
]

# applies_to / role の部位語 → タグ語尾
# コアフォルダ形態は髪・瞳ではなく胴体部位 (arm/foot/chest 等) のパレットを持つため、
# 部位語をそのまま色タグの名詞に使う (例: "yellow arms", "blue chest")。
_PART_TAG_SUFFIX: dict[str, str] = {
    "hair": "hair",
    "髪": "hair",
    "eye": "eyes",
    "eyes": "eyes",
    "瞳": "eyes",
    "arm": "arms",
    "foot": "feet",
    "leg": "legs",
    "chest": "chest",
    "body": "body",
    "tail": "tails",
    "ear": "ears",
}


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int] | None:
    text = (hex_str or "").strip().lstrip("#")
    if len(text) != 6:
        return None
    try:
        return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return None


def _nearest_color_word(hex_str: str) -> str | None:
    rgb = _hex_to_rgb(hex_str)
    if rgb is None:
        return None
    best: tuple[int, str] | None = None
    for word, anchor in _COLOR_ANCHORS:
        dist = sum((a - b) ** 2 for a, b in zip(rgb, anchor))
        if best is None or dist < best[0]:
            best = (dist, word)
    return best[1] if best else None


def palette_to_tags(record: dict, form: str, limit: int = 4) -> list[str]:
    """DB の color_palette から `blonde hair` / `orange eyes` 等の色タグを作る。

    部位が hair/eyes 系のエントリのみタグ化する (胴体色などは LoRA 側の作風に任せる)。
    """
    try:
        from src.utils.dataset import extract_color_palette
    except ImportError:
        return []
    tags: list[str] = []
    for entry in extract_color_palette(record, form)[: limit * 2]:
        applies = [str(a).lower() for a in (entry.get("applies_to") or [])]
        role = str(entry.get("role_ja") or "").lower()
        suffix = None
        for key, tag_suffix in _PART_TAG_SUFFIX.items():
            if any(key in a for a in applies) or key in role:
                suffix = tag_suffix
                break
        if not suffix:
            continue
        word = _nearest_color_word(entry.get("hex", ""))
        if not word:
            continue
        if word == "blonde" and suffix != "hair":
            word = "yellow"  # blonde は髪専用の色語のため、他部位は yellow へ丸める
        tag = f"{word} {suffix}"
        if tag not in tags:
            tags.append(tag)
        if len(tags) >= limit:
            break
    return tags


def build_sdxl_prompt(
    record: dict,
    form: str,
    scene_tags: str = "",
    extra_tags: "list[str] | None" = None,
) -> tuple[str, str]:
    """SDXL 用 (positive, negative) プロンプトを構築する。

    Parameters
    ----------
    record:     キャラクターレコード (find_character の返却値)
    form:       形態。v1 は "corefolder" のみ対応
    scene_tags: シーンのタグ列 or 短い英語句 (例: "reading a book, library")
    extra_tags: 追加タグ (呼び出し側での上書き用)

    Raises
    ------
    ValueError: 未対応形態 (LoRA が存在しない) の場合
    """
    trigger = TRIGGER_WORDS.get(form)
    if not trigger:
        raise ValueError(
            f"form={form!r} の作風LoRAは未学習です (対応形態: {sorted(TRIGGER_WORDS)})"
        )

    parts: list[str] = [trigger]
    parts.extend(_DEFAULT_POSITIVE)
    parts.extend(palette_to_tags(record, form))
    if extra_tags:
        parts.extend(t for t in extra_tags if t and t not in parts)
    if scene_tags:
        parts.append(scene_tags.strip())

    # 重複除去 (順序維持)
    seen: set[str] = set()
    deduped = [p for p in parts if not (p in seen or seen.add(p))]
    return ", ".join(deduped), DEFAULT_NEGATIVE


__all__ = ["build_sdxl_prompt", "palette_to_tags", "TRIGGER_WORDS", "DEFAULT_NEGATIVE"]
