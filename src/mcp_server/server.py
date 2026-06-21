#!/usr/bin/env python3
"""ナンバーテールズ画像生成パイプラインの MCP サーバ (FastMCP)。

`src.pipeline.image_pipeline` の各入口を MCP ツールとして公開する:

- numbertales_generate_character   : 単体キャラ生成 (run_image_pipeline)
- numbertales_generate_joint       : 合同生成      (run_combined_pipeline)
- numbertales_generate_from_natural: 自然文ディスパッチ (parse_generation_request)
- numbertales_iterate              : i2i 改稿       (run_image_pipeline + iterate_from)
- numbertales_job_status           : ジョブ進捗ポーリング
- numbertales_list_runs            : 直近ジョブ一覧

長時間処理のため生成系ツールは「ジョブ登録 → job_id 即返し」方式。
進捗・完成画像リンクは numbertales_job_status で取得する。

起動:
    # ローカル (stdio)
    python -m src.mcp_server.server
    # リモート (Cloud Run など、Streamable HTTP)
    MCP_TRANSPORT=streamable-http PORT=8080 python -m src.mcp_server.server
"""

from __future__ import annotations

import json
import os
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from src.mcp_server import output_sink
from src.mcp_server.auth import SimpleOAuthProvider
from src.mcp_server.jobs import MANAGER

# ── サーバ設定 ──────────────────────────────────────────────────
SERVER_NAME = "numbertales_mcp"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
# HTTP transport (GCE/Cloud Run) で OAuth を有効化する場合は公開 URL を設定する
# 例: https://mcp.numbertales-radiann.net
ISSUER_URL = os.getenv("MCP_ISSUER_URL", "").rstrip("/")
DEFAULT_WORK_KEY = "#Works_NumberTales"

_oauth_provider = SimpleOAuthProvider() if ISSUER_URL else None
_auth_settings = AuthSettings(issuer_url=ISSUER_URL) if ISSUER_URL else None

mcp = FastMCP(
    SERVER_NAME,
    host=HOST,
    port=PORT,
    auth_server_provider=_oauth_provider,
    auth=_auth_settings,
)


# ── 列挙・共通モデル ────────────────────────────────────────────
class Form(str, Enum):
    """ナンバーテールズの形態。"""

    COREFOLDER = "corefolder"
    HUMANOID = "humanoid"


class CorrectionMode(str, Enum):
    """重度違反時の対処モード。"""

    T2I = "t2i"        # Stage 4 内で T2I フル再生成
    STAGE3 = "stage3"  # Stage 3 に差し戻してラフ再生成


class _Base(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )


# ── 入力モデル ──────────────────────────────────────────────────
class GenerateCharacterInput(_Base):
    """単体キャラ生成の入力。"""

    num: int = Field(..., description="キャラクター番号 (1-100、例: 57)", ge=1, le=100)
    form: Form = Field(default=Form.COREFOLDER, description="形態 (corefolder / humanoid)")
    scene: str = Field(default="", description="シーン・ポーズ説明。空ならランダム自動生成 (例: '図書館で本を読んでいるシーン')", max_length=600)
    style: str = Field(default="", description="作風ヒント (例: 'watercolor')", max_length=200)
    composition: str = Field(default="", description="構図ヒント (例: 'bust shot')", max_length=200)
    background: str = Field(default="", description="背景ヒント", max_length=200)
    skip_canva: bool = Field(default=False, description="True で Stage 5 の Canva フィニッシングをスキップ")
    correction_mode: CorrectionMode = Field(default=CorrectionMode.T2I, description="重度違反時の対処モード")
    work_key: str = Field(default=DEFAULT_WORK_KEY, description="作品キー", max_length=100)


class GenerateJointInput(_Base):
    """合同生成（複数キャラを 1 枚に）の入力。"""

    nums: list[int] = Field(..., description="キャラクター番号のリスト (例: [25, 57])", min_length=2, max_length=6)
    form: Form = Field(default=Form.COREFOLDER, description="形態 (corefolder / humanoid)")
    scene: str = Field(default="", description="共通シーン説明 (例: '自信に満ちた表情で並んでいるシーン')", max_length=600)
    style: str = Field(default="", description="作風ヒント", max_length=200)
    composition: str = Field(default="", description="構図ヒント", max_length=200)
    background: str = Field(default="", description="背景ヒント", max_length=200)
    skip_canva: bool = Field(default=False, description="True で Stage 5 をスキップ")
    correction_mode: CorrectionMode = Field(default=CorrectionMode.T2I, description="重度違反時の対処モード")
    work_key: str = Field(default=DEFAULT_WORK_KEY, description="作品キー", max_length=100)

    @field_validator("nums")
    @classmethod
    def _validate_nums(cls, v: list[int]) -> list[int]:
        for n in v:
            if not (1 <= n <= 100):
                raise ValueError(f"キャラクター番号は 1-100 の範囲です: {n}")
        return v


class GenerateFromNaturalInput(_Base):
    """自然文リクエストからの生成入力。"""

    text: str = Field(..., description="自然文（例: 'コアフォルダ姿の25(フィズ)がチョコレートを咥えている絵'）", min_length=2, max_length=4000)
    prefer_gemini_parse: bool = Field(default=False, description="True で自然文パースを Gemini 優先にする")
    skip_canva: bool = Field(default=False, description="True で Stage 5 をスキップ")
    correction_mode: CorrectionMode = Field(default=CorrectionMode.T2I, description="重度違反時の対処モード")


class IterateInput(_Base):
    """i2i 改稿の入力（前回 run を起点に Stage 3〜5 を改稿モードで再実行）。"""

    num: int = Field(..., description="キャラクター番号 (1-100)", ge=1, le=100)
    iterate_from: str = Field(..., description="前回生成画像のパスまたは run-dir (例: 'output/20260609/20260609_15/..._num057')", min_length=1, max_length=600)
    revisions: str = Field(..., description="修正指示（';' または改行区切り。例: '尻尾は元のまま; 表情だけ笑顔にして'）", min_length=1, max_length=1000)
    form: Form = Field(default=Form.COREFOLDER, description="形態 (corefolder / humanoid)")
    skip_canva: bool = Field(default=False, description="True で Stage 5 をスキップ")
    correction_mode: CorrectionMode = Field(default=CorrectionMode.T2I, description="重度違反時の対処モード")
    work_key: str = Field(default=DEFAULT_WORK_KEY, description="作品キー", max_length=100)


class JobStatusInput(_Base):
    """ジョブ進捗照会の入力。"""

    job_id: str = Field(..., description="生成ツールが返した job_id", min_length=1, max_length=64)


class ListRunsInput(_Base):
    """直近ジョブ一覧の入力。"""

    limit: int = Field(default=20, description="返す最大件数", ge=1, le=100)


# ── 結果整形ヘルパ ──────────────────────────────────────────────
def _extract_output_paths(result_dict: dict[str, Any]) -> list[str]:
    """PipelineResult 由来の辞書から「最良の」画像パス群を取り出す。

    Stage5(完成) > Stage4(修正済みラフ) > Stage3(Gemini ラフ) の優先順。
    """
    s5 = result_dict.get("stage5_paths", {}) or {}
    s4 = result_dict.get("stage4_paths", {}) or {}
    s3 = result_dict.get("stage3_paths", {}) or {}
    for bucket, key in ((s5, "all"), (s4, "all"), (s3, "gemini")):
        paths = bucket.get(key) or []
        if paths:
            return list(paths)
    # それでも無ければ全ステージのパスをかき集める
    collected: list[str] = []
    for bucket in (s5, s4, s3):
        for vals in bucket.values():
            collected.extend(vals or [])
    return collected


def _result_to_dict(result: Any) -> dict[str, Any]:
    """PipelineResult / MultiCharPipelineResult を素の辞書へ。"""
    from dataclasses import asdict, is_dataclass

    if is_dataclass(result):
        return asdict(result)
    if isinstance(result, dict):
        return result
    return {"value": str(result)}


def _run_and_publish(result: Any) -> dict[str, Any]:
    """パイプライン結果を要約し、出力画像をシンクへ公開した要約 dict を返す。"""
    rd = _result_to_dict(result)
    run_dir = rd.get("pipeline_dir", "")
    run_label = os.path.basename(run_dir.rstrip("/\\")) if run_dir else ""
    image_paths = _extract_output_paths(rd)
    outputs = output_sink.publish(image_paths, run_label=run_label)
    return {
        "status": rd.get("status", "unknown"),
        "pipeline_dir": run_dir,
        "scene_used": rd.get("scene_used", ""),
        "errors": rd.get("errors", []),
        "image_count": len(image_paths),
        "outputs": outputs,
        "sink": output_sink.current_sink(),
        "stage_summary": {
            "stage1": rd.get("stage1_prompts", {}),
            "stage2": rd.get("stage2_summary", {}),
        },
    }


# ── ツール: 単体生成 ────────────────────────────────────────────
@mcp.tool(
    name="numbertales_generate_character",
    annotations={
        "title": "ナンバーテールズ 単体キャラ生成",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def numbertales_generate_character(params: GenerateCharacterInput) -> str:
    """1 体のナンバーテールズを Stage 1〜5 のパイプラインで生成する（非同期ジョブ）。

    このツールはジョブを登録して即座に job_id を返す。生成は数分かかるため、
    完成画像のリンクは numbertales_job_status で取得すること。不変特徴
    （耳・尻尾本数・髪色・瞳色）はパイプライン側で検証・修正される。

    Args:
        params (GenerateCharacterInput):
            - num (int): キャラクター番号 1-100
            - form (Form): 'corefolder' | 'humanoid'
            - scene (str): シーン説明（空ならランダム生成）
            - style/composition/background (str): 各種ヒント
            - skip_canva (bool): Stage 5 スキップ
            - correction_mode (CorrectionMode): 't2i' | 'stage3'
            - work_key (str): 作品キー

    Returns:
        str: JSON 文字列。スキーマ::
            {
              "job_id": str,        # numbertales_job_status に渡す ID
              "status": "pending",
              "kind": "generate_character",
              "message": str        # 次アクション案内
            }
    """
    p = params

    def _job() -> dict[str, Any]:
        from src.pipeline.image_pipeline import run_image_pipeline

        result = run_image_pipeline(
            num=p.num,
            form=p.form.value,
            work_key=p.work_key,
            scene=p.scene,
            style=p.style,
            composition=p.composition,
            background=p.background,
            skip_canva=p.skip_canva,
            correction_mode=p.correction_mode.value,
        )
        return _run_and_publish(result)

    job = MANAGER.submit("generate_character", p.model_dump(mode="json"), _job)
    return _submit_response(job)


# ── ツール: 合同生成 ────────────────────────────────────────────
@mcp.tool(
    name="numbertales_generate_joint",
    annotations={
        "title": "ナンバーテールズ 合同生成（複数キャラ 1 枚）",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def numbertales_generate_joint(params: GenerateJointInput) -> str:
    """複数のナンバーテールズを 1 枚に合同生成する（非同期ジョブ）。

    Stage 3-4 をキャラ別に実行し、Stage 5 で全員を 1 枚に合成する。
    完成画像のリンクは numbertales_job_status で取得すること。

    Args:
        params (GenerateJointInput):
            - nums (list[int]): キャラクター番号のリスト（2-6 体）
            - form (Form), scene/style/composition/background (str)
            - skip_canva (bool), correction_mode (CorrectionMode), work_key (str)

    Returns:
        str: JSON 文字列 {"job_id", "status": "pending", "kind", "message"}
    """
    p = params

    def _job() -> dict[str, Any]:
        from src.pipeline.image_pipeline import run_combined_pipeline

        result = run_combined_pipeline(
            nums=list(p.nums),
            form=p.form.value,
            work_key=p.work_key,
            scene=p.scene,
            style=p.style,
            composition=p.composition,
            background=p.background,
            skip_canva=p.skip_canva,
            correction_mode=p.correction_mode.value,
        )
        return _run_and_publish(result)

    job = MANAGER.submit("generate_joint", p.model_dump(mode="json"), _job)
    return _submit_response(job)


# ── ツール: 自然文ディスパッチ ──────────────────────────────────
@mcp.tool(
    name="numbertales_generate_from_natural",
    annotations={
        "title": "ナンバーテールズ 自然文から生成",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def numbertales_generate_from_natural(params: GenerateFromNaturalInput) -> str:
    """自然文リクエストを解析し、適切なキャラ・形態・シーンで生成する（非同期ジョブ）。

    入力文から (num, form, scene, …) を抽出し、1 体なら単体生成、
    複数体なら合同生成へディスパッチする。CLI の `--natural` と同等。

    Args:
        params (GenerateFromNaturalInput):
            - text (str): 自然文（日本語/英語）
            - prefer_gemini_parse (bool): パースを Gemini 優先に
            - skip_canva (bool), correction_mode (CorrectionMode)

    Returns:
        str: JSON 文字列。解析成功時 {"job_id", "status": "pending", "parsed": [...], "kind", "message"}。
             抽出 0 件なら {"status": "failed", "error": "..."}。
    """
    p = params

    def _job() -> dict[str, Any]:
        from src.pipeline.image_pipeline import (
            run_combined_pipeline,
            run_image_pipeline,
        )
        from src.pipeline.natural_parser import parse_generation_request

        char_params = parse_generation_request(p.text, prefer_gemini=p.prefer_gemini_parse)
        if not char_params:
            return {
                "status": "failed",
                "error": "自然文からキャラクターパラメータを抽出できませんでした。",
                "outputs": [],
            }

        if len(char_params) == 1:
            cp = char_params[0]
            result = run_image_pipeline(
                num=cp["num"],
                form=cp.get("form", "corefolder"),
                work_key=cp.get("work_key", DEFAULT_WORK_KEY),
                scene=cp.get("scene", ""),
                style=cp.get("style", ""),
                composition=cp.get("composition", ""),
                background=cp.get("background", ""),
                skip_canva=p.skip_canva,
                correction_mode=p.correction_mode.value,
            )
        else:
            result = run_combined_pipeline(
                nums=[cp["num"] for cp in char_params],
                form=char_params[0].get("form", "corefolder"),
                work_key=char_params[0].get("work_key", DEFAULT_WORK_KEY),
                scene=char_params[0].get("scene", ""),
                style=char_params[0].get("style", ""),
                composition=char_params[0].get("composition", ""),
                background=char_params[0].get("background", ""),
                skip_canva=p.skip_canva,
                correction_mode=p.correction_mode.value,
            )
        summary = _run_and_publish(result)
        summary["parsed"] = char_params
        return summary

    job = MANAGER.submit("generate_from_natural", p.model_dump(mode="json"), _job)
    return _submit_response(job)


# ── ツール: i2i 改稿 ────────────────────────────────────────────
@mcp.tool(
    name="numbertales_iterate",
    annotations={
        "title": "ナンバーテールズ i2i 改稿",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def numbertales_iterate(params: IterateInput) -> str:
    """前回生成画像を起点に、指示に沿って改稿する（i2i・非同期ジョブ）。

    iterate_from で指定した run を起点に Stage 3 を i2i モードで実行し、
    Stage 4/5 は通常通り回す。CLI の `--iterate-from` / `--revisions` と同等。

    Args:
        params (IterateInput):
            - num (int): キャラクター番号
            - iterate_from (str): 起点となる画像パス or run-dir
            - revisions (str): 修正指示（';'/改行区切り）
            - form (Form), skip_canva (bool), correction_mode, work_key

    Returns:
        str: JSON 文字列 {"job_id", "status": "pending", "kind", "message"}
    """
    p = params

    def _job() -> dict[str, Any]:
        from src.pipeline.image_pipeline import run_image_pipeline

        result = run_image_pipeline(
            num=p.num,
            form=p.form.value,
            work_key=p.work_key,
            skip_canva=p.skip_canva,
            correction_mode=p.correction_mode.value,
            iterate_from=p.iterate_from,
            revisions=p.revisions,
        )
        return _run_and_publish(result)

    job = MANAGER.submit("iterate", p.model_dump(mode="json"), _job)
    return _submit_response(job)


# ── ツール: ジョブ進捗 ──────────────────────────────────────────
@mcp.tool(
    name="numbertales_job_status",
    annotations={
        "title": "ナンバーテールズ ジョブ進捗照会",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def numbertales_job_status(params: JobStatusInput) -> str:
    """生成ジョブの進捗・完成画像リンクを照会する（読み取り専用）。

    Args:
        params (JobStatusInput): job_id (str)

    Returns:
        str: JSON 文字列。スキーマ::
            {
              "job_id": str,
              "kind": str,
              "status": "pending"|"running"|"succeeded"|"failed",
              "created_at": str, "started_at": str, "finished_at": str,
              "result": {                # status == succeeded のとき
                 "status": str,
                 "pipeline_dir": str,
                 "scene_used": str,
                 "image_count": int,
                 "sink": "local"|"drive"|"gcs",
                 "outputs": [ {"name","local_path","url","sink","note"} ],
                 "errors": [str]
              } | null,
              "error": str               # status == failed のとき
            }
    """
    job = MANAGER.get(params.job_id)
    if job is None:
        return json.dumps(
            {"error": f"job_id '{params.job_id}' が見つかりません。numbertales_list_runs で確認してください。"},
            ensure_ascii=False,
        )
    return json.dumps(job.snapshot(), ensure_ascii=False, indent=2)


# ── ツール: ジョブ一覧 ──────────────────────────────────────────
@mcp.tool(
    name="numbertales_list_runs",
    annotations={
        "title": "ナンバーテールズ 直近ジョブ一覧",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def numbertales_list_runs(params: ListRunsInput) -> str:
    """直近の生成ジョブを新しい順に一覧する（読み取り専用）。

    Args:
        params (ListRunsInput): limit (int, 1-100)

    Returns:
        str: JSON 文字列 {"count": int, "jobs": [ {job_id, kind, status, created_at, finished_at} ]}
    """
    jobs = MANAGER.list_recent(params.limit)
    rows = [
        {
            "job_id": j.job_id,
            "kind": j.kind,
            "status": j.status,
            "created_at": j.created_at,
            "finished_at": j.finished_at,
        }
        for j in jobs
    ]
    return json.dumps({"count": len(rows), "jobs": rows}, ensure_ascii=False, indent=2)


# ── 共通: 登録レスポンス ────────────────────────────────────────
def _submit_response(job: Any) -> str:
    return json.dumps(
        {
            "job_id": job.job_id,
            "status": job.status,
            "kind": job.kind,
            "message": f"生成ジョブを登録しました。numbertales_job_status に job_id='{job.job_id}' を渡して進捗を確認してください。",
        },
        ensure_ascii=False,
    )


# ── エントリポイント ────────────────────────────────────────────
def _normalize_transport(raw: Optional[str]) -> str:
    """環境変数の表記ゆれを SDK が受け付ける形に正規化する。"""
    t = (raw or "stdio").strip().lower().replace("_", "-")
    if t in ("http", "streamable", "streamable-http"):
        return "streamable-http"
    if t == "sse":
        return "sse"
    return "stdio"


def main() -> None:
    transport = _normalize_transport(os.getenv("MCP_TRANSPORT"))
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
