"""
tests/test_appearance_detail_review.py — AppearanceDetail 照合レビューの回帰テスト。

pytest 非依存で書いてあり、どちらでも走る:
    python tests/test_appearance_detail_review.py   # 自己完結ランナー
    python -m pytest tests/                         # pytest を入れている場合

固定したい挙動は 3 つ:
  1. `entries_for_form()` が Formation=null (両形態共通) を落とさず、他形態を混ぜないこと。
  2. `normalize_results()` がモデル出力の欠落・重複・範囲外を握り潰さないこと。
     判定が返らなかった行が黙って消えると「全件照合済み」に見え、レビューが嘘になる。
  3. `palette_source_image_keys()` が typedef の `$palette.source` 宣言だけを拾い、
     `conceptAlt_PNGName` → `concept_alt` の命名差を吸収すること。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.tools.verify_appearance_detail import (  # noqa: E402
    entries_for_form,
    excluded_for_form,
    format_entry,
    normalize_results,
    palette_source_image_keys,
    summarize,
)

_RECORD = {
    "db_record": {
        "AppearanceDetail": [
            {
                "Formation": "corefolder",
                "BodyPart": ["#BodyPart_Arm"],
                "Laterality": "#Lat_Right",
                "DesignElement": "#Element_NumberMark",
                "Attrs": [
                    {"AttrLabel": "#DesignAttr_Color", "value_JP": "黄緑", "value_EN": "yellow-green"},
                ],
            },
            {
                "Formation": "humanoid",
                "BodyPart": ["#BodyPart_Leg"],
                "DesignElement": "#Element_CostumeItem",
                "Attrs": [{"AttrLabel": "#DesignAttr_Overview", "value_EN": "orange shorts"}],
            },
            {
                "Formation": None,
                "BodyPart": ["#BodyPart_Ear"],
                "Laterality": "#Lat_Both",
                "DesignElement": "#Element_Ear",
                "Attrs": [{"AttrLabel": "#DesignAttr_Ear", "vdict_EarShapeType": "#EarShapeType_Fox"}],
            },
        ]
    }
}


def test_entries_for_form_keeps_shared_and_drops_other_form() -> None:
    core = entries_for_form(_RECORD, "corefolder")
    assert [e["DesignElement"] for e in core] == ["#Element_NumberMark", "#Element_Ear"], core

    humanoid = entries_for_form(_RECORD, "humanoid")
    assert [e["DesignElement"] for e in humanoid] == ["#Element_CostumeItem", "#Element_Ear"], humanoid


def test_format_entry_keeps_enum_and_text_values() -> None:
    lines = [format_entry(i, e) for i, e in enumerate(entries_for_form(_RECORD, "corefolder"), 1)]
    assert lines[0] == "1. [Arm(Right)] NumberMark: Color=yellow-green", lines[0]
    # vdict_* の列挙値 (value_EN を持たない) も落とさないこと。
    assert lines[1] == "2. [Ear(Both)] Ear: Ear=Fox", lines[1]


def test_normalize_results_fills_missing_and_drops_garbage() -> None:
    raw = [
        {"index": 1, "verdict": "MATCH", "note": "確認できた"},
        {"index": 1, "verdict": "mismatch", "note": "重複なので捨てる"},
        {"index": 99, "verdict": "mismatch", "note": "範囲外なので捨てる"},
        {"index": 2, "verdict": "怪しい", "note": "未知の verdict は unclear へ"},
        "壊れた要素",
    ]
    results = normalize_results(raw, 3)
    assert [r["index"] for r in results] == [1, 2, 3], results
    assert results[0]["verdict"] == "match"
    assert results[1]["verdict"] == "unclear"
    # 3 はモデルが返さなかった行。消さずに unclear で残す。
    assert results[2]["verdict"] == "unclear" and results[2]["note"], results[2]
    assert summarize(results) == {"match": 1, "mismatch": 0, "unclear": 2}


def test_normalize_results_handles_non_list() -> None:
    assert [r["verdict"] for r in normalize_results(None, 2)] == ["unclear", "unclear"]


_TYPEDEF = {
    "$DefType": [
        {"hashTag": "Name_JP"},
        {
            "hashTag": "Images",
            "$type": [
                {"hashTag": "concept_PNGName", "$palette": {"source": "swatch"}},
                {"hashTag": "conceptAlt_PNGName", "$palette": {"source": "swatch"}},
                {"hashTag": "corefolder_PNGPath", "$palette": {"source": "artwork"}},
                # $palette 宣言なし = 配色抽出の対象外。照合にも使わない。
                {"hashTag": "humanoid_PNGPath"},
                {"hashTag": "NotAnImageField"},
            ],
        },
    ]
}


def test_palette_source_image_keys_reads_typedef_declaration() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_dir = Path(tmp) / "data" / "Works_NumberTales" / "DataBases"
        db_dir.mkdir(parents=True)
        (db_dir / "db_type.json").write_text(json.dumps(_TYPEDEF), encoding="utf-8")

        keys = palette_source_image_keys("#Works_NumberTales", tmp)
        # conceptAlt → concept_alt へ正規化され、宣言のない humanoid は入らない。
        assert keys == ["concept", "concept_alt", "corefolder"], keys


def test_excluded_for_form_keeps_form_neutral_material() -> None:
    catalog = "data/Works_NumberTales/Images/DB_Primary/catalog/chr-dsgn_catalogNTS-57.png"
    concept = "data/Works_NumberTales/Images/DB_Primary/concept/cnsp_imgNTS-57.png"
    core = "data/Works_NumberTales/Images/DB_Primary/corefolder/57/emstk_corefolderNTS-57-1.png"
    # 設定資料・設定原画は形態に依らないのでどちらの照合にも残す。
    for path in (catalog, concept):
        assert not excluded_for_form(path, "corefolder"), path
        assert not excluded_for_form(path, "humanoid"), path
    # 形態専用画像は他形態の照合からは外す。
    assert excluded_for_form(core, "humanoid")
    assert not excluded_for_form(core, "corefolder")


def test_palette_source_image_keys_missing_typedef_returns_empty() -> None:
    # 宣言が無い作品では呼び出し側が従来の参照画像へフォールバックする。
    with tempfile.TemporaryDirectory() as tmp:
        assert palette_source_image_keys("#Works_Unknown", tmp) == []


if __name__ == "__main__":
    test_entries_for_form_keeps_shared_and_drops_other_form()
    test_format_entry_keeps_enum_and_text_values()
    test_normalize_results_fills_missing_and_drops_garbage()
    test_normalize_results_handles_non_list()
    test_palette_source_image_keys_reads_typedef_declaration()
    test_excluded_for_form_keeps_form_neutral_material()
    test_palette_source_image_keys_missing_typedef_returns_empty()
    print("OK: tests/test_appearance_detail_review.py")
