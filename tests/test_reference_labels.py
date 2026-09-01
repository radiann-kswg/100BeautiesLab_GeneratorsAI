"""
tests/test_reference_labels.py — 参照画像の役割ラベル + Stage4 欠落検出の回帰テスト
Copyright © RadianN_kswg — CC BY-NC 4.0

API へ渡す参照画像が「無名のバイト列の並び」に戻り、ラフ/起点画像と公式原典の区別が
モデルから見えなくなること (蛇足の引き継ぎ・特徴の見落としの根本原因) を防ぐ。
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.gemini.generate import (  # noqa: E402
    REF_LABEL_DB,
    REF_LABEL_EXTRA,
    _build_reference_parts,
)

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class _Part:
    def __init__(self, kind, value):
        self.kind, self.value = kind, value

    @classmethod
    def from_text(cls, text):
        return cls("text", text)

    @classmethod
    def from_bytes(cls, data, mime_type):
        return cls("image", mime_type)


class _Types:
    Part = _Part


def _write(tmp_path: Path, name: str) -> str:
    p = tmp_path / name
    p.write_bytes(_PNG)
    return str(p)


def test_labels_interleave_and_default_to_db(tmp_path, monkeypatch):
    import src.utils.image_io as image_io

    monkeypatch.setattr(image_io, "load_reference_bytes", lambda p: (_PNG, "image/png"))
    rough = _write(tmp_path, "rough.png")
    origin = _write(tmp_path, "origin.png")

    parts = _build_reference_parts(
        _Types, [], [rough, origin], limit=5, labels={rough: REF_LABEL_EXTRA}
    )
    kinds = [p.kind for p in parts]
    assert kinds == ["text", "image", "text", "image"], "ラベルが画像の直前に挟まれていない"
    assert REF_LABEL_EXTRA in parts[0].value and parts[0].value.startswith("[参照1")
    assert REF_LABEL_DB in parts[2].value, "未登録パスが公式原典ラベルになっていない"


def test_limit_counts_images_not_labels(tmp_path, monkeypatch):
    import src.utils.image_io as image_io

    monkeypatch.setattr(image_io, "load_reference_bytes", lambda p: (_PNG, "image/png"))
    paths = [_write(tmp_path, f"{i}.png") for i in range(4)]
    parts = _build_reference_parts(_Types, [], paths, limit=2, labels={})
    assert sum(p.kind == "image" for p in parts) == 2


def test_no_labels_when_none(tmp_path, monkeypatch):
    import src.utils.image_io as image_io

    monkeypatch.setattr(image_io, "load_reference_bytes", lambda p: (_PNG, "image/png"))
    parts = _build_reference_parts(_Types, [], [_write(tmp_path, "a.png")], labels=None)
    assert [p.kind for p in parts] == ["image"]


def test_stage4_missing_reaches_correction_prompt(tmp_path, monkeypatch):
    from src.pipeline import correction_generator as cg

    captured: dict = {}

    def _fake_generate_image(**kw):
        captured.update(kw)
        return [tmp_path / "out.png"]

    import src.gemini.generate as gg

    monkeypatch.setattr(gg, "generate_image", _fake_generate_image)
    record = {"data": {"Num": 57}, "ai_hints": {"common": {"identity_tags": ["fox ears"]}}}
    rough = Path(_write(tmp_path, "rough.png"))
    cg._apply_correction_gemini(
        record, "corefolder", rough,
        analysis={"violations": [], "missing": ["尻尾: 原典では7本"], "composition_issues": []},
        prompts={"base_gemini": "BASE"}, stage_dir=tmp_path, work_key="#Works_NumberTales",
        index=1, use_t2i=False,
    )
    assert "尻尾: 原典では7本" in captured["prompt_override"]
    assert captured.get("skip_db_refs") is None, "i2i 修正で DB 原典が外されている"
