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


def _download_remote_image(url: str) -> Path:
    """GCS URL / 署名 URL を tempfile にダウンロードして Path を返す。

    - ``gs://bucket/key`` は google-cloud-storage で取得
    - ``https://...`` は urllib.request で取得
    失敗時は RuntimeError を送出する。
    """
    # 拡張子を URL から推測して tempfile 名に使う
    parsed_path = urllib.parse.urlparse(url).path.lower()
    suffix = ".jpg"
    for ext in _SUPPORTED_IMAGE_SUFFIXES:
        if parsed_path.endswith(ext):
            suffix = ext
            break

    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        if url.startswith("gs://"):
            try:
                from google.cloud import storage  # type: ignore
            except ImportError as e:
                raise RuntimeError(f"google-cloud-storage が未インストールです: {e}") from e
            # gs://bucket/object-key を分解
            without_scheme = url[5:]  # "bucket/key"
            bucket_name, _, object_key = without_scheme.partition("/")
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(object_key)
            blob.download_to_filename(tmp.name)
        else:
            import urllib.request
            urllib.request.urlretrieve(url, tmp.name)  # noqa: S310
    except Exception as e:
        Path(tmp.name).unlink(missing_ok=True)
        raise RuntimeError(f"リモート画像のダウンロードに失敗しました: {url} — {e}") from e
    finally:
        tmp.close()

    return Path(tmp.name)


def resolve_iterate_source(value: str | Path) -> tuple[Path, Path | None]:
    """``--iterate-from`` の値を ``(画像パス, 起点 run ディレクトリ or None)`` に解決する。

    - 値が GCS URL (``gs://`` / ``https://storage.googleapis.com/...``) なら
      一時ファイルにダウンロードして ``(tmp_path, None)`` を返す
    - 値がファイルなら ``(file, file.parent)`` を返す
    - 値がディレクトリなら、配下の生成画像 (``num*_*``) を 1 つ選んで返す
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
        raise FileNotFoundError(f"iterate-from のパスが存在しません: {value}")

    if path.is_file():
        if path.suffix.lower() not in _SUPPORTED_IMAGE_SUFFIXES:
            raise ValueError(
                f"iterate-from は画像ファイル ({', '.join(_SUPPORTED_IMAGE_SUFFIXES)}) を指定してください: {value}"
            )
        return path, path.parent

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
