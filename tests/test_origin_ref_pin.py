"""
tests/test_origin_ref_pin.py — 原点画像ピンの回帰テスト
Copyright © RadianN_kswg — CC BY-NC 4.0

NT_ORIGIN_REFS_DIR で指名した原点画像が、形態別に・最優先で参照先頭に入ることを守る。
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils.dataset import _collect_pinned_refs  # noqa: E402


def test_origin_image_is_pinned_per_form(tmp_path, monkeypatch):
    (tmp_path / "origin_corefolder57.png").write_bytes(b"x")
    (tmp_path / "origin_humanoid57.webp").write_bytes(b"x")
    (tmp_path / "origin_corefolder5.png").write_bytes(b"x")  # 前方一致で誤爆しないこと
    monkeypatch.setenv("NT_ORIGIN_REFS_DIR", str(tmp_path))
    monkeypatch.delenv("NT_VRM_STYLE_REFS_DIR", raising=False)

    assert _collect_pinned_refs(57, "corefolder") == [str(tmp_path / "origin_corefolder57.png")]
    assert _collect_pinned_refs(57, "humanoid") == [str(tmp_path / "origin_humanoid57.webp")]
    assert _collect_pinned_refs(75, "corefolder") == []


def test_disabled_without_env(tmp_path, monkeypatch):
    monkeypatch.delenv("NT_ORIGIN_REFS_DIR", raising=False)
    monkeypatch.delenv("NT_VRM_STYLE_REFS_DIR", raising=False)
    assert _collect_pinned_refs(57, "corefolder") == []


def test_sheet_thumbnail_order_comes_from_db_type():
    from src.utils.dataset import _creations_db_repo_root, _sheet_thumbnail_order

    order = _sheet_thumbnail_order("#Works_NumberTales", str(_creations_db_repo_root()))
    # キャラシートの代表サムネは concept (設定原画)。arts より必ず前に来る。
    assert order[0] == "concept"
    assert order.index("concept") < order.index("arts")


def test_origin_prefers_sheet_thumbnail_then_transparency(tmp_path):
    from PIL import Image

    from src.utils.dataset import _has_alpha, _pick_origin_ref

    def _png(rel: str, alpha: bool) -> str:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA" if alpha else "RGB", (4, 4)).save(path)
        return str(path)

    core_opaque = _png("corefolder/a.png", alpha=False)
    core_alpha = _png("corefolder/b.png", alpha=True)
    concept = _png("concept/c.png", alpha=False)
    order_args = ("#Works_NumberTales", str(_PROJECT_ROOT / "_creations-ai" / "creations-db"))

    # サムネ順 (concept) が透過より強い
    assert _pick_origin_ref([core_alpha, concept], *order_args) == [concept]
    # 同カテゴリ内では透過が勝つ
    assert _pick_origin_ref([core_opaque, core_alpha], *order_args) == [core_alpha]
    assert _pick_origin_ref([], *order_args) == []
    assert _has_alpha(core_alpha) and not _has_alpha(core_opaque)
