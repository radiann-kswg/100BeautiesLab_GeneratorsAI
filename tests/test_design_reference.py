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
