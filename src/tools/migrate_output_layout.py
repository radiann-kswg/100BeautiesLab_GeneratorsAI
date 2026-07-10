"""
src/tools/migrate_output_layout.py — output/ 配下を `{作業日}/{実行}/` 2 階層へ統一するマイグレーションツール
Copyright © RadianN_kswg — CC BY-NC 4.0

目標レイアウト (現行: 日付フォルダ + 1 実行フォルダの 2 階層):

    output/
      {YYYYMMDD}/                              ← 作業日
        {YYYYMMDD_HHMMSS}_{provider}_{form}_num{NNN}/  ← 1 実行 = 1 フォルダ
            prompt.txt
            run_meta.json
            notes.md
            *.png / *.jpg ...

> 旧レイアウトの時間帯フォルダ `{YYYYMMDD_HH}/` は廃止済み。本ツールは旧 3 階層
> (`{date}/{date}_{HH}/{run}/`) を含む各種フォーマットを 2 階層へ寄せる。

既存レイアウトの対応パターン:

    1. `output/{date}/{ts}_{provider}_{form}_num{NNN}/` (現行 2 階層・単体キャラ・理想形)
        → 何もしない (skip)
    1b. `output/{date}/{ts}_{provider}_{form}_nums{AAA}_{BBB}/` (現行 2 階層・合同キャラ)
        → 何もしない (skip)
    2. `output/{date}/{date}_{HH}/{ts}_{provider}_{form}_num{NNN}/` (旧 3 階層)
        → `{date}/{run}/` へ引き上げ、空になった `{date}_{HH}/` は削除
    3. `output/{ts}_{provider}_{form}_num{NNN}/` (date 階層なし)
        → `output/{date}/{run}/` 配下へ移動
    4. `output/{date}/{date}_{HH}/{date}_{HH}_{provider}/{file}` (バッチ一括ファイル散在)
        → ファイル名から (form, num) を推測し、
           `{date}/{date}_{HH}0000_{provider}_{form}_num{NNN}/{file}` に集約
    5. `output/{date}/{provider}/{file}` (日時情報なし旧フォーマット)
        → `{date}/{date}_000000_{provider}_{form}_num{NNN}/{file}` に集約

ステージ配下再帰モード (`--flatten-stages`):

    パイプラインは各ステージ (`stage3_rough/` / `stage4_correct/rough_NN_corrected/` /
    `stage5_final/` / `stage5_final/synth/` など) 配下の子生成を
    ``date_group=False`` の *フラット* 形式で置く (`{stage}/{ts}_{provider}_{form}_num{NNN}/`)。
    ところが旧 build_run_output_dir は子生成にも日付フォルダを掘っていたため、古い実行では
    ステージ配下に旧 3 階層 (`{date}/{date}_{HH}/{run}/`) や 2 階層 (`{date}/{run}/`) が
    ネストして残っている。本モードは base 直下の作業日フォルダ *より深い位置* にある
    ``{YYYYMMDD}/`` を再帰的に探し、その配下の run を 1 つ上へ引き上げてフラット化し、
    空になった中間日付フォルダと `.DS_Store` 等の不要ファイルを掃除する。

    6. `.../{stage}/{date}/{date}_{HH}/{run}/`  (旧 3 階層のネスト)
        → `.../{stage}/{run}/`
       `.../{stage}/{date}/{run}/`             (旧 2 階層のネスト)
        → `.../{stage}/{run}/`

    トップレベルの `{作業日}/` (base 直下・相対パス 1 階層) は対象外で温存する。

使い方:

    # 計画だけ確認 (デフォルトで output/)
    python -m src.tools.migrate_output_layout --dry-run

    # 実行 (移動)
    python -m src.tools.migrate_output_layout

    # 任意のベースを指定
    python -m src.tools.migrate_output_layout --base output --dry-run

    # トップレベル整形に加え、ステージ配下のネスト日付フォルダもフラット化する
    python -m src.tools.migrate_output_layout --flatten-stages --dry-run
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
    r"(?P<form>[A-Za-z0-9-]+)_nums?(?P<num>\d{3}(?:_\d{3})*)(?:_(?P<suffix>[A-Za-z0-9-]+))?$"
)
_BATCH_PROVIDER_DIR_RE = re.compile(r"^(\d{8})_(\d{2})_([A-Za-z0-9]+)$")
_PROVIDER_DIR_RE = re.compile(r"^(gemini|openai|anthropic|novelai)$", re.IGNORECASE)

# ファイル名パターン: num057_corefolder_01.png / num057_humanoid_dalle.png / num057_corefolder_flash.png
_IMAGE_FILE_RE = re.compile(
    r"^num(?P<num>\d{3})_(?P<form>corefolder|humanoid)_(?P<tag>[A-Za-z0-9]+)\.(?P<ext>[A-Za-z0-9]+)$"
)

# ステージ配下の掃除で削除してよい OS 由来の不要ファイル
_CRUFT_NAMES = frozenset({".DS_Store", "Thumbs.db"})


def _is_cruft(path: Path) -> bool:
    return path.name in _CRUFT_NAMES

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
    target = base / date / run_dir.name
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

    parent_batch = base / date
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

    parent_batch = base / date
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
                    # 配下を引き上げたあと、空になった旧 {date}_{HH}/ フォルダを削除する
                    plan.actions.append(
                        MoveAction(
                            src=sub,
                            dst=sub,
                            kind="cleanup_empty_dir",
                            note="旧 {date}_{HH}/ 中間フォルダを移動後に削除",
                        )
                    )
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
# ステージ配下再帰フラット化 (--flatten-stages)
# ----------------------------------------------------------------------


def _iter_nested_date_dirs(base: Path) -> Iterable[Path]:
    """base 直下の作業日フォルダ *より深い位置* にある `{YYYYMMDD}/` を列挙する。

    トップレベルの作業日フォルダ (base からの相対パスが 1 階層) は対象外。
    深い順 (パス要素数の多い順) に返し、ネストが入れ子でも内側から処理できるようにする。
    """
    found: list[Path] = []
    for d in base.rglob("*"):
        if not d.is_dir() or not _DATE_RE.match(d.name):
            continue
        if len(d.relative_to(base).parts) <= 1:
            continue  # base 直下の作業日フォルダは温存
        found.append(d)
    found.sort(key=lambda p: len(p.parts), reverse=True)
    return found


def _plan_flatten_leaf(run_dir: Path, dest_parent: Path, plan: MigrationPlan) -> None:
    """ネスト日付フォルダ配下の 1 実行ディレクトリを ``dest_parent`` 直下へ引き上げる。"""
    if _is_cruft(run_dir):
        plan.actions.append(
            MoveAction(src=run_dir, dst=run_dir, kind="remove_cruft", note="OS 由来の不要ファイルを削除")
        )
        return
    if not run_dir.is_dir():
        plan.warnings.append(f"ネスト日付フォルダ配下の予期しないファイル (保留): {run_dir}")
        return
    if _parse_run_dir(run_dir.name) is None:
        plan.warnings.append(f"run dir として解析できないディレクトリ (保留): {run_dir}")
        return
    target = dest_parent / run_dir.name
    try:
        if run_dir.resolve() == target.resolve():
            plan.skipped.append((run_dir, "already flat"))
            return
    except OSError:
        pass
    final_target = _safe_unique(target) if target.exists() else target
    plan.actions.append(
        MoveAction(
            src=run_dir,
            dst=final_target,
            kind="rename_dir",
            note="stage 配下の run をフラット化",
        )
    )


def _plan_flatten_nested_date_dir(date_dir: Path, plan: MigrationPlan) -> None:
    """ステージ配下にネストした `{date}/[{date}_{HH}/]{run}/` をフラット化する。"""
    dest_parent = date_dir.parent  # stage / rough_NN_corrected / synth 等
    hour_dirs: list[Path] = []
    for child in sorted(date_dir.iterdir()):
        if _is_cruft(child):
            plan.actions.append(
                MoveAction(src=child, dst=child, kind="remove_cruft", note="OS 由来の不要ファイルを削除")
            )
            continue
        # `{date}_{HH}/` 時間帯フォルダ: 配下の run を引き上げてから空削除
        m_hh = _DATE_HH_RE.match(child.name) if child.is_dir() else None
        if m_hh and m_hh.group(1) == date_dir.name:
            for run in sorted(child.iterdir()):
                _plan_flatten_leaf(run, dest_parent, plan)
            hour_dirs.append(child)
            continue
        # `{date}/{run}/` 時間帯フォルダなしの run
        if child.is_dir() and _parse_run_dir(child.name):
            _plan_flatten_leaf(child, dest_parent, plan)
            continue
        plan.warnings.append(f"ネスト日付フォルダ配下の分類不能エントリ (保留): {child}")
    # 掃除は「時間帯フォルダ → 日付フォルダ」の順 (内側から空にする)
    for hd in hour_dirs:
        plan.actions.append(
            MoveAction(src=hd, dst=hd, kind="cleanup_empty_dir", note="空の時間帯フォルダを削除")
        )
    plan.actions.append(
        MoveAction(src=date_dir, dst=date_dir, kind="cleanup_empty_dir", note="空のネスト日付フォルダを削除")
    )


def build_stage_flatten_plan(base: Path) -> MigrationPlan:
    """ステージ配下にネストした日付フォルダをフラット化するプランを組み立てる。"""
    plan = MigrationPlan()
    if not base.is_dir():
        plan.warnings.append(f"base が存在しない / ディレクトリでない: {base}")
        return plan
    for date_dir in _iter_nested_date_dirs(base):
        _plan_flatten_nested_date_dir(date_dir, plan)
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
        if action.kind == "remove_cruft":
            try:
                if action.src.exists():
                    action.src.unlink()
                    log.append(f"[remove_cruft] {action.src}")
                else:
                    log.append(f"[remove_cruft] skipped (gone): {action.src}")
            except OSError as exc:
                log.append(f"[remove_cruft] error on {action.src}: {exc}")
            continue
        if action.kind == "move_file":
            action.dst.parent.mkdir(parents=True, exist_ok=True)
            target = _safe_unique(action.dst) if action.dst.exists() else action.dst
            shutil.move(str(action.src), str(target))
            log.append(f"[move_file] {action.src} -> {target}")
            continue
        log.append(f"[skip] 未対応 kind: {action.kind} ({action.src})")

    # 空フォルダ削除は深い順に行い、ネストした中間フォルダを内側から畳む
    deferred_cleanups.sort(key=lambda a: len(a.src.parts), reverse=True)
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
        description="output/ 配下を {作業日}/{実行}/ の 2 階層レイアウトへ統一するマイグレーションツール",
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
        "--flatten-stages",
        action="store_true",
        help="トップレベル整形に加え、パイプラインのステージ配下にネストした日付フォルダをフラット化する",
    )
    parser.add_argument(
        "--stages-only",
        action="store_true",
        help="トップレベル整形を行わず、ステージ配下のフラット化のみ実行する",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="計画/実行結果を JSON で出力する",
    )
    return parser


def _resolve_passes(args: argparse.Namespace) -> list[tuple[str, "callable[[Path], MigrationPlan]"]]:
    """CLI フラグから実行するパス (名前, プランビルダ) の列を決める。

    - デフォルト: トップレベル整形のみ
    - ``--flatten-stages``: トップレベル整形 → ステージフラット化
    - ``--stages-only``: ステージフラット化のみ (トップレベル整形はスキップ)
    """
    if args.stages_only:
        return [("stages", build_stage_flatten_plan)]
    passes: list[tuple[str, "callable[[Path], MigrationPlan]"]] = [("toplevel", build_plan)]
    if args.flatten_stages:
        passes.append(("stages", build_stage_flatten_plan))
    return passes


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    base = Path(args.base)
    passes = _resolve_passes(args)

    if args.dry_run:
        # ドライランは FS を変えないため、各パスを現状の base に対して個別に組み立てる
        results = [(name, builder(base)) for name, builder in passes]
        if args.json:
            payload = {
                "base": str(base),
                "dry_run": True,
                "passes": [
                    {
                        "pass": name,
                        "actions": [
                            {"kind": a.kind, "src": str(a.src), "dst": str(a.dst), "note": a.note}
                            for a in plan.actions
                        ],
                        "skipped": [{"path": str(p), "reason": r} for p, r in plan.skipped],
                        "warnings": plan.warnings,
                    }
                    for name, plan in results
                ],
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("=== migrate_output_layout DRY-RUN ===")
            print(f"base: {base}")
            for name, plan in results:
                print(f"\n### PASS: {name}")
                print(render_plan(plan))
        return 0

    # 適用モードは各パスを順に build→apply する (前パスの移動結果を次パスが参照できる)
    pass_payloads: list[dict] = []
    for name, builder in passes:
        plan = builder(base)
        log = apply_plan(plan)
        pass_payloads.append({"pass": name, "log": log, "warnings": plan.warnings})
        if not args.json:
            print(f"=== migrate_output_layout APPLY [{name}] ===")
            print(f"base: {base}")
            for line in log:
                print(line)
            if plan.warnings:
                print("\n## WARNINGS")
                for w in plan.warnings:
                    print(f"  {w}")
    if args.json:
        print(
            json.dumps(
                {"base": str(base), "dry_run": False, "passes": pass_payloads},
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
