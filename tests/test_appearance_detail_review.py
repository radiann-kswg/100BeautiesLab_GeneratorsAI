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
  4. `audit_coverage()` が「色語はあるのに BodyPart が無い」を最優先の欠落として拾い、
     形態違いのエントリを混ぜないこと。配色検知ツールが AppliesTo を埋められない原因そのもの。
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
    _char_label,
    audit_coverage,
    build_color_attr_proposal_md,
    entries_for_form,
    excluded_for_form,
    format_entry,
    normalize_color_suggestions,
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


# `collect_color_hint_evidence()` (node 経由で上流ツールを呼ぶ) の evidence 部分を模したもの。
_EVIDENCE = {
    "entries": [
        # 色語あり + BodyPart あり = 配色ツールが AppliesTo を埋められる
        {"index": 1, "formation": None, "bodyPart": ["#BodyPart_Chest"], "element": "#Element_CostumeItem",
         "text": "Overview: blue inner shirt", "hints": [{"word": "blue", "bodyPart": "#BodyPart_Chest"}]},
        # 色語あり + BodyPart なし = 転記できない (最優先の欠落)
        {"index": 2, "formation": "humanoid", "bodyPart": [], "element": "#Element_Motif",
         "text": "Overview: yellow blazer", "hints": [{"word": "yellow", "bodyPart": None}]},
        # 色語なし = 色語表に無い語 (blonde) の可能性
        {"index": 3, "formation": None, "bodyPart": ["#BodyPart_Hair"], "element": "#Element_Motif",
         "text": "Overview: blonde ponytail", "hints": []},
        # 別形態のエントリは混ぜない
        {"index": 4, "formation": "corefolder", "bodyPart": [], "element": "#Element_Motif",
         "text": "Overview: yellow sphere", "hints": [{"word": "yellow", "bodyPart": None}]},
    ],
    "palette": [
        {"hex": "#4B79BE", "role": "#ColorRole_Sub", "appliesTo": ["#BodyPart_Chest"], "formation": None,
         "hints": [{"word": "blue"}]},
        {"hex": "#F7FFB9", "role": "#ColorRole_Accent", "appliesTo": None, "formation": None, "hints": []},
    ],
}


def test_proposal_excludes_common_colors_from_gaps() -> None:
    """共通造形色 (肌色・毛色) は設計上 ColorPalette に載らないので指摘しないこと。"""
    audit = audit_coverage(_EVIDENCE, None)
    # index 3 (blonde ponytail) は色語が無いエントリ。画像から white と green を読んだ想定。
    detections = {"57(イズナ)": {3: {"color_words": ["white", "green"], "note": "画像より"}}}
    md = build_color_attr_proposal_md(
        [("57(イズナ)", audit)], detections, ["white"], None, "gpt-4o", "cmd"
    )
    # ColorPalette には blue しか無いので green は取りこぼし候補、white は共通色として除外。
    assert "ColorPalette に見当たらない色（1 件）" in md, md
    assert "| `green` (緑) |" in md, md
    assert "| `white` (白) |" not in md, md


def test_normalize_color_suggestions_drops_unknown_words() -> None:
    raw = [
        {"index": 1, "color_words": ["yellow", "white"], "note": "金髪"},
        # 色語表に無い語は捨てる (提案どおり書いても配色ツールが拾えないため)。
        {"index": 2, "color_words": ["turquoise", "blue"], "note": "混在"},
        {"index": 3, "color_words": ["chartreuse"], "note": "全部未知なら採らない"},
        {"index": 4, "color_words": [], "note": "確認できず"},
        {"index": 99, "color_words": ["red"], "note": "範囲外"},
        "壊れた要素",
    ]
    out = normalize_color_suggestions(raw, {1, 2, 3, 4})
    assert sorted(out) == [1, 2], out
    assert out[1]["color_words"] == ["yellow", "white"]
    assert out[2]["color_words"] == ["blue"]


def test_char_label_squashes_newlines() -> None:
    # 別名併記で Name_JP に改行が入るレコードがある。表・見出し・Issue タイトルが崩れないこと。
    assert _char_label({"data": {"Name_JP": "34(サトシ)\nサンジ"}}) == "34(サトシ) サンジ"
    assert _char_label({"data": {"Num": 57}}) == "57"
    assert _char_label({}, fallback="2-alt") == "2-alt"


def test_audit_coverage_flags_missing_body_part_per_form() -> None:
    audit = audit_coverage(_EVIDENCE, "humanoid")
    # humanoid + 形態共通(null) のみ。corefolder 専用の index 4 は入らない。
    assert [e["index"] for e in audit["entries"]] == [1, 2, 3]
    assert [e["index"] for e in audit["missing_body_part"]] == [2]
    assert [e["index"] for e in audit["no_color_word"]] == [3]
    assert [c["hex"] for c in audit["unbacked_hex"]] == ["#F7FFB9"]

    # corefolder 側では index 4 が欠落として挙がる。
    assert [e["index"] for e in audit_coverage(_EVIDENCE, "corefolder")["missing_body_part"]] == [4]


if __name__ == "__main__":
    test_entries_for_form_keeps_shared_and_drops_other_form()
    test_format_entry_keeps_enum_and_text_values()
    test_normalize_results_fills_missing_and_drops_garbage()
    test_normalize_results_handles_non_list()
    test_palette_source_image_keys_reads_typedef_declaration()
    test_excluded_for_form_keeps_form_neutral_material()
    test_palette_source_image_keys_missing_typedef_returns_empty()
    test_proposal_excludes_common_colors_from_gaps()
    test_normalize_color_suggestions_drops_unknown_words()
    test_char_label_squashes_newlines()
    test_audit_coverage_flags_missing_body_part_per_form()
    print("OK: tests/test_appearance_detail_review.py")
