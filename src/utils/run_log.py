"""
utils/run_log.py — 生成実行ごとのプロンプト・メタ情報を保存するユーティリティ
Copyright © RadianN_kswg — CC BY-NC 4.0

各実行ディレクトリ ``output/{ts}_{provider}_{form}_numNNN/`` 配下に
以下を保存する。これによりプロンプト・参照画像・成功失敗の差分を
あとから振り返れるようになる。

- ``prompt.txt``     : モデルに渡したプロンプト本文（自然文）
- ``run_meta.json``  : 実行メタデータ（provider/model/参照画像/生成結果/エラー要旨など）
- ``notes.md``       : 手書きレビュー用テンプレ（成功度・改善案メモ）

ログは「上書きしない」「実行ごとに専用ディレクトリに溜める」方針。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


_NOTES_TEMPLATE = """# 生成レビューメモ

- run_dir: {run_dir}
- provider: {provider}
- model: {model}
- character: #{num} ({form})
- work_key: {work_key}

## 評価
- 成功度: 未評価 (good / mid / bad)
- 良かった点:
- 気になった点:
- プロンプト改善案:
- 次に試したいこと:
"""


def _serialize(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def write_prompt_file(run_dir: Path, prompt_text: str, *, filename: str = "prompt.txt") -> Path:
    """プロンプト本文を ``run_dir`` 配下に保存する。"""
    path = Path(run_dir) / filename
    path.write_text(prompt_text or "", encoding="utf-8")
    return path


def write_run_meta(
    run_dir: Path,
    meta: dict[str, Any],
    *,
    filename: str = "run_meta.json",
) -> Path:
    """実行メタデータを ``run_meta.json`` として保存する。

    既に同名ファイルがある場合は更新（マージ）し、``updated_at`` を打刻する。
    """
    path = Path(run_dir) / filename
    existing: dict[str, Any] = {}
    if path.exists() and path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(existing, dict):
                existing = {}
        except Exception:
            existing = {}

    merged: dict[str, Any] = {**existing, **_serialize(meta)}
    merged.setdefault("created_at", existing.get("created_at") or datetime.now().isoformat(timespec="seconds"))
    merged["updated_at"] = datetime.now().isoformat(timespec="seconds")

    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_notes_template(
    run_dir: Path,
    *,
    provider: str,
    num: int | str,
    form: str,
    work_key: str,
    model: str,
    filename: str = "notes.md",
) -> Path:
    """手書きレビュー用の ``notes.md`` を初期化する。既存なら触らない。"""
    path = Path(run_dir) / filename
    if path.exists():
        return path
    body = _NOTES_TEMPLATE.format(
        run_dir=str(run_dir),
        provider=provider,
        model=model,
        num=num,
        form=form,
        work_key=work_key,
    )
    path.write_text(body, encoding="utf-8")
    return path


def initialize_run_logs(
    run_dir: Path,
    *,
    provider: str,
    num: int | str,
    form: str,
    work_key: str,
    model: str,
    prompt_text: str,
    meta: dict[str, Any] | None = None,
    prompt_filename: str = "prompt.txt",
) -> dict[str, Path]:
    """実行開始時に prompt / meta / notes を一括で初期化する。"""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}
    paths["prompt"] = write_prompt_file(run_dir, prompt_text, filename=prompt_filename)

    base_meta: dict[str, Any] = {
        "provider": provider,
        "model": model,
        "num": num,
        "form": form,
        "work_key": work_key,
        "run_dir": str(run_dir),
        "prompt_file": str(paths["prompt"].name),
        "status": "running",
        "results": [],
        "errors": [],
    }
    if meta:
        base_meta.update(meta)
    paths["meta"] = write_run_meta(run_dir, base_meta)
    paths["notes"] = write_notes_template(
        run_dir,
        provider=provider,
        num=num,
        form=form,
        work_key=work_key,
        model=model,
    )
    return paths


def finalize_run_logs(
    run_dir: Path,
    *,
    status: str,
    results: list[Any] | None = None,
    errors: list[Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """実行終了時に status / results / errors を ``run_meta.json`` へ書き戻す。"""
    payload: dict[str, Any] = {"status": status}
    if results is not None:
        payload["results"] = results
    if errors is not None:
        payload["errors"] = errors
    if extra:
        payload.update(extra)
    return write_run_meta(run_dir, payload)


__all__ = [
    "write_prompt_file",
    "write_run_meta",
    "write_notes_template",
    "initialize_run_logs",
    "finalize_run_logs",
]
