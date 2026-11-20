"""NumberTales 以外の作品 (獣爾騎兵・豹変系女子) をバッジで指定して生成経路へ通す回帰テスト (課金なし)。"""
import json

import pytest

from src import batch_generate
from src.pipeline import db_collector
from src.pipeline import design_reference as dr
from src.utils.dataset import (
    build_dalle_prompt, build_gemini_prompt, find_character, get_characters, record_badge,
    record_num, resolve_target,
)
from src.utils.paths import build_run_output_dir

_NTS, _SAR, _SCG = "#Works_NumberTales", "#Works_ShauErRiders", "#Works_SinisterChangingGirls"


def _manifest_ready() -> bool:
    try:
        return find_character("Mouse", _SAR) is not None
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(
    not _manifest_ready(),
    reason="_creations-ai サブモジュール/manifest 未配置環境では実データ依存テストを skip",
)


def test_badges_follow_the_upstream_declaration():
    # 作品別 db_type.json の $IndexDef.$badge どおり: Num_Badge / 辞書の Beast_Badge / 方位そのまま
    assert record_badge(find_character(57)) == "57"
    assert record_badge(find_character("2-alt")) == "2B"
    assert record_badge(find_character("Mouse", _SAR)) == "EZ1"
    assert record_badge(find_character("ENE", _SCG)) == "ENE"
    # 許可済みキャラクターは全員、作品コード付きのバッジ 1 語で本人に届く
    codes = {_NTS: "NTS", _SAR: "SAR", _SCG: "SCG"}
    # 同じ識別子 "W" を別 DB に持つ豹変系女子は、後ろの DB をバッジで指す
    assert find_character(resolve_target("SCG-W")[0], _SCG)["db_key"] == "#DB_Primary"
    assert find_character(resolve_target("SCG-AW")[0], _SCG)["db_key"] == "#DB_Regioministrators"
    for record in get_characters():
        code = codes.get(record["work_key"])
        if not code or str(record_badge(record)).isdigit():
            continue  # 数字だけのバッジは従来の Num 照合 ("0" と "000" の int 一致は既存仕様)
        num, _form, work = resolve_target(f"{code}-{record_badge(record)}")
        assert work == record["work_key"] and find_character(num, work)["id"] == record["id"], record["id"]


@pytest.mark.parametrize("args, expected", [
    ((57,), (57, "corefolder", _NTS)),
    (("NTS-2B",), ("2-alt", "corefolder", _NTS)),
    (("2-alt",), ("2-alt", "corefolder", _NTS)),          # ハイフン入りの Num は作品コードと取り違えない
    (("EZ1", "corefolder", _SAR), ("Mouse", "humanoid", _SAR)),
    (("sar-ez13",), ("Cat", "humanoid", _SAR)),           # 作品コードから作品を決める。大小文字は問わない
    (("Mouse", "humanoid", _SAR), ("Mouse", "humanoid", _SAR)),
    (("SCG-ENE", "corefolder"), ("ENE", "humanoid", _SCG)),
    (("XX-1",), ("XX-1", "corefolder", _NTS)),            # 未知のコードはそのまま (見つからない扱いになる)
])
def test_resolve_target_maps_badges_to_internal_values(args, expected):
    assert resolve_target(*args) == expected
    assert resolve_target(*resolve_target(*args)) == expected   # 解決済みの値を通しても変わらない


def test_other_work_prompts_drop_numbertales_rules_and_keep_story_states():
    mouse = find_character("Mouse", _SAR)
    assert record_num(mouse) == "Mouse" and "Num" not in mouse["data"]
    for prompt in (build_gemini_prompt(mouse, "humanoid", scene="x")["prompt"],
                   build_dalle_prompt(mouse, "humanoid", scene="x")):
        assert "corefolder" not in prompt and "私服" not in prompt and "番号印字仕様" not in prompt
        # 2026-11-19 の上流で獣爾騎兵にも AIHints が入った。有無に応じて正典の書き方が変わる
        assert ("AIHints を正典とし" if mouse.get("ai_hints") else "AIHints を持たない作品のため") in prompt
        assert "Mouse (large and round)" in prompt and "count: 1" in prompt
        assert "共通配色の上書き #408784" in prompt
    runo = build_gemini_prompt(find_character("E", _SCG), "humanoid", scene="x")["prompt"]
    assert "- Eye / Both / Motif: reddish orange" in runo                      # 豹変前は通常の項目
    fox = [line for line in runo.splitlines() if "Fox" in line]
    assert fox and all(line.startswith("- [別状態 afterChanged だけの特徴。") for line in fox)
    izuna = build_gemini_prompt(find_character(57), "humanoid", scene="x")["prompt"]
    assert "私服寄りの humanoid 表現を優先すること" in izuna and "AIHints を正典とし" in izuna
    assert "別状態" not in izuna


def test_default_states_are_drawn_as_ordinary_entries():
    from src.utils.dataset import build_appearance_detail_block
    block = build_appearance_detail_block({"data": {"AppearanceDetail": [
        {"Formation": "normal", "BodyPart": ["#BodyPart_Tail"], "Attrs": [{"value_EN": "snake tail"}]},
        {"Formation": "beasted", "BodyPart": ["#BodyPart_Arm"], "Attrs": [{"value_EN": "scaled arms"}]},
    ]}}, "humanoid")
    assert "- Tail: snake tail" in block                           # 獣化前は通常の項目
    assert "- [別状態 beasted だけの特徴。" in block


def test_stage2_uses_appearance_detail_as_canon_only_for_works_without_ai_hints(tmp_path, monkeypatch):
    prompts = []

    def observe(prompt, refs):
        prompts.append(prompt)
        return {"observations": ["丸い耳"], "unknowns": [], "conflicts": [], "sources": ["official.png"]}

    monkeypatch.setattr(dr, "_observe", observe)
    data = db_collector.collect_character_data("Mouse", "humanoid", tmp_path / "sar", _SAR)
    assert data["spec"]["char_num"] == "Mouse" and data["spec"]["work_title"] == "獣爾騎兵"
    assert data["spec"]["design_reference"]["observations"] == ["丸い耳"]
    assert "[DB部位別仕様] が正典" in prompts[0] and "#Mouse" not in prompts[0]
    summary = json.loads((tmp_path / "sar" / "stage2_db" / "db_summary.json").read_text(encoding="utf-8"))
    assert summary["num"] == "Mouse" and summary["reference_local_count"] >= 1
    # NumberTales は AIHints が正典のまま。無ければ観察へ進まず確認待ちになる
    bare = {"data": {"Num": 57, "AppearanceDetail": [{"BodyPart": ["#BodyPart_Ear"], "Attrs": [{"value_EN": "fox"}]}]},
            "ai_training": {"allowed": True}}

    def no_answer(warning):
        assert warning["reason"] == "CreationsAI の AIHints がありません"
        raise dr.ReferenceConfirmationRequired("回答待ち")

    with pytest.raises(dr.ReferenceConfirmationRequired):
        dr.collect_design_reference(bare, "humanoid", {}, tmp_path / "nts", no_answer)
    assert len(prompts) == 1


def test_pipeline_carries_an_other_work_badge_through_the_stages(tmp_path, monkeypatch):
    """作品コード付きのバッジ 1 語で、Stage 1〜3 の入口まで作品・識別子・形態が揃って届く (API は偽物)。"""
    from pathlib import Path

    from src.pipeline import image_pipeline as ip

    monkeypatch.setattr(dr, "_observe", lambda prompt, refs: {
        "observations": ["丸い耳"], "unknowns": [], "conflicts": [], "sources": ["official.png"]})
    monkeypatch.setattr(ip, "generate_random_scene", lambda record, form: "訓練場で構えているシーン")
    monkeypatch.setattr(ip, "refine_prompt_dual", lambda record, form, **kw: {
        "openai": "p", "gemini": "p", "base_gemini": "p", "base_dalle": "p", "ref_urls": [], "ref_locals": []})
    seen = {}

    def rough(record, form, **kwargs):
        seen["rough"] = (record_num(record), form, kwargs["work_key"])
        return {"all": []}      # ラフを返さず、Stage 3 で止める

    monkeypatch.setattr(ip, "generate_rough_images", rough)
    result = ip.run_image_pipeline("SAR-EZ1", out_dir=str(tmp_path), skip_canva=True)
    assert (result.num, result.form, result.work_key) == ("Mouse", "humanoid", _SAR)
    assert seen["rough"] == ("Mouse", "humanoid", _SAR) and result.status == "partial"
    run_dir = Path(result.pipeline_dir)
    assert run_dir.name.endswith("_pipeline_humanoid_numMouse")
    summary = json.loads((run_dir / "stage2_db" / "db_summary.json").read_text(encoding="utf-8"))
    assert (summary["num"], summary["num_badge"], summary["form"]) == ("Mouse", "EZ1", "humanoid")


def test_run_names_and_batch_plan_use_the_resolved_identity(tmp_path, capsys):
    run_dir = build_run_output_dir("pipeline", *resolve_target("SAR-EZ1")[:2], base_dir=tmp_path, create=False)
    assert run_dir.name.endswith("_pipeline_humanoid_numMouse")
    results = batch_generate.run_batch(["SAR-EZ1", "ez4"], ["corefolder", "humanoid"], ["gemini"], dry_run=True)
    assert [(r.num, r.form, r.detail) for r in results] == [
        ("Mouse", "humanoid", "dry-run"), ("Rabbit", "humanoid", "dry-run")]
    assert "NOT_FOUND" not in capsys.readouterr().out
