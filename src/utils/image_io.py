"""
utils/image_io.py — 画像バイト列の MIME を判定して正しい拡張子で保存するユーティリティ
Copyright © RadianN_kswg — CC BY-NC 4.0

Anthropic 等の API は宣言 MIME と実体バイト列が一致しないと
`invalid_request_error (400)` で弾くため、保存側で実体に合わせた拡張子を
付ける必要がある (Gemini が JPEG を返してくるのに `.png` 拡張子で保存されて
しまっていた事例があった)。
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

# (短い拡張子, MIME) のタプル
_FORMAT_PNG = ("png", "image/png")
_FORMAT_JPEG = ("jpg", "image/jpeg")
_FORMAT_GIF = ("gif", "image/gif")
_FORMAT_WEBP = ("webp", "image/webp")
_FORMAT_BMP = ("bmp", "image/bmp")
_FORMAT_TIFF = ("tiff", "image/tiff")

# 公開: MIME → 推奨拡張子
MIME_TO_EXTENSION: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
}


def detect_image_format(header: bytes) -> tuple[str, str] | None:
    """先頭バイトから (短い拡張子, MIME) を判定する。判別不能なら None。"""
    if len(header) < 4:
        return None
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return _FORMAT_PNG
    if header.startswith(b"\xff\xd8\xff"):
        return _FORMAT_JPEG
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return _FORMAT_GIF
    if len(header) >= 12 and header[0:4] == b"RIFF" and header[8:12] == b"WEBP":
        return _FORMAT_WEBP
    if header.startswith(b"BM"):
        return _FORMAT_BMP
    if header.startswith(b"II*\x00") or header.startswith(b"MM\x00*"):
        return _FORMAT_TIFF
    return None


def _strip_known_suffix(name: str, known: Sequence[str]) -> str:
    """末尾が known のいずれかであればその拡張子を取り除いて返す。"""
    lower = name.lower()
    for ext in known:
        if lower.endswith(ext):
            return name[: -len(ext)]
    return name


def save_image_bytes(
    data: bytes | bytearray,
    desired_path: str | Path,
    *,
    fallback_ext: str = ".png",
) -> Path:
    """バイト列を MIME 判定したうえで「実体に合った拡張子」で保存する。

    - ``desired_path`` の拡張子は無視され、実体に合致する拡張子で書き換える。
    - 判別不能な場合は ``fallback_ext`` を使う。
    - 戻り値は実際に書き出したファイルパス。
    """
    payload = bytes(data)
    detected = detect_image_format(payload[:16])
    if detected is not None:
        ext = f".{detected[0]}"
    else:
        ext = fallback_ext

    target = Path(desired_path)
    base_name = _strip_known_suffix(
        target.name,
        tuple(MIME_TO_EXTENSION.values()) + (".jpeg", ".jfif", ".tif"),
    )
    final = target.with_name(base_name + ext)
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_bytes(payload)
    return final


__all__ = [
    "MIME_TO_EXTENSION",
    "detect_image_format",
    "save_image_bytes",
]
