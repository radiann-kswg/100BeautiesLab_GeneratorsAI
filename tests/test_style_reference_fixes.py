"""
tests/test_style_reference_fixes.py — 2026-08-29 作風忠実度修正の回帰テスト
Copyright © RadianN_kswg — CC BY-NC 4.0

「最終画が原典を一度も見ない」問題の修正 (catalog 許可・arts 優先・_lang_ 除外・
作風キーワード統合・Stage5 ラフ枠制限) が退行しないことを守る。
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils.dataset import (  # noqa: E402
    _apply_form_reference_focus,
    _get_category_priority,
    _is_path_compatible_with_form,
    get_art_style_keywords,
)


def test_catalog_is_allowed_for_both_forms():
    path = "data/Works_NumberTales/Images/DB_Primary/catalog/chr-dsgn_catalogNTS-57.png"
    assert _is_path_compatible_with_form(path, "corefolder")
    assert _is_path_compatible_with_form(path, "humanoid")


def test_lang_variants_are_excluded():
    path = "data/Works_NumberTales/Images/DB_Primary/arts/corefolders/x/_lang_EN/art[EN]_x-NTS-57.png"
    assert not _is_path_compatible_with_form(path, "corefolder")


def test_arts_outrank_design_docs_for_corefolder():
    prio = _get_category_priority("corefolder")
    assert prio["arts"] < prio["design"]
    assert prio["corefolder"] < prio["arts"]
    assert "catalog" in prio


def test_focus_keeps_catalog_and_one_concept():
    paths = [
        "DB_Primary/corefolder/57/emstk_corefolderNTS-57-1.png",
        "DB_Primary/catalog/chr-dsgn_catalogNTS-57.png",
        "DB_Primary/concept/cnsp_imgNTS-57.png",
    ]
    focused = _apply_form_reference_focus(paths, "corefolder")
    assert paths[0] in focused
    assert paths[1] in focused, "catalog (キャラデザ表) が focus で捨てられている"
    assert paths[2] in focused, "concept が 1 枚も残っていない"


def test_style_keywords_include_analysis_summary():
    keywords = get_art_style_keywords("#Works_NumberTales")
    assert "Cute" in keywords
    # style_analysis_summary.keywords_en 由来 (旧実装では捨てられていた作風の核)
    assert any("shading" in k.lower() or "pastel" in k.lower() for k in keywords)


def test_get_characters_excludes_references_but_keeps_semiprimary():
    """2026-08-29 CreationsAI#1: References は型で除外、AIHints 未収録キャラは列挙する。"""
    from src.utils.dataset import get_characters

    chars = get_characters()
    assert all(
        not str(r.get("db_source") or "").replace("\\", "/").startswith("data/References/")
        for r in chars
    ), "References 参照レコードがキャラクター列挙に混入している"
    ids = {str(r.get("id")) for r in chars}
    assert "3x11" in ids, "SemiPrimary (3x11) がローカル列挙から漏れている"


def test_load_reference_bytes_skips_broken_image(tmp_path):
    """壊れ画像 (シグネチャ不正・PIL 不可読) は None を返しスキップされる。"""
    from src.utils.image_io import load_reference_bytes

    broken = tmp_path / "broken.png"
    broken.write_bytes(b"this is not an image at all........")
    assert load_reference_bytes(broken) is None


def test_name_lookup_includes_semiprimary_names():
    """natural_parser の名前辞書が manifest ベースになり SemiPrimary 名も引ける。"""
    from src.pipeline import natural_parser

    natural_parser._NAME_LOOKUP_CACHE = None  # キャッシュ破棄
    lookup = natural_parser._build_name_lookup()
    semi_nums = {v for v in lookup.values() if not v.isdigit()}
    assert "3x11" in semi_nums, "SemiPrimary (3x11) の名前が辞書に載っていない"


def test_stage5_caps_rough_refs():
    import inspect

    from src.pipeline import final_generator

    src_text = inspect.getsource(final_generator._synthesize_with_gemini)
    assert "[:2]" in src_text, "Stage5 のラフ参照制限が消えている (原典参照枠が全滅する退行)"
