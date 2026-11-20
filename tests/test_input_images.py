"""入力画像（加筆の起点・赤入れ・構図参考・参考画像）、事前確認（dry_run）、軽い加筆（quick）の回帰テスト。

生成 API・Vision・GCS は呼ばない（生成は偽物に差し替え、GCS の読み取りはメモリー上の値を返す）。
"""
from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from src.mcp_server import output_sink
from src.pipeline import correction_generator, final_generator, image_pipeline, input_images, rough_generator
from src.utils.dataset import find_character

OWN = {"provenance": "own_work"}


def _image(width: int = 64, height: int = 64, fmt: str = "PNG", color=(200, 30, 30, 255)) -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGBA", (width, height), color)
    (image if fmt == "PNG" else image.convert("RGB")).save(buffer, format=fmt)
    return buffer.getvalue()


def _resolve(items, files=None, **options):
    files = files or {}
    return input_images.resolve(items, locate=lambda raw: pytest.fail(f"path を開いた: {raw}"),
                                fetch=lambda key: files[key], **options)


def _materialized(tmp_path: Path, roles=("base", "markup", "composition", "reference"), **options) -> list[dict]:
    files = {role: _image() for role in roles}
    items = [{"object_key": role, "role": role, **OWN, **({"note": "床のタイルの質感"} if role == "reference" else {})}
             for role in reversed(roles)]                       # 渡す順に関係なく、役割の順に添付する
    inputs = _resolve(items, files, **options)
    input_images.materialize(inputs, tmp_path)
    return inputs


class _Painter:
    """``generate_image`` の代わりに呼び出しを記録し、PNG を 1 枚書く。"""

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, num, **kwargs):
        self.calls.append({"num": num, **kwargs})
        out = Path(kwargs["out_dir"]) / f"call{len(self.calls):02d}" / "num057_corefolder_01.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(_image())
        return [out]


@pytest.fixture
def painter(monkeypatch):
    from src.gemini import generate as gemini_generate

    fake = _Painter()
    monkeypatch.setattr(gemini_generate, "generate_image", fake)
    return fake


def _names(paths) -> list[str]:
    return [Path(p).name for p in paths or []]


def test_roles_provenance_and_counts_are_checked_before_generation():
    files = {"base": _image(), "mark": _image(), "tall": _image(64, 80), "near": _image(101, 100),
             "square": _image(100, 100), "jpeg": _image(fmt="JPEG"), "gif": b"GIF89a" + b"\x00" * 32,
             "text": b"not an image at all"}
    ok = _resolve([{"object_key": "jpeg", "role": "reference", "note": "床の  タイルの\n質感", **OWN},
                   {"object_key": "mark", "role": "markup", **OWN},
                   {"object_key": "base", "role": "base", "provenance": "own_generated"}], files)
    assert {image["kind"]: image["stages"] for image in ok} == {"reference": (3, 5), "markup": (3, 4), "base": (3, 5)}
    assert ok[0]["note"] == "床の タイルの 質感" and ok[0]["mime"] == "image/jpeg" and ok[0]["path"] is None
    assert "用途: 床の タイルの 質感" in input_images.label(ok[0])

    def refused(items, expected, **options):
        with pytest.raises(ValueError, match=expected):
            _resolve(items, files, **options)

    # 出所は毎回必須。第三者の素材は、値として用意していない
    refused([{"object_key": "base", "role": "base"}], "provenance")
    refused([{"object_key": "base", "role": "base", "provenance": "licensed_third_party"}], "provenance")
    refused([{"object_key": "base", "role": "object", **OWN}], "role")
    refused([{"object_key": "jpeg", "role": "reference", **OWN}], "note")
    refused([{"object_key": "base", "path": "x.png", "role": "base", **OWN}], "どちらか一方")
    refused([{"role": "base", **OWN}], "どちらか一方")
    refused([{"object_key": "base", "role": "base", **OWN}] * 2, "1 枚まで")
    refused([{"object_key": "jpeg", "role": "reference", "note": "質感", **OWN}] * 4, "3 枚まで")
    # 赤入れは加筆の起点が要る。縦横比が 2% 以上違えば受け付けない
    refused([{"object_key": "mark", "role": "markup", **OWN}], "加筆の起点")
    refused([{"object_key": "base", "role": "base", **OWN}, {"object_key": "tall", "role": "markup", **OWN}], "縦横比")
    _resolve([{"object_key": "square", "role": "base", **OWN}, {"object_key": "near", "role": "markup", **OWN}], files)
    # 中身で形式を判定する
    refused([{"object_key": "gif", "role": "base", **OWN}], "PNG・JPEG・WebP")
    refused([{"object_key": "text", "role": "base", **OWN}], "PNG・JPEG・WebP")


def test_local_paths_are_limited_to_the_output_folder_and_references(tmp_path, monkeypatch):
    out, elsewhere = tmp_path / "output", tmp_path / "elsewhere"
    for folder in (out, elsewhere):
        folder.mkdir()
        (folder / "a.png").write_bytes(_image())
    monkeypatch.setattr(input_images, "references_dir", lambda: tmp_path / "references")
    assert input_images.locate_local(str(out / "a.png"), out) == (out / "a.png").resolve()
    with pytest.raises(ValueError, match="出力フォルダーか references/"):
        input_images.locate_local(str(elsewhere / "a.png"), out)
    with pytest.raises(ValueError, match="見つかりません"):
        input_images.locate_local(str(out / "missing.png"), out)
    monkeypatch.setattr(input_images, "MAX_BYTES", 16)
    with pytest.raises(ValueError, match="MB まで"):
        input_images.resolve([{"path": str(out / "a.png"), "role": "base", **OWN}],
                             locate=lambda raw: input_images.locate_local(raw, out), fetch=None)


def test_markup_is_compared_with_the_iterate_base_and_composition_loses_its_colours(tmp_path):
    previous = tmp_path / "previous.png"
    previous.write_bytes(_image(64, 64))
    files = {"same": _image(128, 128), "wide": _image(128, 64), "guide": _image(color=(10, 200, 10, 128))}
    _resolve([{"object_key": "same", "role": "markup", **OWN}], files, iterate_base=previous)
    with pytest.raises(ValueError, match="縦横比"):
        _resolve([{"object_key": "wide", "role": "markup", **OWN}], files, iterate_base=previous)

    images = _resolve([{"object_key": "guide", "role": "composition", **OWN}], files)
    (record,) = input_images.materialize(images, tmp_path)
    written = tmp_path / record["file"]
    assert record["file"] == "inputs/composition_01.png" and record["grayscale"] and images[0]["path"] == written
    assert record["stages"] == [3] and "data" not in record
    with Image.open(written) as gray:
        assert gray.mode == "L" and gray.size == (64, 64)
        assert gray.getpixel((0, 0)) > 100          # 半透明の部分は白地に重なる（黒くならない）


def test_each_stage_gets_only_the_images_for_its_role(tmp_path, monkeypatch, painter):
    record, inputs = find_character(57), _materialized(tmp_path)
    monkeypatch.setattr(rough_generator, "_generate_adobe_composition_guide", lambda *args, **kwargs: [])
    prompts = {"base_gemini": "BASE PROMPT"}

    # Stage 3: 起点 → 赤入れ → 構図参考 →（公式）→ 参考画像
    rough = rough_generator.generate_rough_images(
        record, "corefolder", prompts=prompts, pipeline_dir=tmp_path, count=1, revisions="表情を笑顔に",
        iterate_from="output/older_run", inputs=inputs)
    stage3 = painter.calls[-1]
    assert _names([stage3["iterate_from"]]) == ["base_01.png"]            # 役割 base は、改稿の起点より優先する
    assert _names(stage3["extra_ref_locals"]) == ["markup_01.png", "composition_01.png"]
    assert _names(stage3["trailing_ref_locals"]) == ["reference_01.png"]
    labels = {Path(path).name: text for path, text in stage3["ref_label_overrides"].items()}
    assert labels["base_01.png"].startswith("加筆の起点") and labels["markup_01.png"].startswith("赤入れ")
    assert labels["composition_01.png"].startswith("構図参考") and "用途: 床のタイルの質感" in labels["reference_01.png"]
    prompt = stage3["prompt_override"]
    assert prompt.startswith("[入力画像の扱い]") and prompt.endswith("BASE PROMPT")
    assert "赤入れの指示と [修正指示] だけを反映する" in prompt and "- 修正: 表情を笑顔に" in prompt
    assert "公式原典と設定資料が正しい" in prompt and "色を抜いてある" in prompt and "用途にだけ使う" in prompt

    # Stage 4: 検査に渡すのは赤入れだけ
    seen = {}

    def analyze(image_path, spec, ref_image_path=None, markup_path=None):
        seen["markup"] = markup_path
        return {"violations": [], "missing": [], "composition_issues": [], "overall_ok": True, "skipped": False}

    monkeypatch.setattr(correction_generator, "_analyze_rough_with_openai", analyze)
    corrected = correction_generator.correct_rough_images(
        record, "corefolder", rough_results=rough, char_spec={}, prompts=prompts, pipeline_dir=tmp_path, inputs=inputs)
    assert seen["markup"].name == "markup_01.png" and corrected["passed"] == rough["gemini"]

    # Stage 5: 起点はラフ案の前、参考画像は公式の後ろ。赤入れと構図参考は渡さない
    final = final_generator.generate_final_images(
        record, "corefolder", corrected_results=corrected, pipeline_dir=tmp_path, skip_canva=True,
        prompts=prompts, count=1, inputs=inputs)
    stage5 = painter.calls[-1]
    assert final["all"] and _names(stage5["extra_ref_locals"]) == ["base_01.png", "num057_corefolder_01.png"]
    assert _names(stage5["trailing_ref_locals"]) == ["reference_01.png"]
    assert sorted(_names(stage5["ref_label_overrides"])) == ["base_01.png", "reference_01.png"]
    assert stage5["prompt_override"].startswith("[入力画像の扱い]")
    assert "直した点は、添付のラフ案に従う" in stage5["prompt_override"] and "赤入れ" not in stage5["prompt_override"]

    # 入力画像が無ければ、これまでと同じ呼び出しになる
    rough_generator.generate_rough_images(record, "corefolder", prompts=prompts, pipeline_dir=tmp_path / "plain", count=1)
    plain = painter.calls[-1]
    assert plain["prompt_override"] == "BASE PROMPT" and plain["iterate_from"] is None
    assert plain["extra_ref_locals"] is None and plain["trailing_ref_locals"] is None and plain["ref_label_overrides"] is None


def test_gemini_attaches_inputs_in_role_order_with_their_labels(tmp_path, monkeypatch):
    from google import genai
    from src.gemini import generate as gg

    inputs = _materialized(tmp_path)
    by_kind = {image["kind"]: str(image["path"]) for image in inputs}
    captured = []
    monkeypatch.setenv("GEMINI_API_KEY", "test-not-a-real-key")
    monkeypatch.setattr(genai, "Client", lambda **kw: object())
    monkeypatch.setattr(gg, "_generate_content_with_retry",
                        lambda client, types, model, prompt, parts: (captured.append(parts), (object(), None))[1])
    monkeypatch.setattr(gg, "_extract_generated_image_bytes", lambda response: [_image()])
    assert gg.generate_image(
        57, out_dir=str(tmp_path / "out"), prompt_override="scene", iterate_from=by_kind["base"],
        extra_ref_locals=[by_kind["markup"], by_kind["composition"]], trailing_ref_locals=[by_kind["reference"]],
        ref_label_overrides=input_images.labels(inputs))
    texts = [part.text for part in captured[-1] if part.text]
    assert texts[0].startswith("[参照1｜加筆の起点") and texts[1].startswith("[参照2｜赤入れ")
    assert texts[2].startswith("[参照3｜構図参考") and "公式原典" in texts[3]
    assert "参考画像（用途: 床のタイルの質感）" in texts[-1]                    # 公式の参照より後ろ
    assert len(texts) == sum(1 for part in captured[-1] if part.inline_data)   # どの画像にも役割のラベルが付く


def test_joint_uses_inputs_only_in_the_final_composition(tmp_path, painter):
    previous = tmp_path / "previous.png"
    previous.write_bytes(_image())
    upload = tmp_path / "markup.png"
    upload.write_bytes(_image(128, 128))
    # 合同で赤入れだけを渡すと、改稿の起点が加筆の起点として合成に添えられる
    inputs, records, iterate_from = image_pipeline._prepare_inputs(
        [{"role": "markup", "path": str(upload), **OWN}], str(previous), tmp_path / "run", str(tmp_path), joint=True)
    assert [(r["role"], r["stages"], r["provenance"]) for r in records] == [
        ("base", [5], "own_generated"), ("markup", [5], "own_work")]
    assert iterate_from == str(previous)
    assert input_images.for_stage(inputs, 3) == [] and input_images.for_stage(inputs, 4) == []

    render = tmp_path / "render.png"
    render.write_bytes(_image())
    image_pipeline._compose_multi_char(
        find_character(57), "corefolder", char_renders=[render], composition_prompt="COMPOSE",
        synth_dir=tmp_path / "synth", work_key="#Works_NumberTales", count=1, inputs=inputs, has_revisions=True)
    call = painter.calls[-1]
    assert _names(call["extra_ref_locals"]) == ["base_01.png", "markup_01.png", "render.png"]
    assert call["prompt_override"].startswith("[入力画像の扱い]") and call["prompt_override"].endswith("COMPOSE")
    assert "赤入れの指示と [修正指示] だけを反映する" in call["prompt_override"]

    # 前に添付する入力画像の枚数だけ、合成プロンプトの参照の番号がずれる
    records57 = [find_character(57), find_character(25)]
    forms = {57: "corefolder", 25: "corefolder"}
    shifted = image_pipeline._build_multi_char_composition_prompt(records57, forms, "", has_comp_rough=True, ref_offset=2)
    assert "- 参照3 (構図ガイド)" in shifted and "- 参照4: " in shifted and "- 参照5: " in shifted
    assert "参照4〜5のデザインに忠実に描く" in shifted and "キャラクターの完成イラストに揃える" in shifted
    plain = image_pipeline._build_multi_char_composition_prompt(records57, forms, "", has_comp_rough=True)
    assert "- 参照1 (構図ガイド)" in plain and "参照2以降のデザインに忠実に描く" in plain and "全参照画像に揃える" in plain


def test_invalid_inputs_stop_the_pipeline_before_any_paid_step(tmp_path, monkeypatch, painter):
    monkeypatch.setattr(image_pipeline, "refine_prompt_dual", lambda *a, **k: pytest.fail("Stage 1 へ進んだ"))
    result = image_pipeline.run_image_pipeline(
        num=57, out_dir=str(tmp_path), scene="窓辺", images=[{"role": "markup", "object_key": "x", **OWN}])
    assert result.status == "failed" and "入力画像" in result.errors[0] and not painter.calls
    summary = json.loads((Path(result.pipeline_dir) / "pipeline_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed" and summary["input_images"] == []


def test_dry_run_plans_without_writing_or_calling_apis(tmp_path, monkeypatch, painter):
    files = {"numbertales/uploads/20261120/base.png": _image(), "numbertales/uploads/20261120/pose.png": _image(80, 40)}
    monkeypatch.setattr(output_sink, "read_object", lambda key, max_bytes=0: files[key])
    for name in ("refine_prompt_dual", "generate_random_scene", "collect_character_data"):
        monkeypatch.setattr(image_pipeline, name, lambda *a, **k: pytest.fail("課金のある段階へ進んだ"))
    images = [{"object_key": "numbertales/uploads/20261120/pose.png", "role": "composition", **OWN},
              {"object_key": "numbertales/uploads/20261120/base.png", "role": "base", "provenance": "own_generated"}]

    plan = image_pipeline.plan_pipeline([57], ["corefolder"], revisions="表情を笑顔に", images=images, out_dir=str(tmp_path))
    assert plan["status"] == "dry_run" and plan["pipeline"] == "five-stage" and plan["scene"] == "表情を笑顔に"
    assert [(i["role"], i["stages"], i["grayscale"]) for i in plan["input_images"]] == [
        ("composition", [3], True), ("base", [3, 5], False)]
    (character,) = plan["characters"]
    assert character["num"] == 57 and character["ai_training_gate"]["allowed"] is True
    assert character["base_prompt"].startswith("[入力画像の扱い]") and "[修正指示] だけを反映する" in character["base_prompt"]
    assert "cnsp_imgNTS-57.png" in character["official_references"]
    assert not painter.calls and list(tmp_path.iterdir()) == []            # 何も書かず、何も生成しない

    # 起点があって場面も修正指示も無ければ、起点の場面を保つ。場面も起点も無ければ、本番でランダムに決まる
    assert image_pipeline.plan_pipeline([57], images=images[1:])["scene"] == image_pipeline._KEEP_SCENE
    assert "ランダム" in image_pipeline.plan_pipeline([57])["scene"]
    # 選べる状態と衣装の名前を返す。合同では、入力画像は合成だけで使う
    miko = image_pipeline.plan_pipeline([35], ["humanoid"], costume="miko")["characters"][0]
    assert miko["costume_names"] == ["miko", "usual"] and miko["free_costume_note"] == ""
    joint = image_pipeline.plan_pipeline([25, 57], scene="並んでいる", images=images)
    assert joint["pipeline"] == "joint-five-stage" and [i["stages"] for i in joint["input_images"]] == [[5], [5]]
    assert joint["joint_input_block"].startswith("[入力画像の扱い]")
    assert not joint["characters"][0]["base_prompt"].startswith("[入力画像の扱い]")
    # 検証に通らない入力と、選べない衣装は、生成の前に断る
    with pytest.raises(ValueError, match="加筆の起点"):
        image_pipeline.plan_pipeline([57], images=[{"object_key": "numbertales/uploads/20261120/base.png",
                                                    "role": "markup", **OWN}])
    with pytest.raises(ValueError, match="AI 向けの利用から外している"):
        image_pipeline.plan_pipeline([61], ["humanoid"], costume="idol")


def test_quick_edit_makes_one_call_and_reuses_the_previous_prompt(tmp_path, monkeypatch, painter):
    for name in ("refine_prompt_dual", "generate_random_scene", "collect_character_data", "correct_rough_images"):
        monkeypatch.setattr(image_pipeline, name, lambda *a, **k: pytest.fail("quick が省くはずの段階へ進んだ"))
    previous = tmp_path / "20261120" / "20261120_100000_pipeline_corefolder_num057"
    source = previous / "stage5_final" / "synth" / "run" / "num057_corefolder_01.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(_image())
    (previous / "stage1_prompt").mkdir()
    (previous / "stage1_prompt" / "prompt_base_gemini.txt").write_text("PREVIOUS STAGE1 PROMPT", encoding="utf-8")
    (previous / "pipeline_summary.json").write_text("{}", encoding="utf-8")
    markup = tmp_path / "markup.png"
    markup.write_bytes(_image(128, 128))

    result = image_pipeline.run_quick_edit(
        num=57, out_dir=str(tmp_path), iterate_from=str(source), revisions="表情を笑顔に; 尻尾は元のまま",
        images=[{"role": "markup", "path": str(markup), **OWN}])
    assert result.status == "ok" and len(painter.calls) == 1 and len(result.stage5_paths["all"]) == 1
    call = painter.calls[0]
    assert call["count"] == 1 and call["iterate_from"] == str(source)
    assert _names(call["extra_ref_locals"]) == ["markup_01.png"]
    prompt = call["prompt_override"]
    assert prompt.startswith("[入力画像の扱い]") and prompt.endswith("PREVIOUS STAGE1 PROMPT")
    assert "起点画像（前回生成）に赤で指示を描き込んだもの" in prompt and "- 修正: 尻尾は元のまま" in prompt
    run_dir = Path(result.pipeline_dir)
    assert run_dir.name.endswith("_iter1") and "_pipeline_corefolder_" in run_dir.name and run_dir != previous
    summary = json.loads((run_dir / "pipeline_summary.json").read_text(encoding="utf-8"))
    assert summary["stage1_prompts"]["quick"] is True and summary["stage1_prompts"]["prompt_source"] == "previous_run"
    assert [i["role"] for i in summary["input_images"]] == ["markup"]
    assert (run_dir / "stage1_prompt" / "prompt_base_gemini.txt").read_text(encoding="utf-8") == "PREVIOUS STAGE1 PROMPT"

    # 起点が無ければ生成しない。以前の実行の外の画像が起点なら、土台のプロンプトを組み直す
    missing = image_pipeline.run_quick_edit(num=57, out_dir=str(tmp_path), revisions="表情を笑顔に")
    assert missing.status == "failed" and "起点" in missing.errors[0] and len(painter.calls) == 1
    loose = tmp_path / "loose.png"
    loose.write_bytes(_image())
    fresh = image_pipeline.run_quick_edit(
        num=57, out_dir=str(tmp_path), revisions="表情を笑顔に", images=[{"role": "base", "path": str(loose), **OWN}])
    assert fresh.status == "ok" and fresh.stage1_prompts["prompt_source"] == "base_prompt"
    assert _names([painter.calls[-1]["iterate_from"]]) == ["base_01.png"]
    assert "PREVIOUS STAGE1 PROMPT" not in painter.calls[-1]["prompt_override"]


def test_connector_takes_images_dry_run_and_quick():
    pytest.importorskip("mcp")
    from src.mcp_server import server

    with pytest.raises(ValueError, match="iterate_from か"):
        server.IterateInput(num=57, revisions="表情を笑顔に")
    with pytest.raises(ValueError, match="revisions か"):
        server.IterateInput(num=57, iterate_from="output/run")
    base = {"object_key": "numbertales/uploads/20261120/base.png", "role": "base", "provenance": "own_generated"}
    markup = {**base, "object_key": "numbertales/uploads/20261120/markup.png", "role": "markup"}
    params = server.IterateInput(num=57, images=[base, markup], quick=True)
    assert params.iterate_from == "" and params.revisions == "" and server._images(params)[1]["role"] == "markup"
    with pytest.raises(ValueError):                                   # 出所は決まった値だけ。base64 や URL の欄は無い
        server.GenerateCharacterInput(num=57, images=[{**base, "provenance": "licensed_third_party"}])
    with pytest.raises(ValueError):
        server.GenerateCharacterInput(num=57, images=[{**base, "url": "https://example.com/a.png"}])

    plan = json.loads(asyncio.run(server.numbertales_generate_character(
        server.GenerateCharacterInput(num=57, scene="窓辺で振り返る", dry_run=True))))
    assert plan["status"] == "dry_run" and plan["characters"][0]["num"] == 57
    refused = json.loads(asyncio.run(server.numbertales_generate_character(
        server.GenerateCharacterInput(num=61, form="humanoid", costume="idol", dry_run=True))))
    assert refused["status"] == "error" and "AI 向けの利用から外している" in refused["message"]
