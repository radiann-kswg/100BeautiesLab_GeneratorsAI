"""全件 manifest の明示検索と、許可済みキャラ列挙を分離する（外部通信なし）。"""
import json

from src.utils import dataset


def test_known_denied_record_never_falls_back_to_api(tmp_path, monkeypatch):
    record = {
        "_type": "character", "work_key": "#Works_NumberTales",
        "data": {"Num": "blocked", "Num_Badge": "12B"},
        "ai_training": {"allowed": False, "reason": "AI_Optout: true"},
    }
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps(record), encoding="utf-8")
    def no_fetch(**kwargs):
        raise AssertionError("denied record must stay local")
    monkeypatch.setattr(dataset, "_fetch_db_record_via_creations_db_pkg", no_fetch)
    monkeypatch.setattr(dataset, "_fetch_record_via_api", no_fetch)

    found = dataset.find_character("12B", manifest_path=str(manifest))
    assert found == record
    assert dataset.generation_permitted(found)[0] == "refuse"
    assert dataset.get_characters(str(manifest)) == []


def test_unready_badge_is_resolved_locally_but_not_enumerated(tmp_path, monkeypatch):
    record = {
        "_type": "character", "work_key": "#Works_NumberTales",
        "data": {"Num": "10-alt", "Num_Badge": "10D"},
        "ai_training": {"allowed": False, "reason": "AI_Unready; NOT a rights-based opt-out"},
        "ai_hints": {"forms": {"corefolder": {"ai_tags": ["spherical body"]}}},
    }
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setattr(dataset, "_fetch_db_record_via_creations_db_pkg", lambda **kw: None)
    def no_fetch(**kwargs):
        raise AssertionError("unready record is already in the local manifest")
    monkeypatch.setattr(dataset, "_fetch_record_via_api", no_fetch)

    found = dataset.find_character("10D", manifest_path=str(manifest))
    assert found == record
    assert dataset.generation_permitted(found)[0] == "warn"
    assert dataset.get_characters(str(manifest)) == []
    assert dataset.resolve_badge("10D", "#Works_Other", str(manifest)) == "10D"
