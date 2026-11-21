"""インスタンスが入れ替わっても残す状態（ジョブの記録と、その置き場）の回帰テスト。生成 API は使わない。

2026-11-21、Cloud Run がジョブの直後にインスタンスを入れ替え、サインインの状態とジョブの記録が消えた。
サインインの状態のテストは tests/test_mcp_auth.py。
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import threading
import time
import types
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def test_job_records_survive_a_replaced_instance_when_a_store_is_given():
    # 2026-11-21、Cloud Run がインスタンスを入れ替え、動かしたジョブの状態を照会できなくなった
    from src.mcp_server.jobs import JobManager
    from src.mcp_server.state_store import MemoryStore

    store, gate = MemoryStore(), threading.Event()
    first = JobManager()
    first.use_store(store)
    done = first.submit("generate_character", {"argv": ["--badge=57"]}, lambda: {"run_id": "run-1", "status": "ok"})
    held = first.submit("generate_character", {"argv": ["--badge=58"]}, lambda: gate.wait(5) and {"run_id": "run-2"})
    first.update_partial_result(held.job_id, "stage3", {"count": 3}, "outputs/run-2")
    for _ in range(200):
        if first.get(done.job_id).status == "succeeded":
            break
        time.sleep(0.02)

    replaced = JobManager()                         # 入れ替わったあとのインスタンス
    replaced.use_store(store)
    finished = replaced.get(done.job_id).snapshot()
    assert finished["status"] == "succeeded" and finished["result"] == {"run_id": "run-1", "status": "ok"}
    assert finished["params"] == {"argv": ["--badge=57"]} and "note" not in finished
    # 終わる前に入れ替わったジョブは、中断として返す（処理は引き継げない）。途中までの結果は見せる
    lost = replaced.get(held.job_id).snapshot()
    assert lost["status"] == "interrupted" and "入れ替わりました" in lost["note"]
    assert lost["partial_result"]["stage_summary"] == {"stage3": {"count": 3}}
    # 元のインスタンスが終わらせたら、次の照会では結果が見える（中断の判定を覚え込まない）
    gate.set()
    for _ in range(200):
        if first.get(held.job_id).status == "succeeded":
            break
        time.sleep(0.02)
    assert replaced.get(held.job_id).snapshot()["status"] == "succeeded"

    assert replaced.get("unknown-job") is None and replaced.get("../etc/passwd") is None
    alone = JobManager()                            # 置き場を渡さないサーバーは、これまでどおりメモリーだけ
    assert alone.get(done.job_id) is None


def test_state_store_keeps_json_under_its_own_prefix_and_refuses_odd_names():
    from src.mcp_server import state_store

    blobs: dict[str, str] = {}

    class _Blob:
        def __init__(self, key):
            self.key = key

        def upload_from_string(self, text, content_type=""):
            blobs[self.key] = text

        def exists(self):
            return self.key in blobs

        def download_as_bytes(self):
            return blobs[self.key].encode("utf-8")

        def delete(self):
            del blobs[self.key]

    bucket = types.SimpleNamespace(blob=_Blob)
    with patch.object(state_store.output_sink, "_bucket", lambda: bucket), \
            patch.dict(os.environ, {"GCS_PREFIX": "numbertales"}), contextlib.redirect_stdout(io.StringIO()):
        store = state_store.GcsStore()
        assert store.put("job", "abc123", {"status": "ok"}) and list(blobs) == ["numbertales/state/job/abc123.json"]
        assert store.get("job", "abc123") == {"status": "ok"} and store.get("job", "missing") is None
        # 名前に使えるのは英数字と - _ だけ（ほかの場所のオブジェクトを指せない）
        assert store.put("job", "../x", {}) is False and store.get("job", "a/b") is None and len(blobs) == 1
        store.delete("job", "abc123")
        store.delete("job", "abc123")               # すでに無くても落ちない
        assert not blobs
    with patch.dict(os.environ, {"GCS_BUCKET": ""}):
        assert state_store.default_store() is None  # バケットが無い環境では、何も保存しない
