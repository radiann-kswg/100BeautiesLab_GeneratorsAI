"""
utils/paths.py — 生成画像の保存先ディレクトリ組み立てユーティリティ
Copyright © RadianN_kswg — CC BY-NC 4.0

実行ごとに `output/{YYYYMMDD}/{YYYYMMDD_HHMMSS}_{provider}_{form}_num{NNN}/`
のように時刻入りのサブフォルダを切り、過去の生成結果が上書きされないようにする。

レイアウトの方針:
  - ``date_group=True`` (デフォルト): ``{base}/{YYYYMMDD}/{run}/``
    日付フォルダで 1 日分の実行を束ねる。単体実行・バッチ・パイプラインのトップ階層で使用。
  - ``date_group=False``: ``{base}/{run}/``
    日付フォルダを作らず run フォルダを直に置く。パイプラインが各ステージの
    サブディレクトリ配下に子生成を書き出すときに使い、再ネストを防ぐ。
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


def _format_num_for_path(num: int | str) -> str:
    """num をディレクトリ名用の文字列に変換する。
    22 → "022"  "2-alt" → "2-alt"  整数文字列 "22" → "022"
    """
    if isinstance(num, int):
        return f"{num:03d}"
    s = str(num).strip()
    if s.isdigit():
        return f"{int(s):03d}"
    return _sanitize_token(s)


def default_output_base() -> Path:
    """ルートの出力ベースディレクトリ (デフォルト: ``output``)。

    優先順位は ``OUTPUT_BASE_DIR`` → ``OUTPUT_DIR`` → ``output``。
    ``OUTPUT_DIR`` は旧設定との互換用。
    """
    base = os.environ.get("OUTPUT_BASE_DIR") or os.environ.get("OUTPUT_DIR") or "output"
    return Path(base)


def build_run_output_dir(
    provider: str,
    num: int | str,
    form: str,
    base_dir: str | os.PathLike[str] | None = None,
    *,
    timestamp: datetime | None = None,
    suffix: str | None = None,
    create: bool = True,
    nums: list[int | str] | None = None,
    date_group: bool = True,
) -> Path:
    """実行 1 回ぶんの保存先ディレクトリを作って返す。

    形式:
      - ``date_group=True``  → ``{base_dir}/{YYYYMMDD}/{YYYYMMDD_HHMMSS}_{provider}_{form}_num{NNN}[_suffix]/``
      - ``date_group=False`` → ``{base_dir}/{YYYYMMDD_HHMMSS}_{provider}_{form}_num{NNN}[_suffix]/``

    ``date_group=True`` は ``{作業日}/{実行}`` の 2 階層レイアウト。同日の実行が
    ``{YYYYMMDD}/`` 配下にまとまるため、後から振り返りやクリーンアップがしやすい。
    パイプラインが各ステージのサブディレクトリ配下に子生成を書き出すときは
    ``date_group=False`` を使い、日付フォルダの再ネストを防ぐ。

    Parameters
    ----------
    provider:   画像生成プロバイダ名 (例: ``"gemini"`` / ``"openai"``)
    num:        キャラクター番号
    form:       形態 (``"corefolder"`` / ``"humanoid"`` など)
    base_dir:   ベース出力ディレクトリ (省略時は :func:`default_output_base`)
    timestamp:  タイムスタンプ (省略時は現在時刻)
    suffix:     フォルダ名末尾に付与する任意ラベル
    create:     True なら ``mkdir(parents=True, exist_ok=True)`` まで行う
    date_group: True なら ``{YYYYMMDD}/`` の日付フォルダで束ねる。False なら
                run フォルダを base 直下に置く (再ネスト防止)。
    """
    base = Path(base_dir) if base_dir is not None else default_output_base()
    ts_dt = timestamp or datetime.now()
    date_str = ts_dt.strftime("%Y%m%d")
    ts = ts_dt.strftime("%Y%m%d_%H%M%S")
    if nums and len(nums) > 1:
        num_part = "nums" + "_".join(_format_num_for_path(n) for n in nums)
    else:
        num_part = f"num{_format_num_for_path(num)}"
    parts = [ts, _sanitize_token(provider), _sanitize_token(form), num_part]
    if suffix:
        parts.append(_sanitize_token(suffix))
    run_name = "_".join(parts)
    folder = base / date_str / run_name if date_group else base / run_name
    if create:
        folder.mkdir(parents=True, exist_ok=True)
    return folder


__all__ = ["default_output_base", "build_run_output_dir"]
