"""状態（state）と衣装（costume）の指定の回帰テスト。生成 API は呼ばない。"""
from __future__ import annotations

import pytest

from src.pipeline import image_pipeline
from src.utils import dataset
from src.utils.dataset import (
    build_appearance_detail_block, character_selection, costume_names, find_character, resolve_target, state_names,
)

NTS = "#Works_NumberTales"


def _block(num, work=NTS, form="humanoid", **chosen) -> str:
    with character_selection({(work, num): chosen}):
        return build_appearance_detail_block(find_character(num, work), form)


def test_costume_named_in_the_db_replaces_the_usual_outfit():
    assert costume_names(35) == ["miko", "usual"]
    usual, miko = _block(35), _block(35, costume="miko")
    assert "(usual)" in usual and "(miko)" not in usual and "[状態と衣装の指定]" not in usual
    assert "(miko)" in miko and "(usual)" not in miko
    assert "- 衣装: miko（設定資料にある衣装）" in miko and "違反や欠落に数えない" in miko
    assert "_selection" not in find_character(35)                  # 指定の無い実行のレコードは、これまでと同じ


def test_free_text_changes_only_body_type_and_worn_items():
    free = _block(35, state="寝起きで  ぼんやり", costume="黒いワンピース")
    assert "- 状態の指定: 寝起きで ぼんやり" in free and "- 衣装の指定: 黒いワンピース" in free
    assert "変えてよいのは、体型と衣装・着用物だけ" in free and "(usual)" in free
    assert "着脱できる設定の着用物は無い" in free
    blazer = _block(14, state="ブレザーを脱いでいる")
    assert "外してよい着用物は、着脱できる設定のもの（" in blazer and "ブレザー" in blazer.split("外してよい着用物")[1]


def test_state_named_in_the_db_is_drawn_and_the_default_state_is_set_aside():
    num, form, work = resolve_target("SAR-EZ6", "humanoid")
    assert state_names(find_character(num, work)) == ["beasted", "normal"]
    default, beast = _block(num, work, form), _block(num, work, form, state="beasted")
    assert "[別状態 beasted だけの特徴。シーンがこの状態を指定した場合だけ描く]" in default
    assert "別状態 normal" not in default
    assert "[別状態 normal だけの特徴。今回の絵には描かない]" in beast and "別状態 beasted" not in beast
    assert "- 状態: beasted（設定資料にある状態）" in beast


def test_third_party_costume_cannot_be_chosen():
    with pytest.raises(ValueError, match="AI 向けの利用から外している"):
        _block(61, costume="idol")


def test_pipeline_entry_points_scope_the_choice_to_one_run(monkeypatch):
    seen = {}

    def single(*args, **kwargs):
        seen.update(kwargs=kwargs, record=find_character(35, NTS))
        return "single"

    monkeypatch.setattr(image_pipeline, "_run_image_pipeline", lambda num, form="corefolder", work_key=NTS, out_dir=None,
                        scene="", style="", composition="", background="", costume="", **rest:
                        single(num=num, scene=scene, costume=costume))
    assert image_pipeline.run_image_pipeline(num=35, costume="miko", state="眠そうにしている", scene="縁側") == "single"
    assert seen["kwargs"] == {"num": 35, "scene": "縁側; 状態: 眠そうにしている", "costume": ""}   # DB の衣装は LLM へ差分として渡さない
    assert seen["record"]["_selection"]["costume"] == "miko"
    assert "_selection" not in find_character(35, NTS)             # 実行が終われば指定は残らない

    image_pipeline.run_image_pipeline(num=35, costume="黒いワンピース")
    assert seen["kwargs"]["costume"] == "黒いワンピース" and seen["record"]["_selection"]["costume_note"] == "黒いワンピース"

    def combined(nums, form="corefolder", forms=None, work_key=NTS, out_dir=None, scene="", style="",
                 composition="", background="", costume="", **rest):
        seen.update(states=[(find_character(n, work_key).get("_selection") or {}).get("state_note") for n in nums])
        return "combined"

    monkeypatch.setattr(image_pipeline, "_run_combined_pipeline", combined)
    assert image_pipeline.run_combined_pipeline(nums=[25, 57], states=["", "跳ねている"]) == "combined"
    assert seen["states"] == [None, "跳ねている"]
    with pytest.raises(ValueError, match="states"):
        image_pipeline.run_combined_pipeline(nums=[25, 57], states=["a", "b", "c"])


def test_choice_reaches_characters_named_by_a_work_coded_badge(monkeypatch):
    """作品コード付きのバッジ（SAR-EZ6、NTS-35）は、本体が番号と作品キーへ解決してから検索する。指定も同じ鍵に結び付ける。"""
    seen = {}

    def single(num, form="corefolder", work_key=NTS, out_dir=None, scene="", style="", composition="",
               background="", costume="", **rest):
        resolved, _, work = resolve_target(num, form, work_key)
        seen.update(selection=find_character(resolved, work).get("_selection"), costume=costume)

    monkeypatch.setattr(image_pipeline, "_run_image_pipeline", single)
    image_pipeline.run_image_pipeline(num="SAR-EZ6", form="humanoid", state="beasted")
    assert seen["selection"]["state"] == "beasted"
    image_pipeline.run_image_pipeline(num="NTS-35", form="humanoid", costume="miko")
    assert seen["selection"]["costume"] == "miko" and seen["costume"] == ""      # DB の衣装として選ばれる
    image_pipeline.run_image_pipeline(num="2B", form="humanoid", state="寝起き")
    assert seen["selection"]["state_note"] == "寝起き"

    def combined(nums, form="corefolder", forms=None, work_key=NTS, out_dir=None, scene="", style="",
                 composition="", background="", costume="", **rest):
        _, form, work = resolve_target(nums[0], form, work_key)
        seen.update(states=[(find_character(resolve_target(n, form, work)[0], work).get("_selection") or {}).get("state")
                            for n in nums])

    monkeypatch.setattr(image_pipeline, "_run_combined_pipeline", combined)
    image_pipeline.run_combined_pipeline(nums=["SAR-EZ6", "SAR-EZ1"], states=["beasted", ""])
    assert seen["states"] == ["beasted", None]
