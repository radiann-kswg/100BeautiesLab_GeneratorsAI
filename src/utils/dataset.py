"""
utils/dataset.py — manifest-training.jsonl からキャラクターデータを読み込むユーティリティ
Copyright © RadianN_kswg — CC BY-NC 4.0
"""

from __future__ import annotations

import json
import importlib
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any


def _append_unique(values: list[str], value: Any) -> None:
    if not isinstance(value, str):
        return
    text = value.strip()
    if text and text not in values:
        values.append(text)


def _sanitize_natural_language_description(text: Any) -> str:
    """翻訳指示のメタ文言を除去し、モデルに渡す説明文を安定化する。"""
    if not isinstance(text, str):
        return ""
    cleaned = text.strip()
    cleaned = re.sub(r"^\[TRANSLATE[^\]]*\]:\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def _infer_image_category(path_text: str) -> str:
    lower = path_text.replace("\\", "/").lower()
    parts = [p for p in lower.split("/") if p]
    for segment in parts:
        if segment == "cocneptalt":
            return "conceptalt"
        if segment in {"corefolder", "arts", "design", "designalt", "concept", "conceptalt"}:
            return segment
    return "other"


def _get_category_priority(form: str) -> dict[str, int]:
    if form == "humanoid":
        ordered = ["arts", "design", "designalt", "concept", "conceptalt"]
    else:
        ordered = ["corefolder", "design", "designalt", "arts", "concept", "conceptalt"]

    return {name: idx for idx, name in enumerate(ordered)}


def _get_db_priority(path_text: str) -> int:
    lower = path_text.replace("\\", "/").lower()
    db_order = ["db_primary", "db_semiprimary", "db_secondary", "db_selfsecondary"]
    for idx, db_name in enumerate(db_order):
        if f"/{db_name}/" in lower:
            return idx
    return len(db_order)


def _get_within_category_priority(path_text: str, form: str) -> int:
    """同カテゴリ内の細かい優先度を返す。小さいほど優先。"""
    lower = path_text.replace("\\", "/").lower()

    if form == "corefolder":
        if "/corefolder/" in lower:
            return 0
        if "/arts/corefolders/" in lower:
            return 1
    elif form == "humanoid":
        if "/arts/humanoids/" in lower:
            return 0
        if "/humanoid" in lower:
            return 1

    return 5


def _apply_form_reference_focus(paths: list[str], form: str) -> list[str]:
    """形態ごとの参照絞り込みを適用する。"""
    if form != "corefolder":
        return paths

    focused_primary: list[str] = []
    focused_fallback: list[str] = []
    for path in paths:
        category = _infer_image_category(path)
        lower = path.replace("\\", "/").lower()
        if category == "corefolder" or "/arts/corefolders/" in lower:
            _append_unique(focused_primary, path)
        elif category == "concept":
            _append_unique(focused_fallback, path)

    if focused_primary:
        return focused_primary
    if focused_fallback:
        return focused_fallback

    return paths


def _sort_paths_for_form(paths: list[str], form: str) -> list[str]:
    category_priority = _get_category_priority(form)
    ranked = sorted(
        enumerate(paths),
        key=lambda item: (
            category_priority.get(_infer_image_category(item[1]), len(category_priority)),
            _get_within_category_priority(item[1], form),
            _get_db_priority(item[1]),
            item[0],
        ),
    )
    return [path for _, path in ranked]


def _extract_work_dir_from_key(work_key: str) -> str:
    return work_key[1:] if work_key.startswith("#") else work_key


# corefolder 形態では人型衣装語をプロンプトの「現在形態の重点要素」に載せないようフィルタする。
# `_creations-ai` の outfit_features には humanoid 服飾語が混入している事例があり、
# そのまま prompt に入れると生成モデルが人型装を描いてしまう。
# 2026-06-09: 追加 (A2) — arm warmer / sock / shoe / high heel / bodysuit / armored /
# metallic leg / tunic / belt / cap / beret / hat / mask / hair ornament 系を捕捉し、
# 18 時バッチで観察された corefolder への humanoid 衣装混入を減らす。
_HUMANOID_OUTFIT_KEYWORDS: tuple[str, ...] = (
    # 既存（衣服・装飾の humanoid 専用語）
    "blazer", "shirt", "tshirt", "t-shirt", "shorts", "boots", "boot",
    "dress", "robe", "jacket", "uniform", "skirt", "pants", "trousers",
    "choker", "turtleneck", "sailor-collar", "sailor collar", "scarf",
    "necktie", "tie ", "stocking", "tights", "leggings", "coat", "sweater",
    "vest", "cardigan", "kimono", "hakama", "yukata", "gloves", "glove",
    "sash", "waist", "collar", "sleeve",
    # 追加 (2026-06-09 A2): 足回り・装甲・帽子・髪飾り・マスク
    "arm warmer", "leg warmer",
    "sock", "sneaker", "shoe", "high heel", "heels",
    "bodysuit", "body suit",
    "armored", "armor", "metallic leg", "leg element",
    "tunic", "belt",
    "cap ", "cap,", " cap", "beret", "messenger cap", "baseball cap",
    "hat ", " hat", "hat,",
    "mask",
    "hair ornament", "hair pin", "hairpin", "hair ribbon", "hair tie",
)

# silhouette_notes 内の各セグメントを判定する語彙。outfit_features より厳しく具体化し、
# 球体本体や色味の説明（"warmer coloring"等）を誤って削らないようにする。
_SILHOUETTE_HUMANOID_KEYWORDS: tuple[str, ...] = (
    "arm warmer", "leg warmer",
    "sock", "socks", "sneaker", "sneakers", "shoes", "shoe,",
    "high heel", "heels",
    "metallic leg", "leg element", "angular metallic",
    "armor plating", "armored bodysuit", "bodysuit", "body suit",
    "tunic",
    "human arm", "human leg", "human torso", "humanoid torso",
    "bare leg", "bare-leg", "bare legs",
    "thigh-high", "knee-high",
    "boots", "stocking", "tights",
    # 2026-06-09 (A3 追記): ヘアアクセ / ホログラム輪 など蛇足要素も silhouette_notes から外す。
    # 22(フジ) の "two small ornamental hair pins" / "circular halo-like hologram ring" を抑制。
    "hair pin", "hairpin", "hair ornament", "hair ribbon", "hair tie",
    "hologram ring", "halo-like hologram", "holographic ring",
)


def _filter_corefolder_outfit_features(features: list[str]) -> list[str]:
    """corefolder 形態の outfit_features から humanoid 服飾語を除外して返す。

    残すのは「番号 marking」「hood / shell / harness / core 系」を中心とした
    コアフォルダ記号要素だけ。フィルタ結果が空ならその旨を呼び出し側で処理する。
    """
    if not features:
        return []
    kept: list[str] = []
    for feature in features:
        if not isinstance(feature, str):
            continue
        text = feature.strip()
        if not text:
            continue
        lower = text.lower()
        if any(keyword in lower for keyword in _HUMANOID_OUTFIT_KEYWORDS):
            continue
        kept.append(text)
    return kept


def _filter_corefolder_silhouette_notes(notes: list[str]) -> list[str]:
    """corefolder の silhouette_notes から humanoid 衣装・四肢の節を除外する。

    silhouette_notes は "; " 区切りの文を持ちうるので、セグメント単位で判定し、
    残ったセグメントだけを再結合する。空になった note 自体は捨てる。
    主に新スキーマの `body_description` 側に適用する想定（強めのフィルタ）。
    """
    if not notes:
        return []
    kept_notes: list[str] = []
    for note in notes:
        if not isinstance(note, str):
            continue
        text = note.strip()
        if not text:
            continue
        segments = re.split(r"[;；]", text)
        kept_segments: list[str] = []
        for seg in segments:
            seg_text = seg.strip()
            if not seg_text:
                continue
            lower = seg_text.lower()
            if any(kw in lower for kw in _SILHOUETTE_HUMANOID_KEYWORDS):
                continue
            kept_segments.append(seg_text)
        if not kept_segments:
            continue
        kept_notes.append("; ".join(kept_segments))
    return kept_notes


# attached_items (新スキーマの装着アクセサリ) に対するゆるめのフィルタ。
# キャラ固有のティアラ・マスク・ネックレス・ホログラム輪などは「設定上の装飾」として残し、
# 明確な humanoid 衣装語（pants / dress / shoes / bodysuit など）だけを除外する。
# 2026-06-09 (A5): _creations-db addon-ai-tag の silhouette_notes object 化に対応。
_ATTACHED_ITEM_HUMANOID_KEYWORDS: tuple[str, ...] = (
    "pants", "trousers", "shorts", "skirt", "dress", "robe",
    "blazer", "shirt", "blouse", "jacket", "coat", "sweater",
    "vest", "cardigan", "uniform", "hoodie",
    "bodysuit", "body suit", "leotard",
    "shoes", "boots", "sneakers", "loafers", "high heels",
    "socks", "stockings", "tights", "leggings",
    "kimono", "hakama", "yukata",
    "human arms", "human legs", "human torso",
    "arm warmers", "leg warmers",
    "metallic leg", "armored leg",
)


def _filter_corefolder_attached_items(items: list[str]) -> list[str]:
    """corefolder の attached_items から明確な humanoid 衣装語のみ除外する。

    body_description より弱いフィルタ。キャラ固有装飾（tiara / crown / mask / necklace /
    hologram ring / hair accessory 等）はそのまま残す。
    """
    if not items:
        return []
    kept_items: list[str] = []
    for item in items:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text:
            continue
        segments = re.split(r"[;；]", text)
        kept_segments: list[str] = []
        for seg in segments:
            seg_text = seg.strip()
            if not seg_text:
                continue
            lower = seg_text.lower()
            if any(kw in lower for kw in _ATTACHED_ITEM_HUMANOID_KEYWORDS):
                continue
            kept_segments.append(seg_text)
        if not kept_segments:
            continue
        kept_items.append("; ".join(kept_segments))
    return kept_items


def _extract_silhouette_notes_for_prompt(
    form_data: dict[str, Any],
    form: str,
) -> tuple[list[str], list[str]]:
    """silhouette_notes を新旧両スキーマから (body, attached) のペアで取り出す。

    新スキーマ (`{body_description: [...], attached_items: [...]}`) と
    旧スキーマ (flat `[...]`) の両方に対応。corefolder の場合は
    `body_description` には強フィルタを、`attached_items` には弱フィルタを掛ける。
    """
    raw = form_data.get("silhouette_notes")
    body: list[str] = []
    attached: list[str] = []

    if isinstance(raw, dict):
        body = [
            str(x).strip()
            for x in (raw.get("body_description") or [])
            if str(x).strip()
        ]
        attached = [
            str(x).strip()
            for x in (raw.get("attached_items") or [])
            if str(x).strip()
        ]
    elif isinstance(raw, list):
        # 旧 array 形式は body_description として扱う（attached なし）。
        body = [str(x).strip() for x in raw if str(x).strip()]

    if form == "corefolder":
        body = _filter_corefolder_silhouette_notes(body)
        attached = _filter_corefolder_attached_items(attached)

    return body, attached


def _sanitize_corefolder_form_description(text: Any) -> str:
    """corefolder の natural_language_description から humanoid 衣装節を除去する。

    `_sanitize_natural_language_description` の上位互換。
    "Corefolder form: oversized coat over wide-leg pants, with the number '7' marked"
    のような文章を `,` `;` で分割し、humanoid 衣装語を含むセグメントだけ除外する。
    "Corefolder form:" のような形態プレフィックスは保持する。
    全セグメント除去された場合は球体型の汎用記述で補填し、空文字を返さない。
    """
    cleaned = _sanitize_natural_language_description(text)
    if not cleaned:
        return ""
    prefix_match = re.match(
        r"^(\s*corefolder form\s*[:：]?\s*)", cleaned, flags=re.IGNORECASE
    )
    if prefix_match:
        prefix = prefix_match.group(1)
        body = cleaned[prefix_match.end():]
    else:
        prefix = ""
        body = cleaned
    segments = re.split(r"[,，;；]", body)
    kept_segments: list[str] = []
    removed_any = False
    for seg in segments:
        seg_text = seg.strip().rstrip(".")
        if not seg_text:
            continue
        lower = seg_text.lower()
        if any(kw in lower for kw in _HUMANOID_OUTFIT_KEYWORDS):
            removed_any = True
            continue
        kept_segments.append(seg_text)
    if not removed_any:
        return cleaned
    if not kept_segments:
        fallback = (
            "a spherical cushion-like compact body in the character's signature color,"
            " with the number marking on the harness or front of the sphere"
        )
        return ((prefix or "Corefolder form: ") + fallback + ".").strip()
    rebuilt = ", ".join(kept_segments).strip()
    if not rebuilt.endswith("."):
        rebuilt += "."
    return ((prefix or "") + rebuilt).strip()


def _extract_face_features_for_corefolder(silhouette_features: list[str]) -> list[str]:
    """corefolder 形態でも有効な「顔/瞳」要素を silhouette_features から抽出する。

    corefolder は球体型で髪・耳・尻尾は持つが、blonde ponytail などの髪型指示は
    球体コアと矛盾するため通常は除外している。一方「瞳の色」「耳の種類」「尻尾の数」は
    顔パーツやアクセサリとして表現に効くため、それだけを再注入する。
    """
    if not silhouette_features:
        return []
    kept: list[str] = []
    for feature in silhouette_features:
        if not isinstance(feature, str):
            continue
        text = feature.strip()
        if not text:
            continue
        lower = text.lower()
        # 髪型・髪色のような hair/ponytail/braid を含む要素は corefolder に矛盾する。
        if any(banned in lower for banned in ("hair", "ponytail", "braid", "bun")):
            continue
        # 瞳色・耳・尻尾は corefolder の顔/種別記号としても有効。
        if any(keep in lower for keep in ("eye", "ears", "tail", "fang", "horn")):
            kept.append(text)
    return kept


def _looks_like_target_character(path_text: str, num_value: Any) -> bool:
    if num_value is None:
        return False

    token = str(num_value).strip().lower()
    if not token:
        return False

    lower = path_text.replace("\\", "/").lower()
    if token.isdigit():
        # 前後が数字でない場所にだけマッチさせる。
        # 例: token="22" のとき "/corefolder/22/" はマッチ、 "/corefolder/222/" はマッチさせない。
        # 注: f-string でも raw 接頭辞 (rf"") があれば \d はリテラルの数字メタ文字として渡る。
        return bool(re.search(rf"(?<!\d){re.escape(token)}(?!\d)", lower))
    return token in lower


def _is_path_compatible_with_form(path_text: str, form: str) -> bool:
    lower = path_text.replace("\\", "/").lower()

    # 参照資料・カタログ画像は作風誘導が強すぎるため除外する。
    if "/catalog/" in lower:
        return False

    if form == "corefolder":
        # humanoid 単独作品や humanoid アートは corefolder への作風誘導が強いため除外。
        if "/arts/humanoids/" in lower:
            return False
        if "-humanoid" in lower or "_humanoid" in lower:
            return False
    elif form == "humanoid":
        # corefolder 単独画像や corefolder アートは humanoid への誘導が強いため除外。
        if "/corefolder/" in lower:
            return False
        if "/arts/corefolders/" in lower:
            return False
        if "-corefolder" in lower or "_corefolder" in lower:
            return False

    return True


def _collect_forced_local_images(
    record: dict[str, Any],
    form: str,
    creations_db_base: str,
) -> list[str]:
    work_key = str(record.get("work_key") or "#Works_NumberTales")
    work_dir = _extract_work_dir_from_key(work_key)
    images_root = Path(creations_db_base) / "data" / work_dir / "Images"
    if not images_root.exists() or not images_root.is_dir():
        return []

    num_value = (record.get("data") or {}).get("Num")
    allowed_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    found: list[str] = []

    for path in images_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in allowed_suffixes:
            continue

        text = str(path)
        if not _is_path_compatible_with_form(text, form):
            continue
        if _looks_like_target_character(text, num_value):
            _append_unique(found, text)

    return found


# 公開URL → ローカルパス変換に使用する URL prefix。
# `_creations-db/` 配下に同じ相対パスでファイルが存在することを期待する。
# 2026-06-09 (A4): work_common.reference_images.{form}_reference[] は URL のみで保存されている
# ことが多いため、URL を見つけたらローカルパスにも変換を試みて Gemini に実バイトで渡せるようにする。
_URL_TO_LOCAL_PREFIXES: tuple[str, ...] = (
    "https://database.numbertales-radiann.net/",
    "http://database.numbertales-radiann.net/",
)


def _try_resolve_url_to_local_path(url: str, creations_db_base: str) -> str | None:
    """公開URLが既知の prefix なら、`_creations-db/` 配下の同名ファイルパスを返す。

    対応する prefix に該当しない URL や、ローカルにファイルが存在しない場合は ``None``。
    """
    for prefix in _URL_TO_LOCAL_PREFIXES:
        if url.startswith(prefix):
            rel = url[len(prefix):].lstrip("/")
            if not rel:
                return None
            candidate = Path(creations_db_base) / rel
            try:
                if candidate.exists():
                    return str(candidate)
            except OSError:
                return None
            return None
    return None


def _collect_work_common_reference_images(
    record: dict[str, Any],
    form: str,
    creations_db_base: str,
) -> tuple[list[str], list[str]]:
    """`ai_hints.work_common.reference_images.{form}_reference[]` から URL とローカルを収集する。

    作品共通の設計図 (`Ref_Glossary/concept-figure/cnsp-fg_*CoreFolder.png` 等) を想定する。
    キャラクター番号フィルタは通さない (作品共通リソースのため)。
    ローカル相対パスは ``_creations-db/`` 配下と仮定して絶対化する。
    2026-06-09 (A4): URL しか格納されていない場合でも、対応するローカルファイルが
    ``_creations-db/`` 配下に存在すれば ``locals_`` にも追加する。
    """
    hints = record.get("ai_hints") or {}
    work_common = hints.get("work_common") or {}
    ref_block = work_common.get("reference_images") or {}
    key = f"{form}_reference"
    raw = ref_block.get(key) or []
    if not isinstance(raw, list):
        return ([], [])

    urls: list[str] = []
    locals_: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text:
            continue
        if text.startswith(("http://", "https://")):
            if not _is_path_compatible_with_form(text, form):
                continue
            _append_unique(urls, text)
            # 同名のローカルファイルを併設できる場合はローカル添付対象にも追加する。
            local_candidate = _try_resolve_url_to_local_path(text, creations_db_base)
            if local_candidate and _is_path_compatible_with_form(local_candidate, form):
                _append_unique(locals_, local_candidate)
        else:
            path = str(Path(creations_db_base) / text)
            if _is_path_compatible_with_form(path, form):
                _append_unique(locals_, path)
    return (urls, locals_)


def collect_reference_images(
    record: dict[str, Any],
    form: str = "corefolder",
    creations_db_base: str = "_creations-db",
    max_images: int = 6,
) -> dict[str, list[str]]:
    """レコードから参照画像 URL とローカルパスを集約して返す。

    フィルタ方針：
      - 該当キャラクター本人の画像のみ (他キャラクターの装備・顔が混入しないよう ``_looks_like_target_character``)
      - 形態互換性 (``_is_path_compatible_with_form``)
      - カテゴリ优先順 (``_sort_paths_for_form``)
    """
    num_value = (record.get("data") or {}).get("Num")

    def _allow_path(path: str) -> bool:
        if not _is_path_compatible_with_form(path, form):
            return False
        # 該当キャラクター番号を含まないパスは他キャラクターの装備・顔が混入するため捨てる。
        if num_value is not None and not _looks_like_target_character(path, num_value):
            return False
        return True

    hints = record.get("ai_hints") or {}
    common = hints.get("common") or {}
    form_data = (hints.get("forms") or {}).get(form) or {}
    url_values: list[str] = []

    for value in (form_data.get("reference_images") or {}).values():
        if isinstance(value, str) and _allow_path(value):
            _append_unique(url_values, value)
    for value in (common.get("reference_images") or {}).values():
        if isinstance(value, str) and _allow_path(value):
            _append_unique(url_values, value)

    local_values: list[str] = []
    local_candidates: list[str] = []
    images_by_db = record.get("images") or {}
    if isinstance(images_by_db, dict):
        for db_name in ("DB_Primary", "DB_SemiPrimary", "DB_Secondary", "DB_SelfSecondary"):
            entries = images_by_db.get(db_name) or []
            if isinstance(entries, str):
                entries = [entries]
            if not isinstance(entries, list):
                continue
            for rel in entries:
                if not isinstance(rel, str):
                    continue
                path = str(Path(creations_db_base) / rel)
                if not _allow_path(path):
                    continue
                _append_unique(local_candidates, path)

    for forced_path in _collect_forced_local_images(record, form, creations_db_base):
        if _allow_path(forced_path):
            _append_unique(local_candidates, forced_path)

    ranked_candidates = _sort_paths_for_form(local_candidates, form)
    for path in ranked_candidates:
        _append_unique(local_values, path)

    url_values = _apply_form_reference_focus(url_values, form)
    local_values = _apply_form_reference_focus(local_values, form)
    url_values = _sort_paths_for_form(url_values, form)
    local_values = _sort_paths_for_form(local_values, form)

    # work_common (作品共通の設計図画像) を末尾に追加。
    # キャラ固有性が低いため最優先にはせず、キャラ固有参照の後に並べる。
    wc_urls, wc_locals = _collect_work_common_reference_images(
        record, form, creations_db_base
    )
    for wc_url in wc_urls:
        _append_unique(url_values, wc_url)
    for wc_local in wc_locals:
        _append_unique(local_values, wc_local)

    return {
        "urls": url_values[:max_images],
        "local_paths": local_values[:max_images],
    }


def collect_record_capabilities(
    record: dict[str, Any],
    form: str = "corefolder",
    creations_db_base: str = "_creations-db",
) -> dict[str, Any]:
    """レコードが備える AI ヒント・DB 画像の充実度を辞書化する。

    生成実行ログ (``run_meta.json``) に同梱して、後から
    「どのキャラクターがどの程度サポートされていたか」を確認しやすくする。

    返却例::

        {
            "has_ai_hints": True,
            "has_common_hints": True,
            "form_hints_available": ["corefolder", "humanoid"],
            "current_form_hints_present": True,
            "outfit_features_count": 3,
            "outfit_features_after_filter": 0,
            "reference_url_count": 1,
            "reference_local_count": 3,
            "db_image_present": {
                "corefolder": True,
                "humanoid": True,
                "current_form": True
            },
            "manifest_ai_training_allowed": True,
        }
    """
    hints = record.get("ai_hints") or {}
    common = hints.get("common") or {}
    forms = hints.get("forms") or {}
    form_data = forms.get(form) or {}

    outfit_raw = list(form_data.get("outfit_features", []) or [])
    if form == "corefolder":
        outfit_filtered = _filter_corefolder_outfit_features(list(outfit_raw))
    else:
        outfit_filtered = list(outfit_raw)

    references = collect_reference_images(
        record, form=form, creations_db_base=creations_db_base
    )

    # 各形態でローカル参照画像が拾えるかを「DBにその形態の画像が存在するか」の代理指標として記録する。
    # record["images"] が空のレコードでも、ai_hints と DB ファイル走査の結果から検出できる。
    db_image_presence: dict[str, bool] = {}
    for target_form in ("corefolder", "humanoid"):
        if target_form == form:
            db_image_presence[target_form] = bool(references["local_paths"])
            continue
        other_refs = collect_reference_images(
            record, form=target_form, creations_db_base=creations_db_base
        )
        db_image_presence[target_form] = bool(other_refs["local_paths"])
    db_image_presence["current_form"] = db_image_presence.get(form, False)

    return {
        "has_ai_hints": bool(hints),
        "has_common_hints": bool(common),
        "form_hints_available": sorted(
            [name for name, value in forms.items() if value]
        ),
        "current_form_hints_present": bool(form_data),
        "outfit_features_count": len(outfit_raw),
        "outfit_features_after_filter": len(outfit_filtered),
        "reference_url_count": len(references["urls"]),
        "reference_local_count": len(references["local_paths"]),
        "db_image_present": db_image_presence,
        "manifest_ai_training_allowed": bool(
            (record.get("ai_training") or {}).get("allowed", True)
        ),
    }


def load_manifest(manifest_path: str | None = None) -> list[dict[str, Any]]:
    """manifest-training.jsonl を読み込んでキャラクターレコードのリストを返す。

    manifest-training.jsonl は AI 学習許可済みレコードのみを含む。
    (manifest.jsonl の ai_training.allowed=true のサブセット)
    """
    path = manifest_path or os.environ.get(
        "MANIFEST_PATH",
        "_creations-ai/ai-dataset/manifest-training.jsonl",
    )
    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def get_characters(manifest_path: str | None = None) -> list[dict[str, Any]]:
    """AI 学習許可済みのキャラクターレコードのみを返す。"""
    return [
        r for r in load_manifest(manifest_path)
        if r.get("_type") == "character" and r.get("has_ai_hints")
    ]


def find_character(
    num: int,
    work_key: str = "#Works_NumberTales",
    manifest_path: str | None = None,
) -> dict[str, Any] | None:
    """番号と作品キーでキャラクターを検索して返す。見つからない場合は None。

    `_creations-db/pkg/python` の `CreationsDBClient` が利用可能な場合、
    取得したレコードに原典DBレコードを `db_record` として統合する。
    """
    target: dict[str, Any] | None = None
    for r in get_characters(manifest_path):
        data = r.get("data", {})
        if r.get("work_key") == work_key and data.get("Num") == num:
            target = r
            break
    if target is None:
        return None

    db_record = _fetch_db_record_via_creations_db_pkg(num=num, work_key=work_key)
    if db_record is not None:
        merged = dict(target)
        merged["db_record"] = db_record
        return merged
    return target


def _is_creations_db_pkg_enabled() -> bool:
    return os.environ.get("CREATIONS_DB_PACKAGE_ENABLE", "1").strip() not in {
        "0",
        "false",
        "False",
    }


def _creations_db_repo_root() -> Path:
    project_root = Path(
        os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[2])
    )
    return Path(
        os.environ.get(
            "CREATIONS_DB_REPO_ROOT", project_root / "_creations-db"
        )
    )


@lru_cache(maxsize=1)
def _get_creationdb_client() -> Any | None:
    """`_creations-db/pkg/python` の CreationsDBClient を返す。利用不可なら None。"""
    if not _is_creations_db_pkg_enabled():
        return None

    repo_root = _creations_db_repo_root()
    if not repo_root.exists() or not repo_root.is_dir():
        return None

    pkg_path = repo_root / "pkg" / "python"
    if not pkg_path.exists():
        return None

    pkg_path_text = str(pkg_path)
    if pkg_path_text not in sys.path:
        sys.path.insert(0, pkg_path_text)

    try:
        module = importlib.import_module("creationsdb")
    except Exception:
        return None

    client_cls = getattr(module, "CreationsDBClient", None)
    if client_cls is None:
        return None

    try:
        return client_cls(str(repo_root))
    except Exception:
        return None


def _fetch_db_record_via_creations_db_pkg(
    num: int, work_key: str
) -> dict[str, Any] | None:
    """原典DBレコードを `pkg/python` 経由で取得する。"""
    client = _get_creationdb_client()
    if client is None:
        return None

    work_id = work_key[1:] if work_key.startswith("#") else work_key
    try:
        record = client.get_record(work_id, "Primary", num, idx_key="Num")
    except Exception:
        return None

    return record if isinstance(record, dict) else None


def _extract_work_dir_from_work_key(work_key: str) -> str:
    """`#Works_NumberTales` -> `Works_NumberTales` の正規化。"""
    text = (work_key or "").strip()
    return text[1:] if text.startswith("#") else text


def _form_common_dataset_candidate_paths(work_key: str) -> list[Path]:
    """作品キーに対応する共通形態データセットの候補パスを返す。

    優先順位:
      1. 環境変数 ``FORM_COMMON_DATASET_PATH`` (明示指定; 旧運用との完全互換)
      2. ``_ideas/form_common_datasets/{Works_<Name>}.json`` (作品別; 新標準)
      3. ``_ideas/form_common_dataset_numbertales.json`` (旧パス; NumberTales 限定の後方互換)
    """
    candidates: list[Path] = []

    env_path = os.environ.get("FORM_COMMON_DATASET_PATH")
    if env_path:
        candidates.append(Path(env_path))

    work_dir = _extract_work_dir_from_work_key(work_key or "#Works_NumberTales")
    if work_dir:
        candidates.append(Path("_ideas/form_common_datasets") / f"{work_dir}.json")

    # 旧パス: 既存ユーザー環境との後方互換 (NumberTales のみ)
    if work_dir == "Works_NumberTales":
        candidates.append(Path("_ideas/form_common_dataset_numbertales.json"))

    return candidates


@lru_cache(maxsize=8)
def _load_form_common_dataset(work_key: str = "#Works_NumberTales") -> dict[str, Any]:
    """指定作品キーの共通形態データセットを読み込む。存在しない場合は空辞書。"""
    for path in _form_common_dataset_candidate_paths(work_key):
        if not path.exists() or not path.is_file():
            continue
        try:
            with path.open(encoding="utf-8") as f:
                loaded = json.load(f)
        except Exception:
            continue
        if isinstance(loaded, dict):
            return loaded
    return {}


def _build_preferred_art_style_block(record: dict[str, Any] | None = None) -> str:
    """共通形態データセットのトップレベル ``preferred_art_style`` を [作風指示] として整形。

    値が存在しない場合は空文字を返す。``record["work_key"]`` から作品別 JSON を読み込み、
    リスト or 文字列を許容する。Gemini/DALL-E どちらでも同じブロック表現を共有する。
    """
    work_key = "#Works_NumberTales"
    if record and isinstance(record.get("work_key"), str) and record["work_key"]:
        work_key = record["work_key"]
    dataset = _load_form_common_dataset(work_key)
    if not isinstance(dataset, dict):
        return ""
    raw = dataset.get("preferred_art_style")
    if isinstance(raw, list):
        items = [str(x).strip() for x in raw if str(x).strip()]
    elif isinstance(raw, str) and raw.strip():
        items = [raw.strip()]
    else:
        return ""
    if not items:
        return ""
    body = "\n".join(f"- {item}" for item in items)
    return f"\n[作風指示 (preferred art style)]\n{body}\n"


def _build_form_common_dataset_block(
    form: str, record: dict[str, Any] | None = None
) -> str:
    """共通形態データセットの要点をプロンプト用テキストとして返す。

    `record["db_record"]` がある場合は、原典DB起源の不変属性（TailsUnit / RaceType / FormalName）を
    差し込んで形態表現のぶれを抑える。

    作品キーは ``record["work_key"]`` から取得し、対応する
    ``_ideas/form_common_datasets/<work>.json`` を読み込む。
    """
    work_key = "#Works_NumberTales"
    if isinstance(record, dict):
        candidate = record.get("work_key")
        if isinstance(candidate, str) and candidate.strip():
            work_key = candidate.strip()

    dataset = _load_form_common_dataset(work_key)
    forms = dataset.get("forms") or {}
    profile = forms.get(form) if isinstance(forms, dict) else None
    if not isinstance(profile, dict):
        profile = {}

    definition_ja = str(profile.get("definition_ja") or "").strip()
    definition_en = str(profile.get("definition_en") or "").strip()
    surface_ja = str(profile.get("surface_description_ja") or "").strip()
    surface_en = str(profile.get("surface_description_en") or "").strip()
    silhouette_ja = str(profile.get("silhouette_summary_ja") or "").strip()
    silhouette_en = str(profile.get("silhouette_summary_en") or "").strip()
    shape_keywords = ", ".join(profile.get("required_shape_keywords") or [])
    disallow_keywords = ", ".join(profile.get("disallow_cross_form_keywords") or [])
    common_equipment = ", ".join(profile.get("common_equipment") or [])
    texture_traits = ", ".join(profile.get("texture_traits") or [])
    function_traits = ", ".join(profile.get("function_traits") or [])

    db_lines: list[str] = []
    # 原典 DB 詳細は humanoid 形態でのみ有効。
    # corefolder に TailsUnit の「上2束5本+下1束2本」等を注入すると、
    # 球体型のコアフォルダに分裂シッポを誘発するため出力しない。
    if form == "humanoid" and isinstance(record, dict):
        db_record = record.get("db_record")
        if isinstance(db_record, dict):
            tails_unit = str(db_record.get("TailsUnit") or "").strip()
            race_type = str(db_record.get("RaceType") or "").strip()
            formal_name = str(db_record.get("FormalName") or "").strip()
            formal_name_en = str(db_record.get("FormalName_EN") or "").strip()
            if tails_unit:
                db_lines.append(f"- DB原典/尾の構造: {tails_unit}")
            if race_type:
                db_lines.append(f"- DB原典/種別: {race_type}")
            if formal_name:
                db_lines.append(f"- DB原典/正式名: {formal_name}")
            if formal_name_en:
                db_lines.append(f"- DB原典/正式名(en): {formal_name_en}")

    db_block = ("\n" + "\n".join(db_lines)) if db_lines else ""

    has_any_content = any([
        definition_ja, definition_en,
        surface_ja, surface_en,
        silhouette_ja, silhouette_en,
        shape_keywords, disallow_keywords,
        common_equipment, texture_traits, function_traits,
        db_block,
    ])
    if not has_any_content:
        return ""

    lines: list[str] = ["[形態共通データセット]"]
    lines.append(f"- 定義(ja): {definition_ja or '(なし)'}")
    lines.append(f"- 定義(en): {definition_en or '(なし)'}")
    if surface_ja or surface_en:
        lines.append(f"- 表面/質感(ja): {surface_ja or '(なし)'}")
        lines.append(f"- 表面/質感(en): {surface_en or '(なし)'}")
    if silhouette_ja or silhouette_en:
        lines.append(f"- シルエット要約(ja): {silhouette_ja or '(なし)'}")
        lines.append(f"- シルエット要約(en): {silhouette_en or '(なし)'}")
    if common_equipment:
        lines.append(f"- 共通装備/付属要素: {common_equipment}")
    if texture_traits:
        lines.append(f"- 質感特徴: {texture_traits}")
    if function_traits:
        lines.append(f"- 機能/振る舞い: {function_traits}")
    lines.append(f"- 必須形状キーワード: {shape_keywords or '(なし)'}")
    lines.append(f"- 形態混入の禁止キーワード: {disallow_keywords or '(なし)'}")
    if db_block:
        lines.append(db_block.lstrip("\n"))

    return "\n".join(lines)


def build_novelai_prompt(record: dict[str, Any], form: str = "corefolder") -> dict[str, str]:
    """NovelAI / Stable Diffusion 用のポジティブ・ネガティブプロンプトを返す。"""
    hints = record.get("ai_hints") or {}
    form_data = (hints.get("forms") or {}).get(form) or {}
    return {
        "positive": form_data.get("prompt_export", ""),
        "negative": form_data.get("negative_prompt_export", ""),
    }


def build_dalle_prompt(
    record: dict[str, Any],
    form: str = "corefolder",
    scene: str = "",
) -> str:
    """DALL-E / ChatGPT 用の自然文プロンプトを返す。"""
    hints = record.get("ai_hints") or {}
    common = hints.get("common") or {}
    form_data = (hints.get("forms") or {}).get(form) or {}
    references = collect_reference_images(record, form=form)

    identity_tags = ", ".join(common.get("identity_tags", []))
    immutable_traits = ", ".join(common.get("immutable_traits", []))
    form_tags = ", ".join(form_data.get("form_tags", []))
    form_silhouette_body, form_silhouette_attached = _extract_silhouette_notes_for_prompt(
        form_data, form
    )
    form_immutable_constraints = [
        str(x).strip() for x in (form_data.get("immutable_constraints") or []) if str(x).strip()
    ]
    form_negative_keywords = [
        str(x).strip() for x in (form_data.get("negative_keywords") or []) if str(x).strip()
    ]
    extra_negative_items: list[str] = []
    if form == "corefolder":
        extra_negative_items.extend(
            [
                "full humanoid body",
                "human arms",
                "human legs",
            ]
        )
    else:
        extra_negative_items.extend(["extra arms", "extra hands", "more than two arms"])
    negative_parts = [
        *form_data.get("negative_visuals", []),
        *form_negative_keywords,
        *extra_negative_items,
    ]
    negative_visuals = ", ".join(negative_parts)
    ref_urls = ", ".join(references["urls"])
    if form == "corefolder":
        current_form_description = _sanitize_corefolder_form_description(
            form_data.get("natural_language_description", "")
        )
    else:
        current_form_description = _sanitize_natural_language_description(
            form_data.get("natural_language_description", "")
        )
    if form == "corefolder":
        current_form_description += (
            " Keep a compact spherical corefolder silhouette,"
            " with no humanoid torso and no human limbs."
        )
    form_common_block = _build_form_common_dataset_block(form, record)
    if form == "corefolder":
        form_lock = (
            "- corefolder 形態として描く\n"
            "- humanoid 形態由来の要素は一切混入しない\n"
            "- 装備・衣装の識別要素を省略しない\n"
            "- 人型の腕・手・脚・足を描かない（非人型のコアフォルダ体型を維持）"
        )
    else:
        form_lock = (
            "- humanoid 形態として描く\n"
            "- corefolder 装備を混入しない\n"
            "- 私服寄りの表現を優先する\n"
            "- 腕は必ず 2 本、手は 2 つ（余分な腕・手を描かない）\n"
            "- 尾は枝分かれを含めて·合計 7 本·を守る（定義以上も以下も描かない）"
        )
    if form_immutable_constraints:
        form_lock += "\n" + "\n".join(
            f"- {item}" for item in form_immutable_constraints
        )

    current_outfit_features = form_data.get("outfit_features", []) or []
    if form == "corefolder":
        current_outfit_features = _filter_corefolder_outfit_features(
            list(current_outfit_features)
        )
    current_outfit_dalle = ", ".join(current_outfit_features)
    silhouette_raw = common.get("silhouette_features", []) or []
    silhouette_features = ", ".join(silhouette_raw)
    current_focus_lines: list[str] = []
    if current_outfit_dalle:
        current_focus_lines.append(f"- 衣装: {current_outfit_dalle}")
    # silhouette_features (髪型・瞳色など) は humanoid 形態でのみ有効。
    # corefolder (球体型・髪なし) に「ポニーテールのブロンド髪」を指示すると矛盾するため出さない。
    if form == "humanoid" and silhouette_features:
        current_focus_lines.append(f"- シルエット (形態によらず固定): {silhouette_features}")
    # corefolder でも 瞳色・耳・尾などの「顔/種別記号」は保持したいときだけ抽出して注入。
    if form == "corefolder":
        face_features = _extract_face_features_for_corefolder(list(silhouette_raw))
        if face_features:
            current_focus_lines.append(
                f"- 顔/種別記号 (保持): {', '.join(face_features)}"
            )
    if form_silhouette_body:
        current_focus_lines.append(
            "- 形状補足 (body): " + "; ".join(form_silhouette_body)
        )
    if form_silhouette_attached:
        current_focus_lines.append(
            "- 装着アクセサリ (attached): " + "; ".join(form_silhouette_attached)
        )
    current_focus_block = (
        "[現在形態の重点要素]\n" + "\n".join(current_focus_lines) + "\n\n"
        if current_focus_lines
        else ""
    )

    # 別形態由来のセクションは「抽象表現」のみとし、具体的な衣装単語をプロンプトに露出しない。
    # （拡散モデルは否定語より「具体名のチラ見せ」に引きずられやすいため）
    if form == "corefolder":
        cross_form_block = "- humanoid 形態由来の衣装・人型体型・髪型を一切混入しない"
    else:
        cross_form_block = "- corefolder 形態由来の球体コア・ハーネス・フードを一切混入しない"

    # シーン指定・作風ヒントを末尾に付け足す。
    scene_block = f"\n\n[シーン・追加要望]\n{scene.strip()}" if scene and scene.strip() else ""
    art_style_block = _build_preferred_art_style_block(record)

    return (
        "このキャラクターを描いてください。\n\n"
        "[参照画像]\n"
        f"- 可能であれば以下の既存画像も参照してください。\n"
        f"- URL: {ref_urls or '(なし)'}\n"
        "- ローカル画像は添付される前提です。\n\n"
        f"[素体特徴]\n{_sanitize_natural_language_description(common.get('natural_language_description', ''))}\n\n"
        f"[今回の姿]\n{current_form_description}\n\n"
        f"[形態固定ルール]\n{form_lock}\n\n"
        f"[識別記号 (必ず満たしてください)]\n"
        f"- {identity_tags}\n"
        f"- {immutable_traits}\n"
        f"- {form_tags}\n\n"
        f"{current_focus_block}"
        f"{form_common_block}\n\n"
        f"[混入禁止 (別形態由来)]\n{cross_form_block}\n\n"
        f"[避けるべき要素]\n{negative_visuals}"
        f"{art_style_block}"
        f"{scene_block}"
    )


def build_gemini_prompt(
    record: dict[str, Any],
    form: str = "corefolder",
    scene: str = "",
) -> dict[str, Any]:
    """Gemini / Imagen 用のプロンプトと参照画像 URL を返す。"""
    hints = record.get("ai_hints") or {}
    common = hints.get("common") or {}
    form_data = (hints.get("forms") or {}).get(form) or {}
    references = collect_reference_images(record, form=form)

    palette = common.get("palette_priority") or {}
    identity_tags = ", ".join(common.get("identity_tags", []))
    form_tags = ", ".join(form_data.get("form_tags", []))
    form_silhouette_body, form_silhouette_attached = _extract_silhouette_notes_for_prompt(
        form_data, form
    )
    form_immutable_constraints = [
        str(x).strip() for x in (form_data.get("immutable_constraints") or []) if str(x).strip()
    ]
    form_negative_keywords = [
        str(x).strip() for x in (form_data.get("negative_keywords") or []) if str(x).strip()
    ]
    current_outfit_features = form_data.get("outfit_features", []) or []
    if form == "corefolder":
        current_outfit_features = _filter_corefolder_outfit_features(
            list(current_outfit_features)
        )
    current_outfit = ", ".join(current_outfit_features)
    extra_negative_items: list[str] = []
    if form == "corefolder":
        extra_negative_items.extend(
            [
                "full humanoid body",
                "human arms",
                "human legs",
            ]
        )
    else:
        extra_negative_items.extend(["extra arms", "extra hands", "more than two arms"])
    current_negative = ", ".join(
        [
            *form_data.get("negative_visuals", []),
            *form_negative_keywords,
            *extra_negative_items,
        ]
    )
    ref_urls = "\n".join(f"- {u}" for u in references["urls"])
    if form == "corefolder":
        current_form_description = _sanitize_corefolder_form_description(
            form_data.get("natural_language_description", "")
        )
    else:
        current_form_description = _sanitize_natural_language_description(
            form_data.get("natural_language_description", "")
        )
    if form == "corefolder":
        current_form_description += (
            " Keep a compact spherical corefolder silhouette,"
            " with no humanoid torso and no human limbs."
        )
    form_common_block = _build_form_common_dataset_block(form, record)

    if form == "corefolder":
        form_lock = (
            "- 必ず corefolder 形態として描くこと\n"
            "- safety device harness / hoodie / corefolder要素を明確に残すこと\n"
            "- humanoid 形態由来の要素に一切寄せないこと\n"
            "- 人型の腕・手・脚・足を描かないこと（非人型シルエットを維持）"
        )
        cross_form_block = "- humanoid 形態由来の衣装・人型体型・髪型を一切混入しない"
    else:
        form_lock = (
            "- 必ず humanoid 形態として描くこと\n"
            "- corefolder 装備（harness/hoodie）を混入させないこと\n"
            "- 私服寄りの humanoid 表現を優先すること\n"
            "- 腕は 2 本、手は 2 つで固定し、余分な腕を描かないこと\n"
            "- 尾は枝分かれを含めて·合計 7 本·を守る（それ以上も以下も描かない）"
        )
        cross_form_block = "- corefolder 形態由来の球体コア・ハーネス・フードを一切混入しない"
    if form_immutable_constraints:
        form_lock += "\n" + "\n".join(
            f"- {item}" for item in form_immutable_constraints
        )

    # corefolder では「[シルエット特徴]」ブロック (共通 silhouette 由来の髪型・ポニーテール) を出さない。
    # ただし瞳色・耳・尾など「顔/種別記号」は corefolder でも保持したいため、抽出して別ブロックに記載しわも衡とる。
    silhouette_raw = common.get("silhouette_features", []) or []
    if form == "humanoid":
        silhouette_block = (
            "[シルエット特徴 (形態によらず固定)]\n"
            f"- {', '.join(silhouette_raw) or '(なし)'}\n\n"
        )
    else:
        face_features = _extract_face_features_for_corefolder(list(silhouette_raw))
        if face_features:
            silhouette_block = (
                "[顔/種別記号 (corefolder でも保持)]\n"
                f"- {', '.join(face_features)}\n\n"
            )
        else:
            silhouette_block = ""

    # 現在形態の重点要素 ブロックは、フィルタ後の要素が有る場合のみ出す。
    focus_lines: list[str] = []
    if current_outfit:
        focus_lines.append(current_outfit)
    if form_silhouette_body:
        focus_lines.append(
            "形状補足 (body): " + "; ".join(form_silhouette_body)
        )
    if form_silhouette_attached:
        focus_lines.append(
            "装着アクセサリ (attached): " + "; ".join(form_silhouette_attached)
        )
    if focus_lines:
        current_focus_block = "[現在形態の重点要素]\n" + "\n".join(
            f"- {line}" for line in focus_lines
        ) + "\n\n"
    else:
        current_focus_block = ""

    # シーン指定・作風ヒントを末尾に付け足す。
    scene_block = f"\n[シーン・追加要望]\n{scene.strip()}\n" if scene and scene.strip() else ""
    art_style_block = _build_preferred_art_style_block(record)

    prompt = (
        "以下の参照画像と同じキャラクターを、別のポーズで描いてください。\n\n"
        f"[参照画像URL]\n{ref_urls or '- (なし)'}\n\n"
        "[参照画像ローカル]\n- ローカル画像はAPIリクエスト時に添付されます。\n\n"
        f"[素体特徴]\n{_sanitize_natural_language_description(common.get('natural_language_description', ''))}\n\n"
        f"[今回の姿]\n{current_form_description}\n\n"
        f"[形態固定ルール]\n{form_lock}\n\n"
        f"[識別記号 (必ず満たしてください)]\n"
        f"- {identity_tags}\n"
        f"- 不変属性: {', '.join(common.get('immutable_traits', [])) or '(なし)'}\n"
        f"- {form_tags}\n\n"
        f"{silhouette_block}"
        f"{form_common_block}\n\n"
        f"{current_focus_block}"
        f"[混入禁止 (別形態由来)]\n{cross_form_block}\n\n"
        f"[避けるべき要素]\n{current_negative}\n\n"
        f"{art_style_block}"
        f"{scene_block}"
        f"[パレット参考]\n"
        f"primary: {palette.get('primary', '')}\n"
        f"secondary: {palette.get('secondary', '')}\n"
        f"accent: {palette.get('accent', '')}"
    )

    return {
        "prompt": prompt,
        "reference_image_url": (references["urls"][0] if references["urls"] else ""),
        "reference_image_urls": references["urls"],
        "reference_local_paths": references["local_paths"],
    }


def get_local_image_paths(
    work_key: str = "#Works_NumberTales",
    image_index_path: str | None = None,
    creations_db_base: str = "_creations-ai/creations-db",
) -> list[str]:
    """image-index.json からローカル画像パスの一覧を返す。"""
    path = image_index_path or os.environ.get(
        "IMAGE_INDEX_PATH",
        "_creations-ai/ai-dataset/image-index.json",
    )
    with open(path, encoding="utf-8") as f:
        idx = json.load(f)

    rel_paths = (idx.get("works") or {}).get(work_key, {}).get("images", [])
    return [str(Path(creations_db_base) / rel) for rel in rel_paths]
