"""入力画像の受け取り口（署名付き PUT URL）と、自分の接頭辞の下の読み取りの回帰テスト。GCS は呼ばない。"""
from __future__ import annotations

import pytest

from src.mcp_server import output_sink


class _Blob:
    def __init__(self, bucket, name):
        self.bucket, self.name = bucket, name

    @property
    def size(self):
        return len(self.bucket.store[self.name])

    def download_as_bytes(self):
        return self.bucket.store[self.name]

    def generate_signed_url(self, **options):
        self.bucket.signed.append(options)
        return f"https://signed.example/{self.name}"


class _Bucket:
    def __init__(self, store=None):
        self.store, self.signed = dict(store or {}), []

    def blob(self, key):
        return _Blob(self, key)

    def get_blob(self, key):
        return _Blob(self, key) if key in self.store else None


def test_upload_slot_is_a_short_lived_put_url_under_this_servers_prefix(monkeypatch):
    bucket = _Bucket()
    monkeypatch.setattr(output_sink, "_bucket", lambda: bucket)
    monkeypatch.delenv("GCS_PREFIX", raising=False)
    slot = output_sink.create_upload_slot("image/png")
    assert slot["note"] == "" and slot["object_key"].startswith("numbertales/uploads/") and slot["object_key"].endswith(".png")
    assert slot["headers"] == {"Content-Type": "image/png", "x-goog-content-length-range": "0,10485760"}
    (signed,) = bucket.signed
    assert signed["method"] == "PUT" and signed["content_type"] == "image/png"
    assert signed["expiration"].total_seconds() == 15 * 60
    assert signed["headers"] == {"x-goog-content-length-range": "0,10485760"}
    assert output_sink.create_upload_slot("image/png")["object_key"] != slot["object_key"]
    assert "content_type" in output_sink.create_upload_slot("image/gif")["note"]

    monkeypatch.undo()
    monkeypatch.setenv("GCS_BUCKET", "")
    assert "GCS_BUCKET" in output_sink.create_upload_slot("image/png")["note"]


def test_objects_are_read_only_from_this_servers_prefix_and_within_the_size_limit(monkeypatch):
    bucket = _Bucket({"numbertales/uploads/20261120/a.png": b"png-bytes", "shapechange/uploads/20261120/b.png": b"other",
                      "numbertales/uploads/20261120/huge.png": b"x" * 64})
    monkeypatch.setattr(output_sink, "_bucket", lambda: bucket)
    monkeypatch.delenv("GCS_PREFIX", raising=False)
    assert output_sink.read_object("numbertales/uploads/20261120/a.png") == b"png-bytes"
    for key, expected in (("shapechange/uploads/20261120/b.png", "の下だけ"),
                          ("numbertales/../shapechange/uploads/20261120/b.png", "の下だけ"),
                          ("https://example.com/a.png", "の下だけ"),
                          ("numbertales/uploads/20261120/none.png", "見つかりません")):
        with pytest.raises(ValueError, match=expected):
            output_sink.read_object(key)
    with pytest.raises(ValueError, match="大きすぎます"):
        output_sink.read_object("numbertales/uploads/20261120/huge.png", max_bytes=16)
