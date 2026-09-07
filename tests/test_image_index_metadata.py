"""
tests/test_image_index_metadata.py — image-index.json メタ追従の回帰テスト (GeneratorsAI#20)
Copyright © RadianN_kswg — CC BY-NC 4.0

上流 CreationsAI が image-index.json の配列要素をオブジェクト化し、`category` /
`long_edge_px` / `is_large_original_candidate` を実測値で持つようになった件への追従を守る。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils.dataset import (  # noqa: E402
    _collect_preferred_reference_paths,
    _get_category_priority,
    _image_category,
    _image_index_path,
    _index_entry_path,
    _sort_paths_for_form,
    get_local_image_paths,
)


def _index() -> dict:
    return json.loads(Path(_image_index_path()).read_text(encoding="utf-8"))


def test_index_entries_are_objects_with_metadata():
    """依頼2 (破壊的変更): 要素はオブジェクトで、種別と実測解像度を持つ。"""
    entries = _index()["works"]["#Works_NumberTales"]["images"]
    assert entries and all(isinstance(e, dict) for e in entries)
    first = entries[0]
    assert {"path", "category", "long_edge_px", "is_large_original_candidate"} <= first.keys()


def test_index_entry_path_reads_both_formats():
    """旧形式 (文字列) も読めること — 移行途中のサブモジュールで無言全滅させない。"""
    assert _index_entry_path({"path": "data/a.png"}) == "data/a.png"
    assert _index_entry_path("data/a.png") == "data/a.png"
    assert _index_entry_path({"category": "arts"}) == ""
    assert _index_entry_path(None) == ""


def test_get_local_image_paths_survives_object_entries():
    """オブジェクト化前は `WindowsPath / dict` で TypeError 落ちしていた経路。"""
    paths = get_local_image_paths()
    assert paths and all(p.endswith(".png") or p.endswith(".webp") for p in paths[:5])

    large = get_local_image_paths(large_only=True)
    expected = sum(
        1 for e in _index()["works"]["#Works_NumberTales"]["images"]
        if e.get("is_large_original_candidate")
    )
    assert len(large) == expected < len(paths), "原寸フィルタ (依頼4 の素材選別) が効いていない"


def test_category_comes_from_index_not_path_heuristic():
    """依頼3: 種別は上流 `category` が正典。索引外のパスだけ推定に落ちる。"""
    entries = _index()["works"]["#Works_NumberTales"]["images"]
    base = _PROJECT_ROOT / "_creations-ai" / "creations-db"
    checked = 0
    for entry in entries:
        expected = entry.get("category") or "other"
        assert _image_category(str(base / entry["path"])) == expected
        checked += 1
    assert checked > 100

    # 索引に無いパス (作品共通図・作者指名の原点画像) は推定へフォールバックする
    assert _image_category("/anywhere/origin_refs/concept/x.png") == "concept"
    assert _image_category("/anywhere/nothing/x.png") == "other"


def test_category_priority_uses_upstream_naming():
    """`designalt` / `conceptalt` 表記のままだと上流種別が末尾へ沈む。"""
    for form in ("corefolder", "humanoid"):
        prio = _get_category_priority(form)
        assert "design_alt" in prio and "concept_alt" in prio
        assert "designalt" not in prio and "conceptalt" not in prio
        assert prio["design_alt"] < prio["concept_alt"]


def test_preferred_reference_wins_inside_its_category():
    """`preferred_reference_images` が同種別内の先頭に来る (種別順は動かさない)。"""
    from src.utils.dataset import find_character

    record = find_character(57)
    base = str(_PROJECT_ROOT / "_creations-ai" / "creations-db")
    preferred = _collect_preferred_reference_paths(record, "corefolder", base)
    assert preferred, "#57 の preferred_reference_images が読めていない"

    core_1 = str(Path(base) / "data/Works_NumberTales/Images/DB_Primary/corefolder/57/emstk_corefolderNTS-57-1.png")
    core_2 = str(Path(base) / "data/Works_NumberTales/Images/DB_Primary/corefolder/57/emstk_corefolderNTS-57-2.png")
    concept = str(Path(base) / "data/Works_NumberTales/Images/DB_Primary/concept/cnsp_imgNTS-57.png")
    assert core_1 in preferred and core_2 not in preferred

    ranked = _sort_paths_for_form([core_2, core_1, concept], "corefolder", preferred)
    assert ranked[0] == core_1, "代表指定が同種別内で先頭に来ていない"
    assert ranked.index(core_1) < ranked.index(concept), "種別順 (corefolder > concept) が壊れている"
    # preferred 無しなら元順のまま = タイブレークとしてのみ効く
    assert _sort_paths_for_form([core_2, core_1, concept], "corefolder")[0] == core_2


def test_capabilities_expose_ai_hints_source():
    """run_meta.json から AIHints の出所 (上流整備 / 最小 scaffold) を追えること。"""
    from src.utils.dataset import collect_record_capabilities, find_character

    caps = collect_record_capabilities(find_character(57), form="corefolder")
    assert caps["ai_hints_source"] in {"source", "derived", None}
    assert caps["ai_hints_source"] == "source"
