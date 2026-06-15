"""
utils/paths.py — 生成画像の保存先ディレクトリ組み立てユーティリティ
Copyright © RadianN_kswg — CC BY-NC 4.0

実行ごとに `output/{YYYYMMDD_HHMMSS}_{provider}_{form}_num{NNN}/` のように
時刻入りのサブフォルダを切り、過去の生成結果が上書きされないようにする。
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

_SAFE_TOKEN_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _sanitize_token(value: str) -> str:
    """フォルダ名として安全な文字列へ正規化する。"""
    text = (value or "").strip().replace(" ", "_")
    text = _SAFE_TOKEN_RE.sub("-", text)
    return text or "x"


def default_output_base() -> Path:
    """ルートの出力ベースディレクトリ (デフォルト: ``output``)。

    優先順位は ``OUTPUT_BASE_DIR`` → ``OUTPUT_DIR`` → ``output``。
    ``OUTPUT_DIR`` は旧設定との互換用。
    """
    base = os.environ.get("OUTPUT_BASE_DIR") or os.environ.get("OUTPUT_DIR") or "output"
    return Path(base)


def build_run_output_dir(
    provider: str,
    num: int,
    form: str,
    base_dir: str | os.PathLike[str] | None = None,
    *,
    timestamp: datetime | None = None,
    suffix: str | None = None,
    create: bool = True,
    nums: list[int] | None = None,
) -> Path:
    """実行 1 回ぶんの保存先ディレクトリを作って返す。

    形式: ``{base_dir}/{YYYYMMDD}/{YYYYMMDD_HH}/{YYYYMMDD_HHMMSS}_{provider}_{form}_num{NNN}[_suffix]/``

    すなわち ``{作業日}/{バッチHH}/{実行}`` の 3 階層レイアウト。同日同時間帯の
    実行が `{YYYYMMDD_HH}/` 配下にまとまるため、後から振り返りやクリーンアップが
    しやすい。

    Parameters
    ----------
    provider:  画像生成プロバイダ名 (例: ``"gemini"`` / ``"openai"``)
    num:       キャラクター番号
    form:      形態 (``"corefolder"`` / ``"humanoid"`` など)
    base_dir:  ベース出力ディレクトリ (省略時は :func:`default_output_base`)
    timestamp: タイムスタンプ (省略時は現在時刻)
    suffix:    フォルダ名末尾に付与する任意ラベル
    create:    True なら ``mkdir(parents=True, exist_ok=True)`` まで行う
    """
    base = Path(base_dir) if base_dir is not None else default_output_base()
    ts_dt = timestamp or datetime.now()
    date_str = ts_dt.strftime("%Y%m%d")
    hour_str = ts_dt.strftime("%Y%m%d_%H")
    ts = ts_dt.strftime("%Y%m%d_%H%M%S")
    if nums and len(nums) > 1:
        num_part = "nums" + "_".join(f"{n:03d}" for n in nums)
    else:
        num_part = f"num{int(num):03d}"
    parts = [ts, _sanitize_token(provider), _sanitize_token(form), num_part]
    if suffix:
        parts.append(_sanitize_token(suffix))
    folder = base / date_str / hour_str / "_".join(parts)
    if create:
        folder.mkdir(parents=True, exist_ok=True)
    return folder


__all__ = ["default_output_base", "build_run_output_dir"]
