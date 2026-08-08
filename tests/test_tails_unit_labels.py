"""
tests/test_tails_unit_labels.py — TailsUnit の尾形状ラベル解決の回帰テスト。

pytest 非依存で書いてあり、どちらでも走る:
    python tests/test_tails_unit_labels.py   # 自己完結ランナー
    python -m pytest tests/                  # pytest を入れている場合

2026-08-08 の ai-dataset 更新で `#TailShapeType_BirdTailOnly` (888 / 999 / 1111) が
新登場したが `_TAIL_SHAPE_TYPE_LABELS` に無く、`_describe_tails_unit_entry()` が
`("", "")` を返して尾の形状が**黙って消える**状態だった (本数・節数だけが残る)。

正典ラベルを追加したうえで、未知コードは `_hashtag_fallback_label()` で可読ラベルへ
落とすようにした。上流が列挙値を追加しても情報が欠落しないことを固定する。
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.utils.dataset import _describe_tails_unit_entry  # noqa: E402


def test_bird_tail_only_has_canonical_labels() -> None:
    """888 の実データ形状。db_meta の $EnumDef_TailShapeType と同じ文言が出ること。"""
    jp, en = _describe_tails_unit_entry(
        {
            "TailShapeType": "#TailShapeType_BirdTailOnly",
            "Count": 1,
            "Segment": 1,
            "Note_JP": "左右の翼部と尾羽が3つの「8」のような模様をしている",
            "Note_EN": "The left and right wings and tail feathers have a pattern resembling three '8's.",
        }
    )
    assert jp.startswith("尾羽のみ(翼部形状と併せて設計)1本1節"), jp
    assert "Tail feathers only" in en, en
    assert "1 tail, 1 segment" in en, en


def test_unknown_shape_code_falls_back_readable() -> None:
    """未知コードでも形状が欠落せず、可読ラベルへ落ちること。"""
    jp, en = _describe_tails_unit_entry(
        {"TailShapeType": "#TailShapeType_SomeNewShape", "Count": 2}
    )
    assert "some new shape" in jp, jp
    assert "some new shape" in en, en
    assert "2 tails" in en, en


def test_known_fox_branched_is_unchanged() -> None:
    """57 の 7 本枝分かれ。既知コードの文言が従来どおりであること (デグレ防止)。"""
    jp, en = _describe_tails_unit_entry(
        {
            "TailShapeType": "#TailShapeType_FoxBranched",
            "Count": 7,
            "Branches": [
                {"Laterality": "#Lat_Upper", "ClusterCount": 2, "TailCount": 5},
                {"Laterality": "#Lat_Lower", "ClusterCount": 1, "TailCount": 2},
            ],
        }
    )
    assert jp == "キツネ(枝分かれ)型7本(上2束5本+下1束2本)", jp
    assert en == "Fox (branched): 7 tails (upper: 2 clusters x5, lower: 1 cluster x2)", en


def _run() -> int:
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run())
