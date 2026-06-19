"""tools/check_sync.py — サンドボックス(FUSE)マウントの「同期済み」判定 汎用ツール
Copyright © RadianN_kswg — CC BY-NC 4.0

目的:
    Cowork 等のサンドボックスでは、エディタ(Windows 側)で書き換えた直後の
    ファイルがマウント上で旧版/切り詰め(truncated)として見えることがある
    (eventual consistency)。本ツールは対象ファイルが「壊れず完全に読める」ことを
    確認し、任意で期待部分文字列や SHA256 と照合して同期完了を判定する。
    CI・予約タスク・オーケストレータから繰り返し呼ぶ用途を想定した汎用ユーティリティ。

判定内容:
    1. 存在し、空でないこと
    2. ``.py`` は ``ast.parse`` が通ること(末尾切り詰め=構文崩れを検出)
    3. ``--expect-substr`` 指定時はその文字列を含むこと(機能追加の有無を確認)
    4. ``--expect-sha256`` / ``--manifest`` 指定時はハッシュ一致(厳密同期)

使い方:
    python -m src.tools.check_sync src/pipeline/stage_cli.py
    python -m src.tools.check_sync FILE --expect-substr "main()"
    python -m src.tools.check_sync FILE --expect-sha256 <hex>
    python -m src.tools.check_sync --manifest sync_manifest.json --strict
    python -m src.tools.check_sync FILE --json        # 機械可読出力
    # --strict: 未同期(いずれか pending)で exit 1。予約タスク/CI の分岐に使う。

manifest 形式 (JSON):
    {"files": {"src/pipeline/stage_cli.py": {"expect_substr": "_stage1_combined"},
               "src/utils/dataset.py":      {"sha256": "<hex>"}}}
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
from pathlib import Path


def _read_fresh(path: Path) -> bytes:
    """可能な範囲でページキャッシュを破棄してから読み、最新の実体に寄せる。"""
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        except (AttributeError, OSError):
            pass  # 非対応プラットフォームでは無視
        finally:
            os.close(fd)
    except OSError:
        pass
    return path.read_bytes()


def check_file(
    path: "str | os.PathLike[str]",
    expect_substr: "str | None" = None,
    expect_sha256: "str | None" = None,
) -> "tuple[bool, str]":
    """単一ファイルの同期判定。(synced, detail) を返す。"""
    p = Path(path)
    if not p.exists():
        return False, "not found"
    data = _read_fresh(p)
    if not data:
        return False, "empty"

    if p.suffix == ".py":
        try:
            ast.parse(data.decode("utf-8"))
        except (SyntaxError, UnicodeDecodeError) as e:
            return False, f"truncated/parse-failed ({type(e).__name__})"

    if expect_substr and expect_substr.encode("utf-8") not in data:
        return False, f"missing substr {expect_substr!r}"

    if expect_sha256:
        digest = hashlib.sha256(data).hexdigest()
        if digest.lower() != expect_sha256.lower():
            return False, f"sha256 mismatch (got {digest[:12]}…)"

    return True, f"ok ({len(data)} bytes)"


def _load_manifest(path: "str | os.PathLike[str]") -> dict:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    return obj.get("files", obj) if isinstance(obj, dict) else {}


def main() -> None:
    ap = argparse.ArgumentParser(
        description="FUSE マウントの同期(完全反映)判定 — 汎用ユーティリティ"
    )
    ap.add_argument("files", nargs="*", help="判定対象ファイル(複数可)")
    ap.add_argument("--expect-substr", default=None,
                    help="全対象に共通で要求する部分文字列(機能追加の確認に)")
    ap.add_argument("--expect-sha256", default=None,
                    help="単一対象の期待 SHA256(厳密同期)")
    ap.add_argument("--manifest", default=None,
                    help='JSON マニフェスト: {"files":{path:{expect_substr,sha256}}}')
    ap.add_argument("--strict", action="store_true",
                    help="未同期(いずれか pending)なら exit 1")
    ap.add_argument("--json", action="store_true", help="機械可読 JSON 出力")
    args = ap.parse_args()

    targets: "list[tuple[str, str | None, str | None]]" = []
    if args.manifest:
        for fp, meta in _load_manifest(args.manifest).items():
            meta = meta or {}
            targets.append((fp, meta.get("expect_substr"), meta.get("sha256")))
    for fp in args.files:
        single = len(args.files) == 1
        targets.append((fp, args.expect_substr, args.expect_sha256 if single else None))

    if not targets:
        ap.error("対象ファイルか --manifest を指定してください。")

    results = []
    all_ok = True
    for fp, substr, sha in targets:
        ok, detail = check_file(fp, substr, sha)
        all_ok = all_ok and ok
        results.append({"file": str(fp), "synced": ok, "detail": detail})
        if not args.json:
            print(f"[{'OK  ' if ok else 'WAIT'}] {fp} — {detail}")

    synced_n = sum(1 for r in results if r["synced"])
    if args.json:
        print(json.dumps(
            {"all_synced": all_ok, "synced": synced_n, "total": len(results),
             "results": results},
            ensure_ascii=False, indent=2,
        ))
    else:
        state = "完了 (all synced)" if all_ok else "未完 (pending)"
        print(f"\n同期: {state} / {synced_n}/{len(results)}")

    if args.strict and not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
