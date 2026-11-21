"""長時間パイプライン実行のための非同期ジョブ管理。

パイプライン（Stage 1〜5）は数分かかる同期処理のため、MCP ツールは
「ジョブを登録して即 job_id を返す」→「job_status でポーリング」方式を採る。

ジョブはプロセス内メモリに保持する。Cloud Run では **max-instances=1 / CPU 常時割当** を
前提にすること（複数インスタンスへスケールすると別インスタンスのジョブが見えない）。

Cloud Run は、ジョブが裏で動いていてもインスタンスを入れ替えることがある（2026-11-21）。``use_store`` で
置き場（``state_store``）を渡すと、ジョブの記録を外にも書き、入れ替わったあとのインスタンスからも照会できる。
終わったジョブは結果ごと読める。終わる前にインスタンスが入れ替わったジョブは、``interrupted``（中断）として返す
（動かしていた処理そのものは引き継げない）。
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
_STATUS_INTERRUPTED = "interrupted"    # 別のインスタンスで動いていて、終わった記録が無い
_FINISHED = (_STATUS_SUCCEEDED, _STATUS_FAILED, "cancelled")
_STORE_KIND = "job"
_INTERRUPTED_NOTE = (
    "このジョブを動かしていたサーバーのインスタンスは、入れ替わりました。処理は引き継がれないので、"
    "少し待ってもう一度照会しても状態が変わらなければ、中断されています。途中までの画像は partial_result、"
    "完成画像が残っているかは実行の一覧（list_runs）で確かめ、必要なら同じ指定で登録し直してください。"
)


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
    partial_result: dict[str, Any] | None = None  # 実行中の中間ステージ結果（Stage3/4 完了時に更新）
    confirmation: dict[str, Any] | None = None
    note: str = ""                    # 状態の補足（中断として返すときの説明）

    def snapshot(self) -> dict[str, Any]:
        """外部公開用の辞書スナップショットを返す。"""
        return {
            **({"note": self.note} if self.note else {}),
            "job_id": self.job_id,
            "kind": self.kind,
            "status": self.status,
            "params": self.params,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": self.result,
            "error": self.error,
            "partial_result": self.partial_result,
            "confirmation": self.confirmation,
        }


class JobManager:
    """スレッドプールでパイプラインを走らせる軽量ジョブマネージャ。"""

    def __init__(self, max_workers: int = _MAX_WORKERS) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._answers: dict[str, tuple[threading.Event, bool | None]] = {}
        self._store: Any = None
        self._instance = uuid.uuid4().hex[:8]     # どのインスタンスが書いた記録かを見分ける

    def use_store(self, store: Any) -> None:
        """ジョブの記録を外にも置く（``state_store`` の置き場。None なら置かない）。"""
        self._store = store

    def _persist(self, job: Job) -> None:
        """ジョブのいまの状態を、置き場へ書く。失敗しても処理は続ける。ロックの外で呼ぶ。"""
        if self._store is None:
            return
        with self._lock:
            data = {**job.snapshot(), "instance": self._instance, "updated_at": _now()}
        try:
            self._store.put(_STORE_KIND, job.job_id, data)
        except Exception as err:  # noqa: BLE001
            print(f"[WARN] ジョブの記録を保存できませんでした（{job.job_id}）: {type(err).__name__}")

    def _restore(self, job_id: str) -> Job | None:
        """メモリーに無いジョブを、置き場から読む。終わっていない記録は、中断として返す。"""
        if self._store is None:
            return None
        try:
            data = self._store.get(_STORE_KIND, job_id)
        except Exception:  # noqa: BLE001
            return None
        if not isinstance(data, dict) or data.get("job_id") != job_id:
            return None
        job = Job(job_id=job_id, kind=str(data.get("kind") or ""),
                  params=data.get("params") if isinstance(data.get("params"), dict) else {},
                  status=str(data.get("status") or ""), created_at=str(data.get("created_at") or ""),
                  started_at=str(data.get("started_at") or ""), finished_at=str(data.get("finished_at") or ""),
                  result=data.get("result") if isinstance(data.get("result"), dict) else None,
                  error=str(data.get("error") or ""),
                  partial_result=data.get("partial_result") if isinstance(data.get("partial_result"), dict) else None)
        if job.status in _FINISHED:
            with self._lock:
                self._jobs.setdefault(job_id, job)     # 終わった記録は変わらないので、覚えておく
        else:       # 別のインスタンスがまだ終わりかけている場合もあるので、覚えずに、次の照会でも読み直す
            job.status, job.note = _STATUS_INTERRUPTED, _INTERRUPTED_NOTE
        return job

    def confirm_reference(self, job_id: str, warning: dict, timeout: float = 1800) -> bool | None:
        """警告を公開して回答を待つ。無回答・期限切れは続行許可にならない。"""
        event = threading.Event()
        request_id = uuid.uuid4().hex
        with self._lock:
            job = self._jobs[job_id]
            job.confirmation = {**warning, "request_id": request_id,
                                "timeout_seconds": timeout,
                                "instruction": "理由を利用者に表示し、続行/中止を質問してください。回答を推測しないでください。"}
            job.status = "awaiting_confirmation"
            self._answers[request_id] = (event, None)
        self._persist(job)
        # ponytail: 確認待ちも既存の worker 1 枠を占有する。多数の同時利用が必要なら永続 continuation へ移す。
        event.wait(timeout)
        with self._lock:
            _, answer = self._answers.pop(request_id)
            job.confirmation = None
            job.status = _STATUS_RUNNING
        self._persist(job)
        return answer

    def answer_reference(self, job_id: str, request_id: str, proceed: bool) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if (job is None or job.status != "awaiting_confirmation" or not job.confirmation
                    or job.confirmation.get("request_id") != request_id):
                raise ValueError("該当する確認待ちがありません。最新の job_status を取得してください。")
            event, answer = self._answers[request_id]
            if answer is not None:
                raise ValueError("この確認には回答済みです。")
            if type(proceed) is not bool:
                raise ValueError("回答は true または false で指定してください。")
            self._answers[request_id] = (event, proceed)
            event.set()

    def submit(
        self,
        kind: str,
        params: dict[str, Any],
        fn: Callable[[], dict[str, Any]],
        job_id: str | None = None,
    ) -> Job:
        """ジョブを登録して即座に Job を返す（バックグラウンドで fn を実行）。

        Parameters
        ----------
        kind:   ジョブ種別ラベル
        params: 公開用の入力パラメータ（job_status で見える）
        fn:     実処理。戻り値の dict がそのまま job.result になる。
        job_id: 事前に確定済みの job_id（省略時は自動生成）。
                stage_callback クロージャへ job_id を渡す際に使う。
        """
        if job_id is None:
            job_id = uuid.uuid4().hex[:12]
        job = Job(
            job_id=job_id,
            kind=kind,
            params=params,
            created_at=_now(),
        )
        with self._lock:
            self._jobs[job_id] = job
        self._persist(job)
        self._executor.submit(self._run, job, fn)
        return job

    def update_partial_result(
        self, job_id: str, stage: str, stage_data: dict[str, Any], pipeline_dir: str = ""
    ) -> None:
        """実行中ジョブの中間ステージ結果を更新する（Stage3/4 完了時に呼ぶ）。

        get_run_logs が running 状態でも部分的な中間画像 URL を返せるようにするため、
        ステージごとに partial_result.stage_summary を逐次更新する。
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            partial: dict[str, Any] = dict(job.partial_result or {})
            if pipeline_dir:
                partial.setdefault("pipeline_dir", pipeline_dir)
            partial.setdefault("scene_used", "")
            ss: dict[str, Any] = dict(partial.get("stage_summary") or {})
            ss[stage] = stage_data
            partial["stage_summary"] = ss
            job.partial_result = partial
        self._persist(job)

    def _run(self, job: Job, fn: Callable[[], dict[str, Any]]) -> None:
        with self._lock:
            job.status = _STATUS_RUNNING
            job.started_at = _now()
        self._persist(job)
        try:
            result = fn()
            with self._lock:
                job.result = result
                job.status = _STATUS_SUCCEEDED
                job.finished_at = _now()
        except Exception as e:  # noqa: BLE001 - 失敗内容をジョブに保存して継続
            from src.pipeline.design_reference import ReferenceCancelled
            with self._lock:
                job.error = f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=4)}"
                job.status = "cancelled" if isinstance(e, ReferenceCancelled) else _STATUS_FAILED
                job.finished_at = _now()
        self._persist(job)

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
        return job if job is not None else self._restore(job_id)

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
