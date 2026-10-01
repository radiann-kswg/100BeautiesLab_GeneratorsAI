"""公式部位画像と番号字形が生成・検査へ届くことを API 課金なしで確認する。"""
from pathlib import Path



import base64
import copy
import json
from argparse import Namespace
from types import SimpleNamespace as NS

import pytest

from src.utils.dataset import (
    IMAGE_TEXT_POLICY, _collect_appearance_detail_images, _creations_db_repo_root,
    _build_number_print_block, collect_reference_images, find_character, build_gemini_prompt,
    build_dalle_prompt, is_detail_reference,
)


def _submodule_ready() -> bool:
    """creations-db サブモジュール/manifest が揃っているか (未配置環境では skip)。"""
    try:
        return find_character(93) is not None
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(
    not _submodule_ready(),
    reason="_creations-ai サブモジュール/manifest 未配置環境では実データ依存テストを skip",
)


def test_kumi_number_mark_is_selected_for_both_forms():
    record = find_character(93)
    for form in ("corefolder", "humanoid"):
        refs = collect_reference_images(record, form)
        assert any(Path(p).name == "attr_numberMarkNTS-93.png"
                   for p in refs["local_paths"][:3])


def test_detail_binding_respects_form_real_name_and_work():
    record = copy.deepcopy(find_character(93))
    entry = record["db_record"]["AppearanceDetail"][0]
    entry["Formation"] = "humanoid"
    record["db_record"]["AppearanceDetail"] = [entry]
    record["data"]["AppearanceDetail"] = [entry]
    assert not any(is_detail_reference(p) for p in collect_reference_images(record, "corefolder")["local_paths"])
    assert any("attr_numberMarkNTS-93.png" in p
               for p in collect_reference_images(record, "humanoid")["local_paths"])
    entry["img_PNGName"] = "attr_numberMarkNTS-999999"
    assert _collect_appearance_detail_images(record, "humanoid", str(_creations_db_repo_root())) == []
    entry["img_PNGName"] = "attr_numberMarkNTS-93"
    record["work_key"] = "#Works_Missing"
    assert _collect_appearance_detail_images(record, "humanoid", str(_creations_db_repo_root())) == []


@pytest.mark.parametrize("num", [11, 22, 28, 71, 93, 97])
def test_declared_detail_images_survive_selection(num):
    record = find_character(num)
    for form in ("corefolder", "humanoid"):
        expected = _collect_appearance_detail_images(record, form, str(_creations_db_repo_root()))
        assert expected
        refs = collect_reference_images(record, form)
        assert set(expected) <= set(refs["local_paths"])
        assert not is_detail_reference(refs["local_paths"][0]), "全体図より部位図を先頭にしない"


def test_prompts_preserve_stylized_mark_and_full_applicable_detail():
    record = find_character(93)
    for text in (build_gemini_prompt(record)["prompt"], build_dalle_prompt(record)):
        assert IMAGE_TEXT_POLICY in text
        assert "Arabic numeral '93' (stylized motif)" in text
        assert "attr_numberMarkNTS-93" in text
        assert "- Chest / NumberMark:" in text  # 平文化した部位仕様 (生 JSON の語彙トークンは送らない)
        assert "- Waist" not in text  # humanoid 限定の部位は corefolder に混ぜない
        assert "not as stylized shapes" not in text
        assert "一切描かないこと" not in text
    assert "汎用フォント" in _build_number_print_block(record, "corefolder")


def _mock_vision(monkeypatch, captured, result):
    import openai
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-a-real-key")
    def create(**kwargs):
        captured.append(kwargs["messages"][-1]["content"])
        return NS(choices=[NS(message=NS(content=json.dumps(result)))])
    monkeypatch.setattr(openai, "OpenAI", lambda **kw: NS(chat=NS(completions=NS(create=create))))


def _image_payloads(content):
    return [p["image_url"]["url"] for p in content if p["type"] == "image_url"]


def test_stage2_and_stage4_receive_actual_detail_bytes(tmp_path, monkeypatch):
    from src.pipeline import db_collector, correction_generator as cg, design_reference as dr
    record = find_character(93)
    refs = collect_reference_images(record)
    mark = next(Path(p) for p in refs["local_paths"] if is_detail_reference(p))
    expected = "data:image/png;base64," + base64.b64encode(mark.read_bytes()).decode("ascii")
    captured = []
    _mock_vision(monkeypatch, captured, {
        "observations": ["番号は固有字形"], "unknowns": [], "conflicts": [],
        "missing": ["番号の字形が原典と違う"], "violations": [],
        "composition_issues": [], "overall_ok": False,
    })
    collected = db_collector.collect_character_data(93, "corefolder", tmp_path)
    assert str(mark) in collected["spec"]["design_reference"]["sources"]
    assert expected in _image_payloads(captured[-1])
    analysis = cg._analyze_rough_with_openai(
        Path(refs["local_paths"][2]), collected["spec"], Path(refs["local_paths"][0]))
    assert not analysis["skipped"]
    assert expected in _image_payloads(captured[-1])
    assert "線幅・間隔・切れ目" in captured[-1][0]["text"]
    # ローカル画像なしの URL フォールバックも役割ラベル付きで動作する。
    url = next(u for u in refs["urls"] if is_detail_reference(u))
    dr._observe("test", {"urls": [url]})
    assert _image_payloads(captured[-1]) == [url]


@pytest.mark.parametrize("num,mode", [(93, "rough"), (93, "final"), (28, "final"), (93, "iterate")])
def test_gemini_payload_keeps_details_after_guides(tmp_path, monkeypatch, num, mode):
    from google import genai
    from src.gemini import generate as gg
    record = find_character(num)
    refs = collect_reference_images(record)
    expected = [Path(p).read_bytes() for p in refs["local_paths"] if is_detail_reference(p)]
    captured = []
    monkeypatch.setenv("GEMINI_API_KEY", "test-not-a-real-key")
    monkeypatch.setattr(genai, "Client", lambda **kw: object())
    monkeypatch.setattr(gg.requests, "get", lambda *a, **kw: pytest.fail("ローカルにある公式画像を再取得"))
    def generate(client, types, model, prompt, parts):
        captured.append((prompt, parts))
        return object(), None
    monkeypatch.setattr(gg, "_generate_content_with_retry", generate)
    monkeypatch.setattr(gg, "_extract_generated_image_bytes", lambda response: [expected[0]])
    monkeypatch.setattr(gg, "_generate_images_with_retry", lambda *a: pytest.fail("参照なし生成に脱落"))
    guide = tmp_path / "guide.png"
    guide.write_bytes(expected[0])
    guide2 = tmp_path / "guide2.png"
    guide2.write_bytes(expected[0])
    kwargs = {"extra_ref_locals": [str(guide), str(guide2)]} if mode != "iterate" else {"iterate_from": str(guide)}
    assert gg.generate_image(num, out_dir=str(tmp_path / "out"), prompt_override="scene", **kwargs)
    prompt, parts = captured[-1]
    payloads = [p.inline_data.data for p in parts if p.inline_data]
    # 同じバイトのガイドと区別するため、公式部位図ラベルの直後の画像を検証する。
    detail_bytes = [parts[i + 1].inline_data.data for i, p in enumerate(parts)
                    if p.text and "公式部位図" in p.text]
    assert len(detail_bytes) == len(expected), "部位図をURLから二重添付しない"
    assert all(raw in detail_bytes for raw in expected)
    assert len(payloads) >= len(expected) + 2
    assert "番号印字仕様" in prompt and IMAGE_TEXT_POLICY in prompt
    assert "[DB部位別仕様]" in prompt


def test_openai_edit_receives_all_declared_details(tmp_path, monkeypatch):
    import openai
    from src.openai.generate import generate_image_dalle
    record = find_character(28)
    refs = collect_reference_images(record)
    expected = [Path(p).read_bytes() for p in refs["local_paths"] if is_detail_reference(p)]
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-a-real-key")
    def edit(**kw):
        assert IMAGE_TEXT_POLICY in kw["prompt"]
        assert "[DB部位別仕様]" in kw["prompt"]
        payloads = [f.getvalue() for f in kw["image"]]
        assert all(raw in payloads for raw in expected)
        return NS(data=[NS(b64_json=base64.b64encode(expected[0]).decode("ascii"))])
    monkeypatch.setattr(openai, "OpenAI", lambda **kw: NS(images=NS(edit=edit)))
    assert generate_image_dalle(28, out_dir=str(tmp_path), model="gpt-image-1", prompt_override="fix")


def test_combined_stage_cli_passes_each_character_detail(tmp_path, monkeypatch):
    from src.pipeline import stage_cli
    chars = {}
    for num in (57, 93):
        record = find_character(num)
        refs = collect_reference_images(record)
        chars[str(num)] = {"record": record, "best": [refs["local_paths"][0]],
                           "spec": {"detail_reference_paths": [p for p in refs["local_paths"]
                                                                if is_detail_reference(p)]}}
    state = {"mode": "combined", "nums": [57, 93], "form": "corefolder",
             "work_key": "#Works_NumberTales", "chars": chars, "stages_done": []}
    (tmp_path / "pipeline_state.json").write_text(json.dumps(state), encoding="utf-8")
    captured = {}
    def compose(*args, **kwargs):
        captured.update(kwargs)
        return []
    monkeypatch.setattr(stage_cli, "_compose_multi_char", compose)
    stage_cli.cmd_stage5(Namespace(run_dir=str(tmp_path), count=1))
    assert {Path(p).name for p in captured["detail_refs"]} == {
        "attr_numberMarkNTS-57.png", "attr_numberMarkNTS-93.png"}
    assert "attr_numberMarkNTS-93" in captured["composition_prompt"]


def test_lilith_number_motifs_are_not_restricted_to_one_location():
    text = _build_number_print_block(find_character(666), "corefolder")
    assert "halo, brooch, and wings" in text
    assert "1 か所" not in text
    assert "指定された複数部位や回転配置を保持" in text
