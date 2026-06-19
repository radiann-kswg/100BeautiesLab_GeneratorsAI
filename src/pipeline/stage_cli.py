"""
pipeline/stage_cli.py — マルチLLMパイプラインを「ステージ／API呼び出し単位」で
分割実行するための CLI エントリポイント
Copyright © RadianN_kswg — CC BY-NC 4.0

目的:
    image_pipeline.py の 5 ステージ (Stage1→5) は 1 プロセスで数分かかるため、
    1 コマンドの実行時間に上限のある実行環境 (例: Cowork サンドボックスの 45 秒)
    では完走できない。本モジュールは各ステージを独立した CLI サブコマンドに分け、
    ステージ間の受け渡しを run-dir 直下の ``pipeline_state.json`` で永続化することで、
    「呼び出し単位の小さな実行」を順に積み上げてフルパイプライン相当を実現する。

    各ステージは前段の状態を JSON から読み、自分の出力を JSON と画像に書き戻す。
    Claude (またはオーケストレータ) は stage1 → stage2 → stage3(×N) → stage4 →
    stage5 の順に本 CLI を呼び出す。

使用例:
    # Stage1: run-dir を新規作成し state とプロンプトを書き出す (run-dir パスを出力)
    python -m src.pipeline.stage_cli stage1 --num 57 --form corefolder \
        --scene "図書館で本を読むシーン"

    # Stage2: キャラクター DB データ取得
    python -m src.pipeline.stage_cli stage2 --run-dir output/20260619/..._num057

    # Stage3: ラフを 1 枚ずつ生成 (繰り返し呼ぶと state に追記される)
    python -m src.pipeline.stage_cli stage3 --run-dir <dir> --count 1

    # Stage4: ラフを違反修正 (--limit/--offset で 1 枚ずつ処理も可)
    python -m src.pipeline.stage_cli stage4 --run-dir <dir> --limit 1 --offset 0

    # Stage5: 合成完成画像 (既定で Canva はスキップ。MCP 側で仕上げる想定)
    python -m src.pipeline.stage_cli stage5 --run-dir <dir>

    # 進捗確認
    python -m src.pipeline.stage_cli status --run-dir <dir>

注意:
    - i2i 改稿は stage1 の --iterate-from / --revisions を指定すると state に載り、
      stage3 で i2i モードになる。
    - 合同 (複数キャラ 1 枚合成) はこの分割 CLI では未対応。単体番号のみ対応。
      合同は image_pipeline.py の --nums を使うこと。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import build_run_output_dir, find_character  # noqa: E402
from src.pipeline.prompt_refiner import (  # noqa: E402
    refine_prompt_dual,
    generate_random_scene,
)
from src.pipeline.db_collector import collect_character_data  # noqa: E402
from src.pipeline.rough_generator import generate_rough_images  # noqa: E402
from src.pipeline.correction_generator import correct_rough_images  # noqa: E402
from src.pipeline.final_generator import generate_final_images  # noqa: E402
from src.pipeline.image_pipeline import _save_stage1  # noqa: E402

_STATE_NAME = "pipeline_state.json"
_ROUGH_COUNT_DEFAULT = 1  # 呼び出し単位: 既定 1 枚 (時間制約環境向け)


# ──────────────────────────────────────────
# state I/O
# ──────────────────────────────────────────

def _state_path(run_dir: Path) -> Path:
    return run_dir / _STATE_NAME


def _load_state(run_dir: Path) -> dict:
    p = _state_path(run_dir)
    if not p.exists():
        sys.exit(f"[ERROR] state が見つかりません: {p}\n  先に stage1 を実行してください。")
    return json.loads(p.read_text(encoding="utf-8"))


def _save_state(run_dir: Path, state: dict) -> None:
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _state_path(run_dir).write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _mark_done(state: dict, stage: str) -> None:
    done = state.setdefault("stages_done", [])
    if stage not in done:
        done.append(stage)


def _as_paths(items: "list[str] | None") -> list[Path]:
    return [Path(p) for p in (items or [])]


def _as_strs(items: "list[Path] | None") -> list[str]:
    return [str(p) for p in (items or [])]


# ──────────────────────────────────────────
# Stage 1: プロンプト生成 + run-dir / state 作成
# ──────────────────────────────────────────

def cmd_stage1(args: argparse.Namespace) -> None:
    record = find_character(args.num, args.work)
    if record is None:
        sys.exit(f"[ERROR] キャラクター #{args.num} ({args.work}) が見つかりません。")

    start = datetime.now()
    run_dir = build_run_output_dir(
        provider="pipeline", num=args.num, form=args.form,
        base_dir=args.out, timestamp=start,
    )
    stage1_dir = run_dir / "stage1_prompt"
    stage1_dir.mkdir(parents=True, exist_ok=True)

    scene = args.scene
    if not scene:
        scene = generate_random_scene(record, args.form) or ""
        if scene:
            print(f"[Stage1] シーン: {scene} (自動生成)")

    prompts = refine_prompt_dual(
        record, args.form,
        scene=scene, style=args.style,
        composition=args.composition, background=args.background,
    )
    _save_stage1(stage1_dir, prompts)

    revisions = None
    if args.revisions:
        revisions = [
            r for r in args.revisions.replace(";", "\n").splitlines() if r.strip()
        ]

    state = {
        "num": args.num,
        "form": args.form,
        "work_key": args.work,
        "scene": scene,
        "style": args.style,
        "composition": args.composition,
        "background": args.background,
        "skip_canva": True,        # 分割運用の既定: Canva は MCP 側で仕上げる
        "correction_mode": args.correction_mode,
        "iterate_from": args.iterate_from,
        "revisions": revisions,
        "prompts": prompts,
        "record": record,          # JSON シリアライズ可能 (DB 由来)
        "stage3": {},
        "stage4": {"corrected": [], "passed": [], "needs_regen": [], "all": []},
        "stage5": {"synth": [], "canva": [], "all": []},
        "stages_done": [],
        "created_at": start.isoformat(timespec="seconds"),
    }
    _mark_done(state, "stage1")
    _save_state(run_dir, state)

    print(f"[Stage1] done - OpenAI {len(prompts['openai'])}chars / "
          f"Gemini {len(prompts['gemini'])}chars")
    # オーケストレータが run-dir を拾えるよう最終行に明示出力
    print(f"RUN_DIR={run_dir}")


# ──────────────────────────────────────────
# Stage 2: キャラクター DB データ取得
# ──────────────────────────────────────────

def cmd_stage2(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    state = _load_state(run_dir)

    char_data = collect_character_data(
        state["num"], state["form"], run_dir, state["work_key"]
    )
    if char_data is None:
        sys.exit(f"[ERROR] Stage2: キャラクター #{state['num']} のデータ取得に失敗。")

    state["record"] = char_data["record"]
    state["references"] = char_data["references"]
    state["spec"] = char_data["spec"]
    _mark_done(state, "stage2")
    _save_state(run_dir, state)

    print(f"[Stage2] done - 参照 {len(char_data['references']['urls'])}URL / "
          f"{len(char_data['references']['local_paths'])}local / "
          f"違反チェック {len(char_data['spec']['violation_features'])}件")


# ──────────────────────────────────────────
# Stage 3: ラフ生成 (呼び出し単位で追記)
# ──────────────────────────────────────────

def cmd_stage3(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    state = _load_state(run_dir)
    if "spec" not in state:
        sys.exit("[ERROR] Stage3: 先に stage2 を実行してください (spec 未取得)。")

    rough = generate_rough_images(
        state["record"], state["form"],
        prompts=state["prompts"],
        pipeline_dir=run_dir,
        count=args.count,
        work_key=state["work_key"],
        scene=state.get("scene", ""),
        background=state.get("background", ""),
        style=state.get("style", ""),
        iterate_from=state.get("iterate_from"),
        revisions=state.get("revisions"),
    )

    s3 = state.setdefault("stage3", {})
    for key, paths in rough.items():
        bucket = s3.setdefault(key, [])
        for p in _as_strs(paths):
            if p not in bucket:
                bucket.append(p)
    _mark_done(state, "stage3")
    _save_state(run_dir, state)

    total = len(s3.get("gemini", []))
    print(f"[Stage3] +{len(rough.get('gemini', []))}枚 / 累計 gemini {total}枚")


# ──────────────────────────────────────────
# Stage 4: 違反修正 (--limit/--offset で部分処理可)
# ──────────────────────────────────────────

def cmd_stage4(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    state = _load_state(run_dir)
    if "spec" not in state:
        sys.exit("[ERROR] Stage4: 先に stage2 を実行してください (spec 未取得)。")

    all_rough = state.get("stage3", {}).get("gemini", [])
    if not all_rough:
        sys.exit("[ERROR] Stage4: ラフ画像がありません。先に stage3 を実行してください。")

    # 既に処理済みのラフを除外し、未処理分から limit/offset で選択
    done_set = set(state["stage4"].get("_processed_rough", []))
    pending = [p for p in all_rough if p not in done_set]
    sel = pending[args.offset:]
    if args.limit and args.limit > 0:
        sel = sel[: args.limit]
    if not sel:
        print("[Stage4] 未処理のラフがありません。スキップします。")
        return

    rough_results = {"gemini": _as_paths(sel)}
    corrected = correct_rough_images(
        state["record"], state["form"],
        rough_results=rough_results,
        char_spec=state["spec"],
        prompts=state["prompts"],
        pipeline_dir=run_dir,
        work_key=state["work_key"],
        correction_mode=state.get("correction_mode", "t2i"),
    )

    s4 = state["stage4"]
    for key in ("corrected", "passed", "needs_regen"):
        bucket = s4.setdefault(key, [])
        for p in _as_strs(corrected.get(key)):
            if p not in bucket:
                bucket.append(p)
    s4["all"] = s4.get("corrected", []) + s4.get("passed", [])
    s4.setdefault("_processed_rough", []).extend(sel)
    _mark_done(state, "stage4")
    _save_state(run_dir, state)

    print(f"[Stage4] 処理 {len(sel)}枚 / 累計 corrected {len(s4['corrected'])} "
          f"passed {len(s4['passed'])} all {len(s4['all'])}")


# ──────────────────────────────────────────
# Stage 5: 合成完成画像 (既定 Canva スキップ)
# ──────────────────────────────────────────

def cmd_stage5(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    state = _load_state(run_dir)

    s4 = state.get("stage4", {})
    if not s4.get("all"):
        sys.exit("[ERROR] Stage5: 修正済み画像がありません。先に stage4 を実行してください。")

    skip_canva = state.get("skip_canva", True)
    if args.with_canva:
        skip_canva = False

    corrected_results = {
        "corrected": _as_paths(s4.get("corrected")),
        "passed": _as_paths(s4.get("passed")),
        "all": _as_paths(s4.get("all")),
    }
    final = generate_final_images(
        state["record"], state["form"],
        corrected_results=corrected_results,
        pipeline_dir=run_dir,
        work_key=state["work_key"],
        skip_canva=skip_canva,
        prompts=state.get("prompts"),
        count=args.count,
    )

    # 呼び出し単位の追記 (1 枚ずつ複数回呼ぶ運用に対応)
    s5 = state.setdefault("stage5", {"synth": [], "canva": [], "all": []})
    for key in ("synth", "canva"):
        bucket = s5.setdefault(key, [])
        for p in _as_strs(final.get(key)):
            if p not in bucket:
                bucket.append(p)
    # all は canva があれば canva、なければ synth を採用
    s5["all"] = s5["canva"] if s5.get("canva") else s5.get("synth", [])
    _mark_done(state, "stage5")
    _save_state(run_dir, state)

    print(f"[Stage5] +{len(final.get('synth') or [])}枚 / 累計 完成 {len(s5['all'])}枚")
    for p in s5["all"]:
        print(f"  FINAL={p}")


# ──────────────────────────────────────────
# status
# ──────────────────────────────────────────

def cmd_status(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    state = _load_state(run_dir)
    done = state.get("stages_done", [])
    print(f"run_dir : {run_dir}")
    print(f"char    : #{state['num']:03d} / {state['form']} / scene={state.get('scene','')[:40]}")
    print(f"done    : {', '.join(done) or '(none)'}")
    print(f"stage3  : gemini {len(state.get('stage3',{}).get('gemini',[]))}枚")
    s4 = state.get("stage4", {})
    print(f"stage4  : corrected {len(s4.get('corrected',[]))} / "
          f"passed {len(s4.get('passed',[]))} / all {len(s4.get('all',[]))}")
    print(f"stage5  : all {len(state.get('stage5',{}).get('all',[]))}枚")


# ──────────────────────────────────────────
# argparse
# ──────────────────────────────────────────

def _add_run_dir(p: argparse.ArgumentParser) -> None:
    p.add_argument("--run-dir", required=True, help="stage1 が作成した run-dir パス")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="マルチLLMパイプラインのステージ分割実行 CLI"
    )
    sub = parser.add_subparsers(dest="stage", required=True)

    p1 = sub.add_parser("stage1", help="プロンプト生成 + run-dir/state 作成")
    p1.add_argument("--num", type=int, required=True, help="キャラクター番号 (例: 57)")
    p1.add_argument("--form", choices=["corefolder", "humanoid"], default="corefolder")
    p1.add_argument("--work", default="#Works_NumberTales", help="作品キー")
    p1.add_argument("--out", default=None, help="出力ベースディレクトリ")
    p1.add_argument("--scene", default="", help="シーン (省略時は自動生成)")
    p1.add_argument("--style", default="", help="作風ヒント")
    p1.add_argument("--composition", default="", help="構図ヒント")
    p1.add_argument("--background", default="", help="背景ヒント")
    p1.add_argument("--correction-mode", choices=["t2i", "stage3"], default="t2i",
                    dest="correction_mode")
    p1.add_argument("--iterate-from", default=None, dest="iterate_from",
                    help="i2i 起点画像/run-dir")
    p1.add_argument("--revisions", default=None, help="i2i 修正指示 (';'/改行区切り)")
    p1.set_defaults(func=cmd_stage1)

    p2 = sub.add_parser("stage2", help="キャラクター DB データ取得")
    _add_run_dir(p2)
    p2.set_defaults(func=cmd_stage2)

    p3 = sub.add_parser("stage3", help="ラフ生成 (既定 1 枚ずつ追記)")
    _add_run_dir(p3)
    p3.add_argument("--count", type=int, default=_ROUGH_COUNT_DEFAULT,
                    choices=range(1, 6), help="今回生成する枚数 (1-5, 既定 1)")
    p3.set_defaults(func=cmd_stage3)

    p4 = sub.add_parser("stage4", help="違反修正 (部分処理可)")
    _add_run_dir(p4)
    p4.add_argument("--limit", type=int, default=0,
                    help="今回処理する枚数上限 (0=未処理全部)")
    p4.add_argument("--offset", type=int, default=0, help="未処理リストの開始位置")
    p4.set_defaults(func=cmd_stage4)

    p5 = sub.add_parser("stage5", help="合成完成画像 (既定 Canva スキップ・1 枚ずつ追記)")
    _add_run_dir(p5)
    p5.add_argument("--count", type=int, default=1,
                    help="kaisuu: synth maisuu (default 1). repeat to append")
    p5.add_argument("--with-canva", action="store_true",
                    help="also run Canva finishing (only where api.canva.com reachable)")
    p5.set_defaults(func=cmd_stage5)

    ps = sub.add_parser("status", help="show progress")
    _add_run_dir(ps)
    ps.set_defaults(func=cmd_status)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
