"""
src/tools/migrate_output_layout.py — output/ 配下を `{作業日}/{バッチHH}/{実行}/` 階層へ統一するマイグレーションツール
Copyright © RadianN_kswg — CC BY-NC 4.0

目標レイアウト:

    output/
      {YYYYMMDD}/                              ← 作業日
        {YYYYMMDD_HH}/                         ← その時間帯の一括バッチ
          {YYYYMMDD_HHMMSS}_{provider}_{form}_num{NNN}/  ← 1 実行
            prompt.txt
            run_meta.json
            notes.md
            *.png / *.jpg ...

既存レイアウトの対応パターン:

    1. `output/{date}/{date}_{HH}/{ts}_{provider}_{form}_num{NNN}/` (理想形)
        → 何もしない (skip)
    2. `output/{date}/{ts}_{provider}_{form}_num{NNN}/` (HH 階層なし)
        → `{date}_{HH}/` を挟む形で移動
    3. `output/{ts}_{provider}_{form}_num{NNN}/` (date/HH 階層なし)
        → `output/{date}/{date}_{HH}/` 配下へ移動
    4. `output/{date}/{date}_{HH}/{date}_{HH}_{provider}/{file}` (バッチ一括ファイル散在)
        → ファイル名から (form, num) を推測し、
           `{date}_{HH}0000_{provider}_{form}_num{NNN}/{file}` に集約
    5. `output/{date}/{provider}/{file}` (日時情報なし旧フォーマット)
        → `{date}_00/{date}_000000_{provider}_{form}_num{NNN}/{file}` に集約

使い方:

    # 計画だけ確認 (デフォルトで output/)
    python -m src.tools.migrate_output_layout --dry-run

    # 実行 (移動)
    python -m src.tools.migrate_output_layout

    # 任意のベースを指定
    python -m src.tools.migrate_output_layout --base output --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# ----------------------------------------------------------------------
# 定数 / 正規表現
# ----------------------------------------------------------------------

_DATE_RE = re.compile(r"^\d{8}$")
_DATE_HH_RE = re.compile(r"^(\d{8})_(\d{2})$")
_RUN_DIR_RE = re.compile(
    r"^(?P<date>\d{8})_(?P<hh>\d{2})(?P<mmss>\d{4})_(?P<provider>[A-Za-z0-9]+)_"
    r"(?P<form>[A-Za-z0-9-]+)_num(?P<num>\d{3})(?:_(?P<suffix>[A-Za-z0-9-]+))?$"
)
_BATCH_PROVIDER_DIR_RE = re.compile(r"^(\d{8})_(\d{2})_([A-Za-z0-9]+)$")
_PROVIDER_DIR_RE = re.compile(r"^(gemini|openai|anthropic|novelai)$", re.IGNORECASE)

# ファイル名パターン: num057_corefolder_01.png / num057_humanoid_dalle.png / num057_corefolder_flash.png
_IMAGE_FILE_RE = re.compile(
    r"^num(?P<num>\d{3})_(?P<form>corefolder|humanoid)_(?P<tag>[A-Za-z0-9]+)\.(?P<ext>[A-Za-z0-9]+)$"
)

# ----------------------------------------------------------------------
# データ構造
# ----------------------------------------------------------------------


@dataclass
class MoveAction:
    src: Path
    dst: Path
    kind: str  # "rename_dir" / "move_file" / "create_dir"
    note: str = ""


@dataclass
class MigrationPlan:
    actions: list[MoveAction] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------
# 補助
# ----------------------------------------------------------------------


def _safe_unique(target: Path) -> Path:
    if not target.exists():
        return target
    parent = target.parent
    if target.is_dir():
        base = target.name
        counter = 1
        while True:
            cand = parent / f"{base}.dup{counter}"
            if not cand.exists():
                return cand
            counter += 1
    stem = target.stem
    suffix = target.suffix
    counter = 1
    while True:
        cand = parent / f"{stem}.dup{counter}{suffix}"
        if not cand.exists():
            return cand
        counter += 1


def _parse_run_dir(name: str) -> dict | None:
    match = _RUN_DIR_RE.match(name)
    if not match:
        return None
    return match.groupdict()


def _classify_image_file(name: str) -> dict | None:
    match = _IMAGE_FILE_RE.match(name)
    if not match:
        return None
    return match.groupdict()


# ----------------------------------------------------------------------
# プラン生成
# ----------------------------------------------------------------------


def _plan_run_dir_relocation(
    run_dir: Path,
    base: Path,
    plan: MigrationPlan,
) -> None:
    """`{ts}_{provider}_{form}_numNNN/` 形式の実行ディレクトリを正規位置に再配置。"""
    info = _parse_run_dir(run_dir.name)
    if info is None:
        plan.warnings.append(f"run dir 解析失敗: {run_dir}")
        return
    date = info["date"]
    hh = info["hh"]
    target = base / date / f"{date}_{hh}" / run_dir.name
    try:
        if run_dir.resolve() == target.resolve():
            plan.skipped.append((run_dir, "already in canonical location"))
            return
    except OSError:
        pass
    final_target = _safe_unique(target)
    plan.actions.append(
        MoveAction(
            src=run_dir,
            dst=final_target,
            kind="rename_dir",
            note="run dir → canonical layout",
        )
    )


def _plan_batch_provider_dir(
    batch_dir: Path,
    date: str,
    hh: str,
    provider: str,
    base: Path,
    plan: MigrationPlan,
) -> None:
    """`{date}_{HH}_{provider}/` 配下の散在ファイルを実行フォルダへ集約。"""
    file_groups: dict[tuple[str, str], list[Path]] = {}
    other_files: list[Path] = []
    for child in batch_dir.iterdir():
        if child.is_dir():
            plan.warnings.append(f"batch dir 内に予期しないサブディレクトリ: {child}")
            continue
        meta = _classify_image_file(child.name)
        if meta is None:
            other_files.append(child)
            continue
        key = (meta["num"], meta["form"])
        file_groups.setdefault(key, []).append(child)

    parent_batch = base / date / f"{date}_{hh}"
    # 各 (num, form) ペアにつき 1 実行フォルダを切る
    # タイムスタンプは {date}_{hh}0000 を使い、競合時は秒を +1 する
    seconds_counter = 0
    for (num, form), files in sorted(file_groups.items()):
        ts = f"{date}_{hh}00{seconds_counter:02d}"
        seconds_counter += 1
        run_dir_name = f"{ts}_{provider}_{form}_num{num}"
        run_dir = parent_batch / run_dir_name
        plan.actions.append(
            MoveAction(
                src=batch_dir,
                dst=run_dir,
                kind="create_dir",
                note=f"reconstructed run dir for num{num}/{form}",
            )
        )
        for f in sorted(files):
            target = run_dir / f.name
            plan.actions.append(
                MoveAction(
                    src=f,
                    dst=target,
                    kind="move_file",
                    note=f"batch file → run dir",
                )
            )

    for f in other_files:
        plan.warnings.append(f"batch dir 内に分類不能ファイル (保留): {f}")

    # 元の batch_dir は最後に空であれば削除対象としてマークする
    plan.actions.append(
        MoveAction(
            src=batch_dir,
            dst=batch_dir,
            kind="cleanup_empty_dir",
            note="batch provider dir を移動後に削除",
        )
    )


def _plan_dateless_provider_dir(
    provider_dir: Path,
    date: str,
    provider: str,
    base: Path,
    plan: MigrationPlan,
) -> None:
    """`{date}/{provider}/{file}` 旧フォーマットを `{date}_00` バッチ扱いで集約。"""
    file_groups: dict[tuple[str, str], list[Path]] = {}
    other_files: list[Path] = []
    for child in provider_dir.iterdir():
        if child.is_dir():
            plan.warnings.append(f"provider dir 内に予期しないサブディレクトリ: {child}")
            continue
        meta = _classify_image_file(child.name)
        if meta is None:
            other_files.append(child)
            continue
        key = (meta["num"], meta["form"])
        file_groups.setdefault(key, []).append(child)

    parent_batch = base / date / f"{date}_00"
    seconds_counter = 0
    for (num, form), files in sorted(file_groups.items()):
        ts = f"{date}_0000{seconds_counter:02d}"
        seconds_counter += 1
        run_dir_name = f"{ts}_{provider}_{form}_num{num}"
        run_dir = parent_batch / run_dir_name
        plan.actions.append(
            MoveAction(
                src=provider_dir,
                dst=run_dir,
                kind="create_dir",
                note=f"reconstructed run dir for num{num}/{form} (no timestamp source)",
            )
        )
        for f in sorted(files):
            target = run_dir / f.name
            plan.actions.append(
                MoveAction(
                    src=f,
                    dst=target,
                    kind="move_file",
                    note="dateless provider dir → run dir",
                )
            )

    for f in other_files:
        plan.warnings.append(f"provider dir 内に分類不能ファイル (保留): {f}")

    plan.actions.append(
        MoveAction(
            src=provider_dir,
            dst=provider_dir,
            kind="cleanup_empty_dir",
            note="dateless provider dir を移動後に削除",
        )
    )


def build_plan(base: Path) -> MigrationPlan:
    plan = MigrationPlan()
    if not base.is_dir():
        plan.warnings.append(f"base が存在しない / ディレクトリでない: {base}")
        return plan

    for top in sorted(base.iterdir()):
        if not top.is_dir():
            continue
        name = top.name
        # ルート直下の {ts}_{provider}_{form}_numNNN/
        if _parse_run_dir(name):
            _plan_run_dir_relocation(top, base, plan)
            continue
        # 日付ディレクトリ
        if _DATE_RE.match(name):
            date = name
            for sub in sorted(top.iterdir()):
                if not sub.is_dir():
                    plan.warnings.append(f"日付ディレクトリ直下のファイル (保留): {sub}")
                    continue
                sub_name = sub.name
                # 既に {date}_{HH}/ ならその配下の実行ディレクトリを正規化
                m_hh = _DATE_HH_RE.match(sub_name)
                if m_hh and m_hh.group(1) == date:
                    for run_or_batch in sorted(sub.iterdir()):
                        if not run_or_batch.is_dir():
                            plan.warnings.append(
                                f"{date}_{m_hh.group(2)}/ 直下のファイル (保留): {run_or_batch}"
                            )
                            continue
                        rb_name = run_or_batch.name
                        if _parse_run_dir(rb_name):
                            _plan_run_dir_relocation(run_or_batch, base, plan)
                            continue
                        m_batch = _BATCH_PROVIDER_DIR_RE.match(rb_name)
                        if m_batch and m_batch.group(1) == date and m_batch.group(2) == m_hh.group(2):
                            _plan_batch_provider_dir(
                                run_or_batch,
                                date=date,
                                hh=m_hh.group(2),
                                provider=m_batch.group(3).lower(),
                                base=base,
                                plan=plan,
                            )
                            continue
                        plan.warnings.append(f"{date}_{m_hh.group(2)}/ 配下の分類不能ディレクトリ: {run_or_batch}")
                    continue
                # `{date}/{ts}_{provider}_{form}_numNNN/` 形式 (HH 階層なし)
                if _parse_run_dir(sub_name):
                    _plan_run_dir_relocation(sub, base, plan)
                    continue
                # `{date}/{provider}/{file}` 旧フォーマット
                if _PROVIDER_DIR_RE.match(sub_name):
                    _plan_dateless_provider_dir(
                        sub,
                        date=date,
                        provider=sub_name.lower(),
                        base=base,
                        plan=plan,
                    )
                    continue
                plan.warnings.append(f"日付ディレクトリ配下の分類不能サブディレクトリ: {sub}")
            continue
        plan.warnings.append(f"トップレベルの分類不能ディレクトリ: {top}")

    return plan


# ----------------------------------------------------------------------
# プラン適用
# ----------------------------------------------------------------------


def apply_plan(plan: MigrationPlan) -> list[str]:
    """プランを実際にファイルシステムへ反映する。各種操作のログを返す。"""
    log: list[str] = []
    # 1) ディレクトリリネーム (rename_dir) を先にやると、その後 move_file の src が変わってしまうため、
    #    順序通り (insertion order) に処理する。ただし cleanup_empty_dir は最後。
    deferred_cleanups: list[MoveAction] = []
    created_dirs: set[Path] = set()
    for action in plan.actions:
        if action.kind == "cleanup_empty_dir":
            deferred_cleanups.append(action)
            continue
        if action.kind == "rename_dir":
            action.dst.parent.mkdir(parents=True, exist_ok=True)
            target = _safe_unique(action.dst) if action.dst.exists() else action.dst
            shutil.move(str(action.src), str(target))
            log.append(f"[rename_dir] {action.src} -> {target}")
            continue
        if action.kind == "create_dir":
            action.dst.mkdir(parents=True, exist_ok=True)
            created_dirs.add(action.dst)
            log.append(f"[create_dir] {action.dst} ({action.note})")
            continue
        if action.kind == "move_file":
            action.dst.parent.mkdir(parents=True, exist_ok=True)
            target = _safe_unique(action.dst) if action.dst.exists() else action.dst
            shutil.move(str(action.src), str(target))
            log.append(f"[move_file] {action.src} -> {target}")
            continue
        log.append(f"[skip] 未対応 kind: {action.kind} ({action.src})")

    for action in deferred_cleanups:
        try:
            if action.src.exists() and action.src.is_dir() and not any(action.src.iterdir()):
                action.src.rmdir()
                log.append(f"[cleanup_empty_dir] removed empty: {action.src}")
            else:
                log.append(f"[cleanup_empty_dir] skipped (not empty or gone): {action.src}")
        except OSError as exc:
            log.append(f"[cleanup_empty_dir] error on {action.src}: {exc}")

    return log


# ----------------------------------------------------------------------
# 出力
# ----------------------------------------------------------------------


def render_plan(plan: MigrationPlan) -> str:
    lines: list[str] = []
    lines.append(f"actions : {len(plan.actions)}")
    lines.append(f"skipped : {len(plan.skipped)}")
    lines.append(f"warnings: {len(plan.warnings)}")
    if plan.actions:
        lines.append("\n## ACTIONS")
        for a in plan.actions:
            arrow = "" if a.src == a.dst else f" -> {a.dst}"
            lines.append(f"  [{a.kind}] {a.src}{arrow}  ({a.note})")
    if plan.skipped:
        lines.append("\n## SKIPPED")
        for p, why in plan.skipped:
            lines.append(f"  {p}  ({why})")
    if plan.warnings:
        lines.append("\n## WARNINGS")
        for w in plan.warnings:
            lines.append(f"  {w}")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.tools.migrate_output_layout",
        description="output/ 配下を {作業日}/{バッチHH}/{実行}/ レイアウトへ統一するマイグレーションツール",
    )
    parser.add_argument(
        "--base",
        default="output",
        help="マイグレーション対象のベースディレクトリ (デフォルト: output)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際にはファイルを動かさず、計画だけ表示する",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="計画/実行結果を JSON で出力する",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    base = Path(args.base)
    plan = build_plan(base)

    if args.dry_run:
        if args.json:
            payload = {
                "base": str(base),
                "dry_run": True,
                "actions": [
                    {"kind": a.kind, "src": str(a.src), "dst": str(a.dst), "note": a.note}
                    for a in plan.actions
                ],
                "skipped": [{"path": str(p), "reason": r} for p, r in plan.skipped],
                "warnings": plan.warnings,
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("=== migrate_output_layout DRY-RUN ===")
            print(f"base: {base}")
            print(render_plan(plan))
        return 0

    log = apply_plan(plan)
    if args.json:
        payload = {
            "base": str(base),
            "dry_run": False,
            "log": log,
            "warnings": plan.warnings,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("=== migrate_output_layout APPLY ===")
        print(f"base: {base}")
        for line in log:
            print(line)
        if plan.warnings:
            print("\n## WARNINGS")
            for w in plan.warnings:
                print(f"  {w}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
