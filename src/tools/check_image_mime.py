"""
src/tools/check_image_mime.py — 画像ファイルの拡張子と実体フォーマットの不一致を検出・修正するツール
Copyright © RadianN_kswg — CC BY-NC 4.0

背景:
    Anthropic などのモデル API は、入力画像の MIME 宣言と実体バイト列が
    一致しない場合 400 (`invalid_request_error`) で弾く。たとえば
    `image/png` と宣言された base64 が中身 JPEG だと履歴ごとリクエストが
    失敗してしまうため、生成済み画像を早期にスキャンして検知しておく。

使い方:
    # output/ 配下を再帰スキャンしてミスマッチを一覧表示 (デフォルト)
    python -m src.tools.check_image_mime

    # 任意ディレクトリを複数指定 (output と _ideas を同時にスキャン)
    python -m src.tools.check_image_mime output _ideas

    # 拡張子をリネームして実体に揃える (例: .png 中身 jpeg → .jpg)
    python -m src.tools.check_image_mime --fix-rename

    # 実体を拡張子に合わせて再エンコード (Pillow を使用)
    python -m src.tools.check_image_mime --fix-reencode

    # CI 用: ミスマッチがあれば exit code 1
    python -m src.tools.check_image_mime --strict

検出対象: PNG / JPEG / GIF / WEBP / BMP / TIFF
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from src.utils.image_io import detect_image_format

# --------------------------------------------------------------------------
# マジックバイト判定
# --------------------------------------------------------------------------

# 既知のフォーマット表 (拡張子小文字（ドット込み） → (短い拡張子, MIME))
_FORMAT_PNG = ("png", "image/png")
_FORMAT_JPEG = ("jpg", "image/jpeg")
_FORMAT_GIF = ("gif", "image/gif")
_FORMAT_WEBP = ("webp", "image/webp")
_FORMAT_BMP = ("bmp", "image/bmp")
_FORMAT_TIFF = ("tiff", "image/tiff")

# 拡張子 → 期待される実体フォーマットのキー
_EXTENSION_TO_FORMAT = {
    ".png": _FORMAT_PNG,
    ".jpg": _FORMAT_JPEG,
    ".jpeg": _FORMAT_JPEG,
    ".jfif": _FORMAT_JPEG,
    ".gif": _FORMAT_GIF,
    ".webp": _FORMAT_WEBP,
    ".bmp": _FORMAT_BMP,
    ".tif": _FORMAT_TIFF,
    ".tiff": _FORMAT_TIFF,
}

# 走査対象の画像拡張子
_IMAGE_EXTENSIONS = set(_EXTENSION_TO_FORMAT.keys())


def detect_format(header: bytes) -> tuple[str, str] | None:
    """``src.utils.image_io.detect_image_format`` へのラッパ (互換のため残置)。"""
    return detect_image_format(header)


# --------------------------------------------------------------------------
# データ構造
# --------------------------------------------------------------------------


@dataclass
class ImageFinding:
    path: Path
    extension: str
    declared_mime: str | None  # 拡張子から期待される MIME
    actual_short: str | None   # 実体の短い拡張子 ("png" 等)
    actual_mime: str | None    # 実体の MIME
    note: str = ""             # "mismatch" / "unknown" / "ok" / "unreadable"

    @property
    def is_mismatch(self) -> bool:
        return self.note == "mismatch"

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "extension": self.extension,
            "declared_mime": self.declared_mime,
            "actual_mime": self.actual_mime,
            "note": self.note,
        }


@dataclass
class ScanResult:
    scanned: int = 0
    mismatches: list[ImageFinding] = field(default_factory=list)
    unknowns: list[ImageFinding] = field(default_factory=list)
    unreadable: list[ImageFinding] = field(default_factory=list)


# --------------------------------------------------------------------------
# スキャン本体
# --------------------------------------------------------------------------


def iter_image_files(roots: Iterable[Path]) -> Iterable[Path]:
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix.lower() in _IMAGE_EXTENSIONS:
                resolved = root.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield root
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in _IMAGE_EXTENSIONS:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path


def inspect_file(path: Path) -> ImageFinding:
    ext = path.suffix.lower()
    expected = _EXTENSION_TO_FORMAT.get(ext)
    declared_mime = expected[1] if expected else None
    try:
        with path.open("rb") as fh:
            header = fh.read(16)
    except OSError as exc:
        return ImageFinding(
            path=path,
            extension=ext,
            declared_mime=declared_mime,
            actual_short=None,
            actual_mime=None,
            note=f"unreadable: {exc.__class__.__name__}",
        )
    actual = detect_format(header)
    if actual is None:
        return ImageFinding(
            path=path,
            extension=ext,
            declared_mime=declared_mime,
            actual_short=None,
            actual_mime=None,
            note="unknown",
        )
    actual_short, actual_mime = actual
    if declared_mime is None:
        # 拡張子側が想定外。基本的にここには来ないが念のため
        return ImageFinding(
            path=path,
            extension=ext,
            declared_mime=None,
            actual_short=actual_short,
            actual_mime=actual_mime,
            note="unknown",
        )
    if actual_mime == declared_mime:
        return ImageFinding(
            path=path,
            extension=ext,
            declared_mime=declared_mime,
            actual_short=actual_short,
            actual_mime=actual_mime,
            note="ok",
        )
    return ImageFinding(
        path=path,
        extension=ext,
        declared_mime=declared_mime,
        actual_short=actual_short,
        actual_mime=actual_mime,
        note="mismatch",
    )


def scan(roots: Iterable[Path]) -> ScanResult:
    result = ScanResult()
    for path in iter_image_files(roots):
        result.scanned += 1
        finding = inspect_file(path)
        if finding.is_mismatch:
            result.mismatches.append(finding)
        elif finding.note == "unknown":
            result.unknowns.append(finding)
        elif finding.note.startswith("unreadable"):
            result.unreadable.append(finding)
    return result


# --------------------------------------------------------------------------
# 修正系
# --------------------------------------------------------------------------


def _unique_target(target: Path) -> Path:
    """衝突回避: foo.jpg が既にあれば foo.1.jpg, foo.2.jpg... を試す。"""
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}.{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def fix_by_rename(findings: list[ImageFinding], *, dry_run: bool = False) -> list[tuple[Path, Path]]:
    """拡張子を実体に合わせてリネームする。戻り値は (src, dst) のリスト。"""
    moves: list[tuple[Path, Path]] = []
    for finding in findings:
        if finding.actual_short is None:
            continue
        new_ext = f".{finding.actual_short}"
        target = _unique_target(finding.path.with_suffix(new_ext))
        moves.append((finding.path, target))
        if dry_run:
            continue
        finding.path.rename(target)
    return moves


def fix_by_reencode(findings: list[ImageFinding], *, dry_run: bool = False) -> list[Path]:
    """実体を拡張子側の MIME に合わせて Pillow で再エンコードする。"""
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "Pillow が見つかりません。`pip install Pillow` で導入してください。"
        ) from exc

    # Pillow 出力フォーマットへの対応表 (拡張子 → save format 引数)
    pil_format_map = {
        ".png": "PNG",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".jfif": "JPEG",
        ".gif": "GIF",
        ".webp": "WEBP",
        ".bmp": "BMP",
        ".tif": "TIFF",
        ".tiff": "TIFF",
    }
    converted: list[Path] = []
    for finding in findings:
        target_format = pil_format_map.get(finding.extension)
        if target_format is None:
            continue
        if dry_run:
            converted.append(finding.path)
            continue
        with Image.open(finding.path) as img:
            # JPEG は RGBA を許容しないので必要なら RGB に落とす
            save_img = img
            if target_format == "JPEG" and img.mode in ("RGBA", "LA", "P"):
                save_img = img.convert("RGB")
            tmp_path = finding.path.with_suffix(finding.extension + ".tmp")
            save_img.save(tmp_path, format=target_format)
        tmp_path.replace(finding.path)
        converted.append(finding.path)
    return converted


# --------------------------------------------------------------------------
# 出力
# --------------------------------------------------------------------------


def render_table(findings: list[ImageFinding], title: str) -> str:
    if not findings:
        return ""
    lines = [f"\n## {title} ({len(findings)} 件)", ""]
    lines.append(f"{'PATH':<70} {'EXT':<6} {'DECLARED':<14} {'ACTUAL':<14} NOTE")
    lines.append("-" * 120)
    for f in findings:
        lines.append(
            f"{str(f.path):<70} {f.extension:<6} "
            f"{(f.declared_mime or '-'): <14} {(f.actual_mime or '-'): <14} {f.note}"
        )
    return "\n".join(lines)


def render_summary(result: ScanResult, roots: list[Path]) -> str:
    lines = [
        "==== check_image_mime ====",
        f"scanned roots: {', '.join(str(r) for r in roots) or '(none)'}",
        f"scanned files: {result.scanned}",
        f"mismatches   : {len(result.mismatches)}",
        f"unknowns     : {len(result.unknowns)}",
        f"unreadable   : {len(result.unreadable)}",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.tools.check_image_mime",
        description="画像ファイルの拡張子と実体フォーマットの不一致を検出するツール。",
    )
    parser.add_argument(
        "roots",
        nargs="*",
        help="スキャン対象のパス (ファイル/ディレクトリ)。省略時は `output` を再帰スキャン。",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="人間可読の表ではなく JSON で結果を出力する。",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="ミスマッチや unreadable が 1 件以上あれば exit code 1。CI 用。",
    )
    fix_group = parser.add_mutually_exclusive_group()
    fix_group.add_argument(
        "--fix-rename",
        action="store_true",
        help="ミスマッチを拡張子変更で解消する (例: 中身 JPEG の .png → .jpg)。",
    )
    fix_group.add_argument(
        "--fix-reencode",
        action="store_true",
        help="ミスマッチを Pillow で再エンコードして拡張子側に合わせる。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="--fix-* 指定時に、実際にはファイルを書き換えず何を実行するかだけ出力。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    roots = [Path(r) for r in (args.roots or ["output"])]
    result = scan(roots)

    fix_actions: dict[str, list] = {}
    if args.fix_rename and result.mismatches:
        moves = fix_by_rename(result.mismatches, dry_run=args.dry_run)
        fix_actions["renamed"] = [
            {"from": str(s), "to": str(d)} for s, d in moves
        ]
    elif args.fix_reencode and result.mismatches:
        converted = fix_by_reencode(result.mismatches, dry_run=args.dry_run)
        fix_actions["reencoded"] = [str(p) for p in converted]

    if args.json:
        payload = {
            "scanned": result.scanned,
            "roots": [str(r) for r in roots],
            "mismatches": [f.to_dict() for f in result.mismatches],
            "unknowns": [f.to_dict() for f in result.unknowns],
            "unreadable": [f.to_dict() for f in result.unreadable],
            "fix_actions": fix_actions,
            "dry_run": args.dry_run,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_summary(result, roots))
        table = render_table(result.mismatches, "MISMATCHES (拡張子と実体が不一致)")
        if table:
            print(table)
        table = render_table(result.unknowns, "UNKNOWNS (実体フォーマット判別不能)")
        if table:
            print(table)
        table = render_table(result.unreadable, "UNREADABLE (読み取りエラー)")
        if table:
            print(table)
        if fix_actions:
            print("\n## FIX ACTIONS" + (" (dry-run)" if args.dry_run else ""))
            print(json.dumps(fix_actions, ensure_ascii=False, indent=2))

    if args.strict and (result.mismatches or result.unreadable):
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
