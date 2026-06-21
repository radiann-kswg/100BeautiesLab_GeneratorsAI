"""長時間パイプライン実行のための非同期ジョブ管理。

パイプライン（Stage 1〜5）は数分かかる同期処理のため、MCP ツールは
「ジョブを登録して即 job_id を返す」→「job_status でポーリング」方式を採る。

ジョブはプロセス内メモリに保持する。Cloud Run では
**min-instances=1 / max-instances=1 / CPU 常時割当** を前提にすること
（複数インスタンスへスケールすると別インスタンスのジョブが見えない）。
将来的に複数インスタンス化する場合は Firestore 等の共有ストアへ差し替える。
"""

from __future__ import annotations

import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

# パイプラインは外部 API を直列に叩くため、過剰並列を避け既定 2 本に絞る。
_MAX_WORKERS = 2

_STATUS_PENDING = "pending"
_STATUS_RUNNING = "running"
_STATUS_SUCCEEDED = "succeeded"
_STATUS_FAILED = "failed"


@dataclass
class Job:
    """1 回のパイプライン実行に対応するジョブ。"""

    job_id: str
    kind: str                         # generate_character / generate_joint / ...
    params: dict[str, Any]
    status: str = _STATUS_PENDING
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    result: dict[str, Any] | None = None   # 完了時の要約 + 出力リンク
    error: str = ""

    def snapshot(self) -> dict[str, Any]:
        """外部公開用の辞書スナップショットを返す。"""
        return {
            "job_id": self.job_id,
            "kind": self.kind,
            "status": self.status,
            "params": self.params,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": self.result,
            "error": self.error,
        }


class JobManager:
    """スレッドプールでパイプラインを走らせる軽量ジョブマネージャ。"""

    def __init__(self, max_workers: int = _MAX_WORKERS) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def submit(
        self, kind: str, params: dict[str, Any], fn: Callable[[], dict[str, Any]]
    ) -> Job:
        """ジョブを登録して即座に Job を返す（バックグラウンドで fn を実行）。

        Parameters
        ----------
        kind:   ジョブ種別ラベル
        params: 公開用の入力パラメータ（job_status で見える）
        fn:     実処理。戻り値の dict がそのまま job.result になる。
        """
        job_id = uuid.uuid4().hex[:12]
        job = Job(
            job_id=job_id,
            kind=kind,
            params=params,
            created_at=_now(),
        )
        with self._lock:
            self._jobs[job_id] = job
        self._executor.submit(self._run, job, fn)
        return job

    def _run(self, job: Job, fn: Callable[[], dict[str, Any]]) -> None:
        with self._lock:
            job.status = _STATUS_RUNNING
            job.started_at = _now()
        try:
            result = fn()
            with self._lock:
                job.result = result
                job.status = _STATUS_SUCCEEDED
                job.finished_at = _now()
        except Exception as e:  # noqa: BLE001 - 失敗内容をジョブに保存して継続
            with self._lock:
                job.error = f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=4)}"
                job.status = _STATUS_FAILED
                job.finished_at = _now()

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_recent(self, limit: int = 20) -> list[Job]:
        with self._lock:
            jobs = sorted(
                self._jobs.values(), key=lambda j: j.created_at, reverse=True
            )
        return jobs[:limit]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# モジュールレベルの共有インスタンス（サーバ全体で 1 つ）
MANAGER = JobManager()
