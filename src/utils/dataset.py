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


def _looks_like_target_character(path_text: str, num_value: Any) -> bool:
    if num_value is None:
        return False

    token = str(num_value).strip().lower()
    if not token:
        return False

    lower = path_text.replace("\\", "/").lower()
    if token.isdigit():
        return bool(re.search(rf"(?<!\\d){re.escape(token)}(?!\\d)", lower))
    return token in lower


def _is_path_compatible_with_form(path_text: str, form: str) -> bool:
    lower = path_text.replace("\\", "/").lower()

    # 参照資料・カタログ画像は作風誘導が強すぎるため除外する。
    if "/catalog/" in lower:
        return False

    if form == "corefolder":
        if "/arts/humanoids/" in lower:
            return False
    elif form == "humanoid":
        if "/corefolder/" in lower:
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


def collect_reference_images(
    record: dict[str, Any],
    form: str = "corefolder",
    creations_db_base: str = "_creations-db",
    max_images: int = 6,
) -> dict[str, list[str]]:
    """レコードから参照画像 URL とローカルパスを集約して返す。"""
    hints = record.get("ai_hints") or {}
    common = hints.get("common") or {}
    form_data = (hints.get("forms") or {}).get(form) or {}
    url_values: list[str] = []

    for value in (form_data.get("reference_images") or {}).values():
        if isinstance(value, str) and _is_path_compatible_with_form(value, form):
            _append_unique(url_values, value)
    for value in (common.get("reference_images") or {}).values():
        if isinstance(value, str) and _is_path_compatible_with_form(value, form):
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
                if not _is_path_compatible_with_form(path, form):
                    continue
                _append_unique(local_candidates, path)

    for forced_path in _collect_forced_local_images(record, form, creations_db_base):
        _append_unique(local_candidates, forced_path)

    ranked_candidates = _sort_paths_for_form(local_candidates, form)
    for path in ranked_candidates:
        _append_unique(local_values, path)

    url_values = _apply_form_reference_focus(url_values, form)
    local_values = _apply_form_reference_focus(local_values, form)
    url_values = _sort_paths_for_form(url_values, form)
    local_values = _sort_paths_for_form(local_values, form)

    return {
        "urls": url_values[:max_images],
        "local_paths": local_values[:max_images],
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


@lru_cache(maxsize=1)
def _load_form_common_dataset() -> dict[str, Any]:
    """共通形態データセットを読み込む。存在しない場合は空辞書を返す。"""
    path = Path(
        os.environ.get(
            "FORM_COMMON_DATASET_PATH",
            "_ideas/form_common_dataset_numbertales.json",
        )
    )
    if not path.exists() or not path.is_file():
        return {}

    try:
        with path.open(encoding="utf-8") as f:
            loaded = json.load(f)
    except Exception:
        return {}

    return loaded if isinstance(loaded, dict) else {}


def _build_form_common_dataset_block(
    form: str, record: dict[str, Any] | None = None
) -> str:
    """共通形態データセットの要点をプロンプト用テキストとして返す。

    `record["db_record"]` がある場合は、原典DB起源の不変属性（TailsUnit / RaceType / FormalName）を
    差し込んで形態表現のぶれを抑える。
    """
    dataset = _load_form_common_dataset()
    forms = dataset.get("forms") or {}
    profile = forms.get(form) if isinstance(forms, dict) else None
    if not isinstance(profile, dict):
        profile = {}

    definition_ja = str(profile.get("definition_ja") or "").strip()
    definition_en = str(profile.get("definition_en") or "").strip()
    shape_keywords = ", ".join(profile.get("required_shape_keywords") or [])
    disallow_keywords = ", ".join(profile.get("disallow_cross_form_keywords") or [])

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

    if not (definition_ja or definition_en or shape_keywords or disallow_keywords or db_block):
        return ""

    return (
        "[形態共通データセット]\n"
        f"- 定義(ja): {definition_ja or '(なし)'}\n"
        f"- 定義(en): {definition_en or '(なし)'}\n"
        f"- 必須形状キーワード: {shape_keywords or '(なし)'}\n"
        f"- 形態混入の禁止キーワード: {disallow_keywords or '(なし)'}"
        f"{db_block}"
    )


def build_novelai_prompt(record: dict[str, Any], form: str = "corefolder") -> dict[str, str]:
    """NovelAI / Stable Diffusion 用のポジティブ・ネガティブプロンプトを返す。"""
    hints = record.get("ai_hints") or {}
    form_data = (hints.get("forms") or {}).get(form) or {}
    return {
        "positive": form_data.get("prompt_export", ""),
        "negative": form_data.get("negative_prompt_export", ""),
    }


def build_dalle_prompt(record: dict[str, Any], form: str = "corefolder") -> str:
    """DALL-E / ChatGPT 用の自然文プロンプトを返す。"""
    hints = record.get("ai_hints") or {}
    common = hints.get("common") or {}
    form_data = (hints.get("forms") or {}).get(form) or {}
    references = collect_reference_images(record, form=form)

    identity_tags = ", ".join(common.get("identity_tags", []))
    immutable_traits = ", ".join(common.get("immutable_traits", []))
    form_tags = ", ".join(form_data.get("form_tags", []))
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
    negative_parts = [*form_data.get("negative_visuals", []), *extra_negative_items]
    negative_visuals = ", ".join(negative_parts)
    ref_urls = ", ".join(references["urls"])
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

    current_outfit_dalle = ", ".join(form_data.get("outfit_features", []))
    silhouette_features = ", ".join(common.get("silhouette_features", []))
    current_focus_lines: list[str] = []
    if current_outfit_dalle:
        current_focus_lines.append(f"- 衣装: {current_outfit_dalle}")
    # silhouette_features (髪型・瞳色など) は humanoid 形態でのみ有効。
    # corefolder (球体型・髪なし) に「ポニーテールのブロンド髪」を指示すると矛盾するため出さない。
    if form == "humanoid" and silhouette_features:
        current_focus_lines.append(f"- シルエット (形態によらず固定): {silhouette_features}")
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
    )


def build_gemini_prompt(record: dict[str, Any], form: str = "corefolder") -> dict[str, Any]:
    """Gemini / Imagen 用のプロンプトと参照画像 URL を返す。"""
    hints = record.get("ai_hints") or {}
    common = hints.get("common") or {}
    form_data = (hints.get("forms") or {}).get(form) or {}
    references = collect_reference_images(record, form=form)

    palette = common.get("palette_priority") or {}
    identity_tags = ", ".join(common.get("identity_tags", []))
    form_tags = ", ".join(form_data.get("form_tags", []))
    current_outfit = ", ".join(form_data.get("outfit_features", []))
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
    current_negative = ", ".join([*form_data.get("negative_visuals", []), *extra_negative_items])
    ref_urls = "\n".join(f"- {u}" for u in references["urls"])
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

    # corefolder では「[シルエット特徴]」「[現在形態の重点要素]」(共通silhouette由来) を出さない
    # (球体型コアに blonde ponytail を強制すると矛盾するため)
    if form == "humanoid":
        silhouette_block = (
            "[シルエット特徴 (形態によらず固定)]\n"
            f"- {', '.join(common.get('silhouette_features', [])) or '(なし)'}\n\n"
        )
    else:
        silhouette_block = ""

    prompt = (
        "以下の参照画像と同じキャラクターを、別のポーズで描いてください。\n\n"
        f"[参照画像URL]\n{ref_urls or '- (なし)'}\n\n"
        "[参照画像ローカル]\n- ローカル画像はAPIリクエスト時に添付されます。\n\n"
        f"[素体特徴]\n{_sanitize_natural_language_description(common.get('natural_language_description', ''))}\n\n"
        f"[今回の姿]\n{current_form_description}\n\n"
        f"[形態固定ルール]\n{form_lock}\n\n"
        f"[識別記号 (必ず満たしてください)]\n"
        f"- {identity_tags}\n"
        f"- {form_tags}\n\n"
        f"{silhouette_block}"
        f"{form_common_block}\n\n"
        f"[現在形態の重点要素]\n{current_outfit}\n\n"
        f"[混入禁止 (別形態由来)]\n{cross_form_block}\n\n"
        f"[避けるべき要素]\n{current_negative}\n\n"
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
