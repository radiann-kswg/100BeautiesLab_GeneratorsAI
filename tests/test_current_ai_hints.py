"""課金なし: 構造再同期された AIHints と旧 Vision 説明を混在させない。"""
import copy
import json

import pytest

from src.utils import dataset
from src.pipeline import db_collector, design_reference
from src.pipeline.text_pipeline import _build_char_summary


def current_record():
    return {
        "data": {"Num": 57}, "ai_training": {"allowed": True},
        "ai_hints": {
            "common": {"identity_tags": ["yellow-green irises with blue pupils"]},
            "forms": {"humanoid": {
                "ai_tags": ["humanoid form", "yellow-green irises with blue pupils",
                            "yellow long-sleeved top", "long olive-green skirt"],
                "natural_language_description": "amber eyes, orange shorts",
                "outfit_features": ["orange shorts", "yellow boots"],
                "silhouette_notes": {"body_description": ["amber eyes", "yellow blazer"]},
                "negative_visuals": [], "negative_prompt_export": "",
            }},
        },
    }


@pytest.fixture(autouse=True)
def no_reference_scan(monkeypatch):
    monkeypatch.setattr(dataset, "collect_reference_images", lambda *a, **k: {"local_paths": [], "urls": []})


@pytest.mark.parametrize("builder", [dataset.build_dalle_prompt, dataset.build_gemini_prompt,
                                    dataset.build_novelai_prompt])
def test_current_tags_replace_old_description_in_every_prompt(builder):
    record = current_record()
    before = copy.deepcopy(record)
    result = builder(record, "humanoid")
    prompt = result if isinstance(result, str) else result.get("prompt", result.get("positive"))
    for tag in record["ai_hints"]["forms"]["humanoid"]["ai_tags"]:
        assert tag in prompt
    for stale in ("amber eyes", "orange shorts", "yellow boots", "yellow blazer", "合計 7 本"):
        assert stale not in prompt
    assert record == before
    assert "long olive-green skirt" in _build_char_summary(record, "humanoid")


def test_explicit_corefolder_tags_survive_filters_and_conflicting_negatives():
    record = {"data": {"Num": 1}, "ai_hints": {"forms": {"corefolder": {
        "ai_tags": ["corefolder form", "light pink hooded top"],
        "negative_visuals": [" LIGHT PINK HOODED TOP ", "extra arms"],
        "negative_keywords": ["light pink hooded top"],
        "negative_prompt_export": "light pink hooded top, extra arms",
    }}}}
    view = dataset.generation_ai_hints(record)["forms"]["corefolder"]
    assert view["negative_visuals"] == ["extra arms"]
    assert view["negative_keywords"] == []
    assert dataset.build_novelai_prompt(record)["negative"] == "extra arms"
    for builder in (dataset.build_dalle_prompt, dataset.build_gemini_prompt):
        result = builder(record)
        prompt = result if isinstance(result, str) else result["prompt"]
        assert "light pink hooded top" in prompt.split("[今回の姿]", 1)[1].split("[番号印字仕様", 1)[0]


def test_missing_ai_tags_keeps_legacy_fallback():
    record = current_record()
    del record["ai_hints"]["forms"]["humanoid"]["ai_tags"]
    assert dataset.generation_ai_hints(record) == record["ai_hints"]
    assert "orange shorts" in dataset.build_dalle_prompt(record, "humanoid")


def test_placeholder_does_not_discard_valid_tags():
    record = current_record()
    record["ai_hints"]["forms"]["humanoid"]["ai_tags"].append("TODO: 1girl|1boy|1other")
    record["ai_hints"]["common"]["natural_language_description"] = "TODO: appearance"
    record["ai_hints"]["common"]["silhouette_features"] = ["TODO: eye color"]
    record["db_record"] = {"AIHints": copy.deepcopy(record["ai_hints"])}
    for builder in (dataset.build_dalle_prompt, dataset.build_gemini_prompt, dataset.build_novelai_prompt):
        result = builder(record, "humanoid")
        prompt = result if isinstance(result, str) else result.get("prompt", result.get("positive"))
        assert "long olive-green skirt" in prompt
        assert "TODO:" not in prompt
    design = {"ai_hints": {"common": record["ai_hints"]["common"],
                            "form": record["ai_hints"]["forms"]["humanoid"]}, "form": "humanoid"}
    assert "TODO:" not in design_reference.design_reference_block(design)


def test_stage2_keeps_raw_log_but_only_sends_current_view(tmp_path, monkeypatch):
    record = current_record()
    captured = []
    def observe(prompt, refs):
        captured.append(prompt)
        return {"observations": [], "unknowns": [], "conflicts": [], "sources": []}
    monkeypatch.setattr(design_reference, "_observe", observe)
    design = design_reference.collect_design_reference(record, "humanoid", {}, tmp_path)
    assert "long olive-green skirt" in captured[0] and "orange shorts" not in captured[0]
    log = json.loads((tmp_path / "design_reference" / "run_meta.json").read_text(encoding="utf-8"))
    assert log["ai_hints"]["form"]["outfit_features"] == ["orange shorts", "yellow boots"]
    assert log["generation_ai_hints"]["form"]["outfit_features"] == []
    assert design["ai_hints"] == log["ai_hints"]
    for prompt in (design_reference.design_reference_block(design),
                   design_reference.add_design_reference({"base_gemini": "scene"}, {"design_reference": design})["base_gemini"]):
        assert "long olive-green skirt" in prompt and "orange shorts" not in prompt
    spec = db_collector._build_character_spec(record, "humanoid")
    assert spec["ai_tags"] == record["ai_hints"]["forms"]["humanoid"]["ai_tags"]
