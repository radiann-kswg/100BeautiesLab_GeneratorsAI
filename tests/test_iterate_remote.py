"""改稿の起点をリモートから読むときの制限（自分の置き場だけ・時間切れ・大きさの上限）の回帰テスト。"""
from __future__ import annotations

import io

import pytest

from src.utils import iterate


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_remote_source_must_be_under_this_servers_bucket_and_prefix(monkeypatch):
    monkeypatch.setenv("GCS_BUCKET", "own-bucket")
    monkeypatch.delenv("GCS_PREFIX", raising=False)
    opened = []

    def urlopen(url, timeout=None):
        opened.append((url, timeout))
        return _Response(b"\xff\xd8\xff" + b"0" * 16)

    monkeypatch.setattr(iterate.urllib.request, "urlopen", urlopen)
    ok = "https://storage.googleapis.com/own-bucket/numbertales/run__stage5_num057.jpg?X-Goog-Signature=abc"
    path, run_dir = iterate.resolve_iterate_source(ok)
    assert path.suffix == ".jpg" and path.read_bytes().startswith(b"\xff\xd8\xff") and run_dir is None
    assert opened == [(ok, 30)]                                    # 時間切れを付けて読む
    path.unlink()
    assert iterate._own_object("https://own-bucket.storage.googleapis.com/numbertales/a%20b.png") == (
        "own-bucket", "numbertales/a b.png")

    for bad in ("https://storage.googleapis.com/other-bucket/numbertales/x.jpg",
                "https://storage.googleapis.com/own-bucket/shapechange/x.jpg",
                "https://storage.googleapis.com/own-bucket/numbertales/../shapechange/x.jpg",
                "gs://other-bucket/numbertales/x.jpg"):
        with pytest.raises(RuntimeError, match="の下の画像だけ"):
            iterate.resolve_iterate_source(bad)
    assert len(opened) == 1                                        # 置き場の外の URL は開かない

    monkeypatch.delenv("GCS_BUCKET")
    with pytest.raises(RuntimeError, match="GCS_BUCKET が未設定"):
        iterate.resolve_iterate_source(ok)


def test_remote_source_larger_than_the_limit_is_refused(monkeypatch):
    monkeypatch.setenv("GCS_BUCKET", "own-bucket")
    monkeypatch.setattr(iterate, "REMOTE_MAX_BYTES", 8)
    monkeypatch.setattr(iterate.urllib.request, "urlopen", lambda url, timeout=None: _Response(b"0" * 64))
    with pytest.raises(RuntimeError, match="大きすぎます"):
        iterate.resolve_iterate_source("https://storage.googleapis.com/own-bucket/numbertales/huge.png")
