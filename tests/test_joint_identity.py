"""合同生成で、識別要素 (番号・ラベル・タグ) が持ち主以外のキャラクターへ写らないようにする仕組みの回帰テスト。

2026-11-20 の合同 (20 とバイナ) で、バイナの「試用」ラベルがハツカにも付いた。生成 API は使わない。
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PIL import Image  # noqa: E402

from src.pipeline import correction_generator as cg  # noqa: E402
from src.pipeline import image_pipeline  # noqa: E402
from src.utils.dataset import find_character  # noqa: E402

WORK = "#Works_NumberTales"


def _png(path: Path) -> Path:
    Image.new("RGB", (8, 8), "white").save(path)
    return path


def test_joint_references_are_labelled_with_their_owner(tmp_path, monkeypatch):
    hatsuka, binor = find_character(20, WORK), find_character("2-alt", WORK)
    renders = [_png(tmp_path / "render_20.png"), _png(tmp_path / "render_2b.png")]
    guide = _png(tmp_path / "guide.png")
    labels = image_pipeline._joint_ref_labels(
        [hatsuka, binor], renders, [["a/attr_numberMarkNTS-20.png"], ["a/attr_tagNTS-2B.png", "a/shared.png"]], guide=guide)
    assert labels[str(renders[0])].startswith("20(ハツカ) の単体レンダー")
    assert labels[str(renders[1])].startswith("バイナ の単体レンダー")
    assert labels["a/attr_tagNTS-2B.png"].startswith("バイナ の公式部位図") and "ほかのキャラクターには描かない" in labels["a/attr_tagNTS-2B.png"]
    assert labels[str(guide)].startswith("構図ガイド")
    both = image_pipeline._joint_ref_labels([hatsuka, binor], renders, [["a/shared.png"], ["a/shared.png"]])
    assert both["a/shared.png"].startswith("20(ハツカ)・バイナ の公式部位図")

    # ラベルは、合成の呼び出しまで届く
    captured: dict = {}
    import src.gemini.generate as gg

    monkeypatch.setattr(gg, "generate_image", lambda **kw: captured.update(kw) or [])
    monkeypatch.setenv("GEMINI_IMAGE_SLEEP", "0")
    image_pipeline._compose_multi_char(
        hatsuka, "corefolder", char_renders=renders, composition_prompt="COMPOSE", synth_dir=tmp_path / "synth",
        work_key=WORK, count=1, detail_refs=["a/attr_tagNTS-2B.png"], ref_labels=labels)
    assert captured["ref_label_overrides"][str(renders[1])].startswith("バイナ の単体レンダー")
    assert captured["ref_label_overrides"]["a/attr_tagNTS-2B.png"].startswith("バイナ の公式部位図")


def test_composition_prompt_names_the_owner_rule_and_an_explicit_reference_range():
    records = [find_character(20, WORK), find_character("2-alt", WORK)]
    forms = {20: "corefolder", "2-alt": "corefolder"}
    for has_guide in (True, False):
        prompt = image_pipeline._build_multi_char_composition_prompt(records, forms, "ソファ", has_comp_rough=has_guide)
        assert "[識別要素の持ち主]" in prompt and "持ち主のキャラクターにだけ描く" in prompt
        assert "以降" not in prompt.split("[キャラクター別形態ルール]")[0]


def test_identity_tags_fall_back_to_form_specific_hints():
    # バイナの common は種族の 1 語だけ。髪・瞳・「試用」ラベルは形態別にしか無い (CreationsDB #67)
    binor = find_character("2-alt", WORK)
    tags = cg._identity_tags(binor, "corefolder")
    for expected in ("Fox", "pale silver-gray long hair", "amber-orange eyes", "試用"):
        assert expected in tags, expected
    assert tags.count("Fox") == 1
    assert cg._identity_tags({"ai_hints": {"common": {"identity_tags": ["fox ears"]}}}, "corefolder") == "fox ears"
    assert cg._identity_tags({}, "humanoid") == ""


def test_joint_mixing_check_reports_marks_drawn_on_the_wrong_character(tmp_path, monkeypatch):
    image = _png(tmp_path / "final.png")
    characters = [(find_character(20, WORK), "corefolder"), (find_character("2-alt", WORK), "corefolder")]
    seen: dict = {}

    def ask(system, content):
        seen.update(system=system, text=content[0]["text"], image=content[1]["image_url"]["url"][:22])
        return {"mixed": ["20(ハツカ) に バイナ の「試用」ラベル", ""]}

    result = cg.check_joint_identity_mixing(image, characters, ask=ask)
    assert result == {"mixed": ["20(ハツカ) に バイナ の「試用」ラベル"], "skipped": False}
    assert "20(ハツカ) (corefolder): 番号 20" in seen["text"] and "バイナ (corefolder): Fox" in seen["text"]
    assert "試用" in seen["text"] and seen["image"] == "data:image/png;base64,"
    assert "2 体でなければ" in seen["text"]            # 体数も見る (構図ラフに顔が 3 つあった)
    assert cg.check_joint_identity_mixing(image, characters, ask=lambda *a: {"mixed": "x"}) == {"mixed": [], "skipped": True}
    assert cg.check_joint_identity_mixing(image, characters, ask=lambda *a: {}) == {"mixed": [], "skipped": True}
    assert cg.check_joint_identity_mixing(image, characters, ask=lambda *a: {"mixed": ["ok", 123]}) == {"mixed": [], "skipped": True}

    def broken(*_args):
        raise RuntimeError("vision down")

    assert cg.check_joint_identity_mixing(image, characters, ask=broken) == {"mixed": [], "skipped": True}
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)      # キーが無ければ呼ばない
    assert cg.check_joint_identity_mixing(image, characters) == {"mixed": [], "skipped": True}
    assert cg.check_joint_identity_mixing(tmp_path / "missing.png", characters, ask=ask)["skipped"] is True


def test_per_character_roughs_are_told_to_draw_one_figure_and_stage4_counts_them(tmp_path, monkeypatch):
    # 2026-11-20 の合同では、「寄り添って寝る」場面を受けたキャラ別のラフに 2 体が描かれ、Stage 4 を素通りした
    note = image_pipeline._solo_rough_note("バイナ")
    assert note.startswith("[このラフに描く人数]")
    assert "バイナ 1 体だけを描く" in note
    assert "原典の指定部位と数を維持" in note and "指定外へ重複" in note
    plan = image_pipeline.plan_pipeline([20, "2-alt"], ["corefolder", "corefolder"], scene="ソファで寄り添って寝る", out_dir=str(tmp_path))
    for character, name in zip(plan["characters"], ("20(ハツカ)", "バイナ")):
        assert character["base_prompt"].startswith(f"[このラフに描く人数]\n- {name} 1 体だけを描く")

    seen: dict = {}

    class _Completions:
        @staticmethod
        def create(**kwargs):
            seen.update(kwargs)
            message = type("M", (), {"content": '{"violations": [], "missing": [], "composition_issues": ["体数: 2 体。1 体だけを描く"]}'})
            return type("R", (), {"choices": [type("C", (), {"message": message})]})

    class _OpenAI:
        def __init__(self, **_kwargs):
            self.chat = type("Chat", (), {"completions": _Completions})

    import openai

    monkeypatch.setattr(openai, "OpenAI", _OpenAI)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    result = cg._analyze_rough_with_openai(_png(tmp_path / "rough.png"), {"form": "corefolder", "char_name": "バイナ"})
    text = seen["messages"][1]["content"][0]["text"]
    assert "体数: <何体いるか>" in text and "重複: <要素>" in text
    assert result["composition_issues"] == ["体数: 2 体。1 体だけを描く"] and result["skipped"] is False


def test_record_identifier_is_not_given_as_the_number_to_draw():
    # 2026-11-21 の合同で、バイナのラフの 1 枚に「Bi 2 alt」と描かれ、Stage 4 も通った。
    # 「番号は厳密に 2-alt」という指定が、描く側にも検査する側にも渡っていた
    from src.utils.dataset import _build_number_print_block

    binor = _build_number_print_block(find_character("2-alt", WORK), "corefolder")
    assert "厳密に" not in binor and 'exactly "2-alt"' not in binor
    assert '識別子 "2-alt" は表記ではない' in binor and "never write it in the image" in binor
    assert "Bi 2 nor" in binor and "表示箇所と数は以下の原典指定に従う" in binor     # 描く表記は原典指定から
    hatsuka = _build_number_print_block(find_character(20, WORK), "corefolder")
    assert '番号は厳密に "20" です' in hatsuka and "識別子" not in hatsuka


def test_joint_check_compares_colours_with_the_single_renders(tmp_path):
    # 2026-11-21 の合同の完成 3 枚目で、バイナの尾がオレンジに、ハツカの首輪が黒になった
    image, render_20, render_2b = (_png(tmp_path / name) for name in ("final.png", "r20.png", "r2b.png"))
    characters = [(find_character(20, WORK), "corefolder"), (find_character("2-alt", WORK), "corefolder")]
    seen: dict = {}

    def ask(system, content):
        seen["content"] = content
        return {"mixed": ["配色: バイナ の 尾 が オレンジ (基準は 銀灰色)"]}

    result = cg.check_joint_identity_mixing(image, characters, ask=ask, renders=[render_20, tmp_path / "missing.png"])
    assert result == {"mixed": ["配色: バイナ の 尾 が オレンジ (基準は 銀灰色)"], "skipped": False}
    texts = [part["text"] for part in seen["content"] if part["type"] == "text"]
    assert "配色: <名前> の <部位>" in texts[0] and texts[1:] == ["20(ハツカ) の単体レンダー (配色の基準。検査対象ではない):"]
    assert sum(part["type"] == "image_url" for part in seen["content"]) == 2      # 開けないレンダーは添付しない
    assert "番号 20; " in texts[0] and "番号 2" not in texts[0].replace("番号 20", "")   # 識別子 (2-alt・2B) は番号として渡さない
    cg.check_joint_identity_mixing(image, characters, ask=ask)
    assert "配色:" not in seen["content"][0]["text"] and len(seen["content"]) == 2     # レンダーが無ければ配色は見ない
