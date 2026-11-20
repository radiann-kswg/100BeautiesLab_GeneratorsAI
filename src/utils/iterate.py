"""
utils/iterate.py — 直前 run の生成画像を起点に追加指示で再生成 (i2i) するためのヘルパー
Copyright © RadianN_kswg — CC BY-NC 4.0

Gemini / OpenAI どちらの generate スクリプトからも使う想定で、
- 入力された ``--iterate-from`` 値 (画像ファイル or run ディレクトリ or GCS URL) を画像パスへ解決
- ファイル名 / 親ディレクトリ名から ``iterN`` カウンタを推測し、次の番号を返す
の 2 つを提供する。

GCS URL 対応:
  ``gs://`` または署名 URL (https://storage.googleapis.com/...) を渡すと
  tempfile に自動ダウンロードして扱う。
"""

from __future__ import annotations

import re
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

_SUPPORTED_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
_ITER_TOKEN_RE = re.compile(r"iter(\d+)", re.IGNORECASE)

# GCS URL パターン判定
_GCS_SIGNED_URL_RE = re.compile(
    r"^https://storage\.googleapis\.com/|"
    r"^https://[^/]+\.storage\.googleapis\.com/|"
    r"^https://storage\.cloud\.google\.com/",
    re.IGNORECASE,
)


def _is_remote_url(value: str) -> bool:
    """GCS 署名 URL または gs:// スキームかどうかを判定する。"""
    return value.startswith("gs://") or bool(_GCS_SIGNED_URL_RE.match(value))


REMOTE_MAX_BYTES = 10 * 1024 * 1024
_REMOTE_TIMEOUT_SEC = 30


def _own_object(url: str) -> tuple[str, str]:
    """URL を (バケット, オブジェクトキー) に分け、このサーバーの置き場のものか確かめる。

    受け付けるのは ``GCS_BUCKET`` の ``GCS_PREFIX``（既定 numbertales）の下だけ。同じ形の URL でも、
    ほかのバケットやほかの用途の接頭辞の画像は起点にしない。
    """
    import os

    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path).lstrip("/")
    host = (parsed.netloc or "").lower()
    if parsed.scheme == "gs":
        bucket, key = parsed.netloc, path
    elif host in ("storage.googleapis.com", "storage.cloud.google.com"):
        bucket, _, key = path.partition("/")
    else:                                           # https://<bucket>.storage.googleapis.com/<key>
        bucket, key = host.removesuffix(".storage.googleapis.com"), path
    own_bucket = os.environ.get("GCS_BUCKET", "").strip()
    prefix = os.environ.get("GCS_PREFIX", "numbertales").strip("/") or "numbertales"
    if not own_bucket:
        raise RuntimeError("GCS_BUCKET が未設定のため、リモートの画像を起点にできません。")
    if bucket != own_bucket or not key.startswith(f"{prefix}/") or ".." in key.split("/"):
        raise RuntimeError(f"起点にできるのは、このサーバーのバケットの {prefix}/ の下の画像だけです。")
    return bucket, key


def _download_remote_image(url: str) -> Path:
    """GCS URL / 署名 URL を tempfile にダウンロードして Path を返す。

    - 受け付けるのは、このサーバーの置き場（``_own_object``）の画像だけ
    - ``gs://bucket/key`` は google-cloud-storage、``https://...`` は urllib で取得する
    - ``_REMOTE_TIMEOUT_SEC`` 秒で打ち切り、``REMOTE_MAX_BYTES`` を超える画像は受け付けない
    失敗時は RuntimeError を送出する。
    """
    bucket_name, object_key = _own_object(url)
    suffix = next((ext for ext in _SUPPORTED_IMAGE_SUFFIXES if object_key.lower().endswith(ext)), ".jpg")
    try:
        if url.startswith("gs://"):
            try:
                from google.cloud import storage  # type: ignore
            except ImportError as e:
                raise RuntimeError(f"google-cloud-storage が未インストールです: {e}") from e
            blob = storage.Client().bucket(bucket_name).get_blob(object_key)
            if blob is None:
                raise RuntimeError("オブジェクトが見つかりません")
            if int(blob.size or 0) > REMOTE_MAX_BYTES:
                raise RuntimeError(f"画像が大きすぎます（上限 {REMOTE_MAX_BYTES // (1024 * 1024)}MB）")
            data = blob.download_as_bytes(timeout=_REMOTE_TIMEOUT_SEC)
        else:
            with urllib.request.urlopen(url, timeout=_REMOTE_TIMEOUT_SEC) as response:  # noqa: S310 — 上で自分の置き場に限定済み
                data = response.read(REMOTE_MAX_BYTES + 1)
            if len(data) > REMOTE_MAX_BYTES:
                raise RuntimeError(f"画像が大きすぎます（上限 {REMOTE_MAX_BYTES // (1024 * 1024)}MB）")
    except RuntimeError as e:
        raise RuntimeError(f"リモート画像のダウンロードに失敗しました: {url[:120]} — {e}") from e
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"リモート画像のダウンロードに失敗しました: {url[:120]} — {e}") from e
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
    return Path(tmp.name)


_RUN_NAME_RE = re.compile(r"^\d{8}_\d{6}_[\w-]+$")


def _locate_run(value: str) -> Path | None:
    """実行フォルダー名だけの指定を、出力フォルダーの中の実行フォルダーに解決する。

    手元に無く、出力先が GCS か Drive の設定なら、GCS の ``<接頭辞>/runs/`` から戻す。見つからなければ None。
    """
    from src.utils.paths import default_output_base

    if not _RUN_NAME_RE.match(value):
        return None
    local = default_output_base() / value[:8] / value
    if local.is_dir():
        return local
    from src.mcp_server import output_sink

    if output_sink.current_sink() == "local":
        return None
    restored = output_sink.restore_run(value, default_output_base())
    if restored is not None:
        print(f"[iterate] 実行 {value} を GCS から戻しました → {restored}")
    return restored


def _pipeline_final(run_dir: Path) -> Path | None:
    """パイプラインの実行フォルダーの記録から、完成画像の先頭を返す（記録が無い・画像が無いなら None）。"""
    import json

    summary_file = run_dir / "pipeline_summary.json"
    if not summary_file.is_file():
        return None
    from src.mcp_server import output_sink

    try:
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(summary, dict):
        return None
    for rel in output_sink.run_final_files(summary, run_dir.name):
        candidate = run_dir.joinpath(*rel.parts)
        if candidate.is_file() and candidate.suffix.lower() in _SUPPORTED_IMAGE_SUFFIXES:
            return candidate
    return None


def resolve_iterate_source(value: str | Path) -> tuple[Path, Path | None]:
    """``--iterate-from`` の値を ``(画像パス, 起点 run ディレクトリ or None)`` に解決する。

    - 値が GCS URL (``gs://`` / ``https://storage.googleapis.com/...``) なら
      一時ファイルにダウンロードして ``(tmp_path, None)`` を返す
    - 値がファイルなら ``(file, file.parent)`` を返す
    - 値がパイプラインの実行フォルダー (``pipeline_summary.json`` がある) なら、記録にある完成画像の先頭を返す
    - 値がそれ以外のディレクトリなら、配下の生成画像 (``num*_*``) を 1 つ選んで返す
    - 値が実行フォルダー名 (``20261120_150049_pipeline_corefolder_num57`` など) だけなら、出力フォルダーから探し、
      無ければ GCS の ``<接頭辞>/runs/`` から戻す (コネクタのサーバーが止まって出力フォルダーが消えたあと)
    - 解決できない場合は ``FileNotFoundError`` / ``RuntimeError`` を投げる
    """
    str_value = str(value)

    # ── GCS URL / 署名 URL の場合は一時ファイルへダウンロード ──
    if _is_remote_url(str_value):
        print(f"[iterate] GCS URL を検出 — ダウンロード中: {str_value[:80]}...")
        tmp_path = _download_remote_image(str_value)
        print(f"[iterate] ダウンロード完了 → {tmp_path}")
        return tmp_path, None

    path = Path(value)
    if not path.exists():
        located = _locate_run(str_value)
        if located is None:
            raise FileNotFoundError(f"iterate-from のパスが存在しません: {value}")
        path = located

    if path.is_file():
        if path.suffix.lower() not in _SUPPORTED_IMAGE_SUFFIXES:
            raise ValueError(
                f"iterate-from は画像ファイル ({', '.join(_SUPPORTED_IMAGE_SUFFIXES)}) を指定してください: {value}"
            )
        return path, path.parent

    # パイプラインの実行フォルダーなら、記録にある完成画像の先頭を起点にする。
    final = _pipeline_final(path)
    if final is not None:
        return final, path

    # ディレクトリの場合: 配下の `num*_*.{png,jpg,...}` を新しいもの順で探す。
    candidates: list[Path] = []
    for suffix in _SUPPORTED_IMAGE_SUFFIXES:
        candidates.extend(path.glob(f"num*{suffix}"))
    if not candidates:
        # 想定外の命名でも、画像が 1 枚しか無いケースは拾う。
        for suffix in _SUPPORTED_IMAGE_SUFFIXES:
            candidates.extend(path.glob(f"*{suffix}"))
    if not candidates:
        raise FileNotFoundError(
            f"iterate-from の指定ディレクトリ配下に生成画像が見つかりません: {value}"
        )
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0], path


def next_iteration_label(source_path: Path) -> str:
    """起点画像から次の ``iterN`` ラベルを推測する。

    - 起点ファイル名 / 親ディレクトリ名に ``iterN`` が含まれていれば ``iter(N+1)``
    - 含まれていなければ ``iter1``
    """
    haystacks = [source_path.name]
    if source_path.parent is not None:
        haystacks.append(source_path.parent.name)
    max_seen: int | None = None
    for text in haystacks:
        for match in _ITER_TOKEN_RE.finditer(text):
            try:
                value = int(match.group(1))
            except ValueError:
                continue
            if max_seen is None or value > max_seen:
                max_seen = value
    if max_seen is None:
        return "iter1"
    return f"iter{max_seen + 1}"


def parse_revisions(value: str | None) -> list[str]:
    """``--revisions`` の文字列を ``;`` / 改行で分割した list に正規化する。"""
    if not value:
        return []
    parts: list[str] = []
    for chunk in re.split(r"[;\n]+", value):
        text = chunk.strip()
        if text:
            parts.append(text)
    return parts


__all__ = [
    "resolve_iterate_source",
    "next_iteration_label",
    "parse_revisions",
    "is_remote_url",
]


def is_remote_url(value: str) -> bool:
    """GCS URL かどうかを外部から確認するためのパブリックラッパー。"""
    return _is_remote_url(str(value))
