"""
roleplay/resolve.py — 上流生成済みロールプレイプロンプトの安全な解決・読み込み
Copyright © RadianN_kswg — CC BY-NC 4.0

上流 creations-db の ``tools/build-roleplay-prompts.mjs`` が ConversationPattern 等の
**充填済みフィールド**から機械生成したキャラ単位ロールプレイプロンプト Markdown を、
manifest レコードの ``roleplay_prompt.path``（creations-db サブモジュールルート基点）から
**ゲート付きで消費する**。src で組み立て直さない（上流生成器の二重実装を避ける。
policy を再実装しないのと同じ原則）。

漏洩ガード（最重要）: ``manifest.jsonl`` は ``allowed=false`` レコードの path も載せる
（例: ``#DB_SemiPrimary`` Num 100 は生成物があるが権利軸で不許可）。本文を読む前に
必ず権利軸ゲート（``generation_permitted(usage="roleplay")`` は権利軸・充填軸とも refuse）
を通す。上流 CLAUDE.md も「フォルダ一括読みは漏洩事故のため厳禁」と明記。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.utils.dataset import apply_generation_gate

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CREATIONS_DB_BASE = "_creations-ai/creations-db"
_ROLEPLAY_DIR_MARKER = "RoleplayPrompts"
_FILENAME_PREFIX = "roleplay-prompt-"


def _creations_db_root(creations_db_base: str = DEFAULT_CREATIONS_DB_BASE) -> Path:
    return (_PROJECT_ROOT / creations_db_base).resolve()


def resolve_roleplay_prompt_path(
    record: dict[str, Any] | None,
    *,
    creations_db_base: str = DEFAULT_CREATIONS_DB_BASE,
) -> Path | None:
    """``record.roleplay_prompt.path`` を creations-db ルート基点で解決する。

    パストラバーサル防止のため、解決結果が creations-db ルート配下かつ
    パスに ``RoleplayPrompts/`` を含むことを検証する。範囲外・空なら None。
    """
    rp = (record or {}).get("roleplay_prompt") or {}
    rel = rp.get("path")
    if not rel or not isinstance(rel, str):
        return None
    base = _creations_db_root(creations_db_base)
    candidate = (base / rel).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None  # base の外へ出るパス（../ 等）は拒否
    if _ROLEPLAY_DIR_MARKER not in candidate.parts:
        return None  # RoleplayPrompts 配下以外は拒否
    return candidate


def _filename_matches_num(path: Path, num: int | str) -> bool:
    """ファイル名 ``roleplay-prompt-<charId>.md`` の charId が num と一致するか。"""
    stem = path.stem  # 例: "roleplay-prompt-57"
    if not stem.startswith(_FILENAME_PREFIX):
        return False
    return stem[len(_FILENAME_PREFIX):] == str(num)


def _submodule_commit(creations_db_base: str = DEFAULT_CREATIONS_DB_BASE) -> str | None:
    """``build-info.json`` の ``submodule_commit``（creations-db コミット）を返す。失敗時 None。"""
    info = _PROJECT_ROOT / "_creations-ai" / "ai-dataset" / "build-info.json"
    try:
        data = json.loads(info.read_text(encoding="utf-8"))
        commit = data.get("submodule_commit")
        return commit if isinstance(commit, str) else None
    except Exception:
        return None


def load_roleplay_prompt(
    record: dict[str, Any] | None,
    *,
    num: int | str | None = None,
    creations_db_base: str = DEFAULT_CREATIONS_DB_BASE,
) -> dict[str, Any]:
    """ロールプレイプロンプト本文をゲート付きで読み込む。

    Returns
    -------
    dict: ``{status, reason, path, text, ai_training_gate, submodule_commit}``
      status:
        - ``"ok"``          … 読み込み成功（``text`` に本文）
        - ``"refused"``     … 権利軸／充填軸オプトアウト（本文は読まない）
        - ``"unavailable"`` … ``has_roleplay_prompt=false`` / path 無し（未生成）
        - ``"error"``       … パス範囲外・ファイル欠落・charId 不一致
      ``text`` は ``status=="ok"`` のときのみ設定。
    """
    result: dict[str, Any] = {
        "status": "",
        "reason": "",
        "path": None,
        "text": None,
        "ai_training_gate": None,
        "submodule_commit": _submodule_commit(creations_db_base),
    }

    # 1. 権利軸ゲート（roleplay は最厳格: 権利軸・充填軸とも refuse）。本文を読む前に必ず通す。
    proceed, gate = apply_generation_gate(record, usage="roleplay", num=num, printer=None)
    result["ai_training_gate"] = gate
    if not proceed:
        result["status"] = "refused"
        result["reason"] = f"ai_training opt-out: {gate['reason']}"
        return result

    # 2. 生成物の有無
    if not record or not record.get("has_roleplay_prompt"):
        result["status"] = "unavailable"
        result["reason"] = "has_roleplay_prompt=false（このキャラのロールプレイプロンプトは未生成）"
        return result

    # 3. パス解決 + トラバーサル防止
    path = resolve_roleplay_prompt_path(record, creations_db_base=creations_db_base)
    if path is None:
        result["status"] = "error"
        result["reason"] = "roleplay_prompt.path が空／範囲外（RoleplayPrompts 配下でない）"
        return result
    result["path"] = str(path)

    # 4. charId 一致確認（取り違え防止）
    if num is not None and not _filename_matches_num(path, num):
        result["status"] = "error"
        result["reason"] = f"ファイル名の charId が要求 num={num} と不一致: {path.name}"
        return result

    # 5. 実在確認 + 読み込み
    if not path.exists():
        result["status"] = "error"
        result["reason"] = f"生成物ファイルが存在しない: {path}"
        return result
    result["text"] = path.read_text(encoding="utf-8")
    result["status"] = "ok"
    result["reason"] = "ok"
    return result
