"""課金なし: 画像観察失敗の承認境界と、AIHints 原文の受け渡し。"""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.pipeline import design_reference as dr
from src.pipeline import db_collector
from src.mcp_server.jobs import Job, JobManager


def record():
    return {"data": {"Num": 57}, "ai_training": {"allowed": True},
            "ai_hints": {"common": {"immutable_traits": ["尻尾は7本"]},
                         "forms": {"corefolder": {"description": "球体"}}}}


def test_observation_preserves_hints_and_reuses_same_run(tmp_path, monkeypatch):
    calls = []
    def observe(prompt, refs):
        calls.append(prompt)
        return {"observations": ["耳は上部"], "unknowns": ["背面は不明"],
                "conflicts": [], "sources": ["official.png"]}
    monkeypatch.setattr(dr, "_observe", observe)
    design = dr.collect_design_reference(record(), "corefolder", {}, tmp_path)
    again = dr.collect_design_reference(record(), "corefolder", {}, tmp_path)
    assert design == again and len(calls) == 1
    assert design["ai_hints"]["common"] == record()["ai_hints"]["common"]
    prompts = dr.add_design_reference({"base_gemini": "scene", "ref_urls": []}, {"design_reference": design})
    assert "尻尾は7本" in prompts["base_gemini"] and "耳は上部" in prompts["base_gemini"]
    assert dr.add_design_reference(prompts, {"design_reference": design}) == prompts


def test_other_work_with_ai_hints_uses_hints_as_canon(tmp_path, monkeypatch):
    prompts = []
    monkeypatch.setattr(dr, "_observe", lambda prompt, refs: (
        prompts.append(prompt) or {
            "observations": ["丸い耳"], "unknowns": [], "conflicts": [], "sources": ["official.png"]}))
    character = record()
    character["work_key"] = "#Works_ShauErRiders"

    dr.collect_design_reference(character, "corefolder", {}, tmp_path)

    assert "以下の AIHints 文面が正典です" in prompts[0]
    assert "[DB部位別仕様] が正典です" not in prompts[0]


@pytest.mark.parametrize("change", ["form", "appearance_detail"])
def test_saved_observation_rejects_changed_form_or_part_specification(tmp_path, monkeypatch, change):
    monkeypatch.setattr(dr, "_observe", lambda *a: {
        "observations": ["丸い耳"], "unknowns": [], "conflicts": [], "sources": ["official.png"]})
    record = {
        "work_key": "#Works_ShauErRiders",
        "record_identity": {"index": {"Name": "Mouse"}},
        "data": {"AppearanceDetail": [{
            "Formation": None, "BodyPart": ["#BodyPart_Ear"],
            "Attrs": [{"AttrLabel": "#DesignAttr_Shape", "value_EN": "round"}],
        }]},
    }
    original_detail = dr.build_appearance_detail_block(record, "humanoid")
    dr.collect_design_reference(record, "humanoid", {}, tmp_path)
    meta = json.loads((tmp_path / "design_reference" / "run_meta.json").read_text(encoding="utf-8"))
    assert meta["form"] == "humanoid"
    assert meta["appearance_detail"] == original_detail

    if change == "form":
        form = "corefolder"
    else:
        record["data"]["AppearanceDetail"][0]["Attrs"][0]["value_EN"] = "oval"
        form = "humanoid"
    with pytest.raises(ValueError, match="部位仕様"):
        dr.collect_design_reference(record, form, {}, tmp_path)


def test_openai_correction_uses_record_num_for_character_lookup(tmp_path, monkeypatch):
    from src.pipeline import correction_generator as cg

    record = {"data": {}, "record_identity": {"index": {"Name": "Mouse"}}}
    monkeypatch.setattr(cg, "record_num", lambda value: "Mouse")
    monkeypatch.setenv("OPENAI_CORRECTION_MODEL", "gpt-image-1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-a-real-key")
    monkeypatch.setenv("OPENAI_IMAGE_SLEEP", "0")
    received = {}

    def generate_image_dalle(**kwargs):
        received.update(kwargs)
        return tmp_path / "corrected.png"

    monkeypatch.setattr("src.openai.generate.generate_image_dalle", generate_image_dalle)
    result = cg._apply_correction_openai(
        record, "humanoid", tmp_path / "rough.png", {"violations": ["wrong shape"]},
        tmp_path, "#Works_ShauErRiders", 1,
    )
    assert received["num"] == "Mouse"
    assert "Character #Mouse" in received["prompt_override"]
    assert result == [tmp_path / "corrected.png"]


def test_multi_character_prompt_uses_record_num_for_form_and_part_spec(monkeypatch):
    from src.pipeline import image_pipeline as ip

    record = {
        "data": {"AppearanceDetail": [{
            "Formation": None, "BodyPart": ["#BodyPart_Ear"],
            "Attrs": [{"AttrLabel": "#DesignAttr_Shape", "value_EN": "round"}],
        }]},
        "record_identity": {"index": {"Name": "Mouse"}},
    }
    monkeypatch.setattr(ip, "record_num", lambda value: "Mouse")
    prompt = ip._build_multi_char_composition_prompt(
        [record], {"Mouse": "humanoid"}, "scene",
    )
    assert "- #Mouse: humanoid 形態" in prompt
    assert "#Mouse の部位仕様" in prompt
    assert "- Ear: round" in prompt


def test_failure_waits_and_only_explicit_true_allows_fallback(tmp_path, monkeypatch):
    def fail(*args):
        raise ValueError("参照画像が壊れています")
    monkeypatch.setattr(dr, "_observe", fail)
    def no_answer(warning):
        assert warning["reason"] == "参照画像が壊れています"
        raise dr.ReferenceConfirmationRequired("回答待ち")
    with pytest.raises(dr.ReferenceConfirmationRequired):
        dr.collect_design_reference(record(), "corefolder", {}, tmp_path, no_answer)
    meta_path = tmp_path / "design_reference" / "run_meta.json"
    assert json.loads(meta_path.read_text())["status"] == "awaiting_confirmation"
    monkeypatch.setattr(dr, "_observe", lambda *a: pytest.fail("再開時に抽出を再課金しない"))
    design = dr.collect_design_reference(record(), "corefolder", {}, tmp_path, lambda w: True)
    assert design["fallback"] and not design["observations"]
    assert json.loads(meta_path.read_text())["status"] == "fallback_approved"


@pytest.mark.parametrize("answer", [False, None, "true"])
def test_decline_and_non_boolean_do_not_continue(tmp_path, monkeypatch, answer):
    monkeypatch.setattr(dr, "_observe", lambda *a: (_ for _ in ()).throw(ValueError("失敗")))
    with pytest.raises(dr.ReferenceCancelled):
        dr.collect_design_reference(record(), "corefolder", {}, tmp_path, lambda w: answer)


def test_optout_is_never_sent_to_vision_or_confirmation(tmp_path, monkeypatch):
    monkeypatch.setattr(db_collector, "find_character", lambda *a: record())
    monkeypatch.setattr(db_collector, "apply_generation_gate", lambda *a, **k: (True, {"axis": "rights"}))
    monkeypatch.setattr(db_collector, "collect_design_reference", lambda *a, **k: pytest.fail("opt-out 画像を送信した"))
    assert db_collector.collect_character_data(57, "corefolder", tmp_path) is None


def test_only_db_settings_are_observed(tmp_path, monkeypatch):
    root = tmp_path / "db"
    root.mkdir()
    monkeypatch.setattr(dr, "_creations_db_repo_root", lambda: root)
    monkeypatch.setattr(dr, "_image_category", lambda p: "arts" if "art.png" in p else "concept")
    official = str(root / "setting.png")
    result = dr._official_settings({"local_paths": [official, str(tmp_path / "generated.png"), str(root / "art.png")],
                                    "urls": ["https://evil.example/data/setting.png"]})
    assert result == {"local_paths": [official], "urls": []}


def test_mcp_answers_are_bound_to_job_and_request():
    manager = JobManager(1)
    manager._jobs["job"] = Job("job", "test", {})
    with ThreadPoolExecutor(1) as worker:
        result = worker.submit(manager.confirm_reference, "job", {"reason": "失敗"}, 2)
        deadline = time.monotonic() + 1
        while manager.get("job").confirmation is None and time.monotonic() < deadline:
            threading.Event().wait(.001)
        request_id = manager.get("job").confirmation["request_id"]
        assert not result.done()
        with pytest.raises(ValueError):
            manager.answer_reference("job", "stale-id", True)
        with pytest.raises(ValueError):
            manager.answer_reference("other-job", request_id, True)
        manager.answer_reference("job", request_id, True)
        assert result.result(timeout=1) is True
        with pytest.raises(ValueError):
            manager.answer_reference("job", request_id, True)
    assert manager.confirm_reference("job", {"reason": "失敗"}, timeout=0) is None
    manager._executor.shutdown()


def test_stage_cli_warning_answer_and_resume(tmp_path, monkeypatch):
    from argparse import Namespace
    from src.pipeline import stage_cli
    state_path = tmp_path / "pipeline_state.json"
    state_path.write_text(json.dumps({"num": 57, "form": "corefolder", "work_key": "#Works_NumberTales",
                                      "prompts": {"base_gemini": "scene"}, "stages_done": []}), encoding="utf-8")
    monkeypatch.setattr(db_collector, "find_character", lambda *a: record())
    monkeypatch.setattr(db_collector, "collect_reference_images", lambda *a, **k: {"local_paths": [], "urls": []})
    monkeypatch.setattr(dr, "_observe", lambda *a: (_ for _ in ()).throw(ValueError("画像を取得できません")))
    monkeypatch.setattr("builtins.input", lambda *a: (_ for _ in ()).throw(EOFError()))
    args = Namespace(run_dir=str(tmp_path), reference_decision=None, num=None)
    with pytest.raises(dr.ReferenceConfirmationRequired):
        stage_cli.cmd_stage2(args)
    assert "spec" not in json.loads(state_path.read_text(encoding="utf-8"))
    monkeypatch.setattr(dr, "_observe", lambda *a: pytest.fail("回答時に再観察しない"))
    args.reference_decision = "continue"
    stage_cli.cmd_stage2(args)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["spec"]["design_reference"]["fallback"] is True
    def generate(rec, form, **kwargs):
        assert "尻尾は7本" in kwargs["prompts"]["base_gemini"]
        return {"gemini": [], "all": []}
    monkeypatch.setattr(stage_cli, "generate_rough_images", generate)
    stage_cli.cmd_stage3(Namespace(run_dir=str(tmp_path), count=1, num=None))
    with pytest.raises(SystemExit):
        stage_cli.cmd_stage2(args)  # 同じ警告への二重回答は拒否


def test_mcp_decision_schema_and_log_routing():
    import asyncio
    import sys
    pytest.importorskip("mcp")
    from src.mcp_server.server import ReferenceDecisionInput, _server_lifespan
    with pytest.raises(ValueError):
        ReferenceDecisionInput(job_id="j", request_id="r", proceed="false")
    async def check():
        original = sys.stdout
        async with _server_lifespan(None):
            assert sys.stdout is sys.stderr
        assert sys.stdout is original
    asyncio.run(check())
