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

合同 (複数キャラ 1 枚合成) の分割実行:
    state["mode"]=="combined" として、キャラごとの作業領域を 1 つの run-dir に持つ。
    stage3 / stage4 は --num で対象キャラを指定し、stage5 で全員を 1 枚に合成する。

    # Stage1: 合同モードで run-dir/state 作成 (--nums に 2 件以上)
    python -m src.pipeline.stage_cli stage1 --nums 24,42 --form corefolder \
        --scene "寝室でくつろぐシーン"
    # Stage2: 全キャラの DB データ取得 (--num で 1 体に限定も可)
    python -m src.pipeline.stage_cli stage2 --run-dir <dir>
    # Stage3: キャラごとにラフ生成 (--num 必須, --count で枚数)
    python -m src.pipeline.stage_cli stage3 --run-dir <dir> --num 24 --count 1
    python -m src.pipeline.stage_cli stage3 --run-dir <dir> --num 42 --count 1
    # Stage4: キャラごとに違反修正 + 合成用ベスト 1 枚を確定 (--num 必須)
    python -m src.pipeline.stage_cli stage4 --run-dir <dir> --num 24
    python -m src.pipeline.stage_cli stage4 --run-dir <dir> --num 42
    # Stage5: 全キャラのベストを Gemini マルチ参照で 1 枚に合成 (--count で枚数)
    python -m src.pipeline.stage_cli stage5 --run-dir <dir> --count 1
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
from src.pipeline.image_pipeline import (  # noqa: E402
    _save_stage1,
    _build_multi_char_composition_prompt,
    _compose_multi_char,
)

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
# combined (合同) helpers
# ──────────────────────────────────────────

def _is_combined(state: dict) -> bool:
    """state が合同 (複数キャラ 1 枚合成) モードかどうか。"""
    return state.get("mode") == "combined"


def _parse_nums(spec: "str | None") -> list[int]:
    """'24,42' のようなカンマ区切り文字列を [24, 42] に変換する。"""
    if not spec:
        return []
    return [int(x) for x in str(spec).replace(" ", "").split(",") if x != ""]


def _char_key(n: int) -> str:
    """chars 辞書のキー (JSON キーは文字列)。"""
    return str(int(n))


# ──────────────────────────────────────────
# Stage 1: プロンプト生成 + run-dir / state 作成
# ──────────────────────────────────────────

def _stage1_combined(args: argparse.Namespace) -> None:
    """合同 (複数キャラ 1 枚合成) の stage1。

    全キャラ分のプロンプトを生成し、run-dir/state を combined モードで作成する。
    state["chars"][str(num)] にキャラごとの作業領域 (record/prompts/stage3/stage4/best)
    を確保する。以降 stage2-4 は --num でキャラを指定し、stage5 で全員を 1 枚に合成する。
    """
    nums = _parse_nums(args.nums)
    if len(nums) < 2:
        sys.exit("[ERROR] --nums は 2 件以上を指定してください (例: 24,42)。")

    records: list[dict] = []
    for n in nums:
        rec = find_character(n, args.work)
        if rec is None:
            sys.exit(f"[ERROR] キャラクター #{n} ({args.work}) が見つかりません。")
        records.append(rec)

    start = datetime.now()
    run_dir = build_run_output_dir(
        provider="pipeline", num=nums[0], form=args.form,
        base_dir=args.out, timestamp=start, nums=nums,
    )

    scene = args.scene
    if not scene:
        scene = generate_random_scene(records[0], args.form) or ""
        if scene:
            print(f"[Stage1] シーン: {scene} (先頭キャラから自動生成)")

    revisions = None
    if args.revisions:
        revisions = [
            r for r in args.revisions.replace(";", "\n").splitlines() if r.strip()
        ]

    stage1_dir = run_dir / "stage1_prompt"
    chars: dict[str, dict] = {}
    for rec in records:
        n = rec["data"]["Num"]
        prompts = refine_prompt_dual(
            rec, args.form, scene=scene, style=args.style,
            composition=args.composition, background=args.background,
        )
        char_stage1_dir = stage1_dir / f"char_{n:03d}"
        char_stage1_dir.mkdir(parents=True, exist_ok=True)
        _save_stage1(char_stage1_dir, prompts)
        chars[_char_key(n)] = {
            "num": n,
            "record": rec,
            "prompts": prompts,
            "stage3": {"gemini": []},
            "stage4": {"corrected": [], "passed": [], "needs_regen": [],
                       "all": [], "_processed_rough": []},
            "best": [],
        }

    state = {
        "mode": "combined",
        "nums": nums,
        "form": args.form,
        "work_key": args.work,
        "scene": scene,
        "style": args.style,
        "composition": args.composition,
        "background": args.background,
        "skip_canva": True,
        "correction_mode": args.correction_mode,
        "iterate_from": args.iterate_from,
        "revisions": revisions,
        "chars": chars,
        "stage5": {"synth": [], "canva": [], "all": []},
        "stages_done": [],
        "created_at": start.isoformat(timespec="seconds"),
    }
    _mark_done(state, "stage1")
    _save_state(run_dir, state)

    print(f"[Stage1] done (combined) - {len(nums)} キャラ分のプロンプト生成完了 / "
          f"シーン: {scene or '(自動生成失敗)'}")
    print(f"RUN_DIR={run_dir}")


def cmd_stage1(args: argparse.Namespace) -> None:
    if getattr(args, "nums", None):
        return _stage1_combined(args)
    if args.num is None:
        sys.exit("[ERROR] stage1 は --num (単体) か --nums (合同) のいずれかが必要です。")

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

    if _is_combined(state):
        targets = [args.num] if getattr(args, "num", None) else list(state["nums"])
        for n in targets:
            key = _char_key(n)
            if key not in state["chars"]:
                sys.exit(f"[ERROR] Stage2: #{n} は対象キャラ {state['nums']} に含まれません。")
            char_dir = run_dir / f"char_{n:03d}"
            cd = collect_character_data(n, state["form"], char_dir, state["work_key"])
            if cd is None:
                sys.exit(f"[ERROR] Stage2: キャラクター #{n} のデータ取得に失敗。")
            ch = state["chars"][key]
            ch["record"] = cd["record"]
            ch["references"] = cd["references"]
            ch["spec"] = cd["spec"]
            print(f"  [Stage2] #{n:03d} OK - 参照 "
                  f"{len(cd['references']['urls'])}URL / "
                  f"{len(cd['references']['local_paths'])}local / "
                  f"違反チェック {len(cd['spec']['violation_features'])}件")
        _mark_done(state, "stage2")
        _save_state(run_dir, state)
        return

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

    if _is_combined(state):
        n = getattr(args, "num", None)
        if not n:
            sys.exit("[ERROR] Stage3(合同): --num でラフ生成するキャラを指定してください。")
        key = _char_key(n)
        ch = state["chars"].get(key)
        if not ch:
            sys.exit(f"[ERROR] Stage3(合同): #{n} は対象キャラ {state['nums']} に含まれません。")
        if "spec" not in ch:
            sys.exit(f"[ERROR] Stage3(合同): #{n} は先に stage2 を実行してください (spec 未取得)。")

        from src.gemini.generate import generate_image
        rough_dir = run_dir / f"char_{n:03d}" / "stage3_rough"
        rough_dir.mkdir(parents=True, exist_ok=True)
        base_prompt = (ch["prompts"].get("base_gemini", "")
                       or ch["prompts"].get("gemini", ""))
        if state.get("iterate_from") and state.get("revisions"):
            from src.utils.dataset import _build_revision_block
            base_prompt = _build_revision_block(state["revisions"]) + "\n\n" + base_prompt
        try:
            paths = generate_image(
                num=n, form=state["form"], work_key=state["work_key"],
                out_dir=str(rough_dir), count=args.count,
                prompt_override=base_prompt,
                skip_ref_urls=True,
                iterate_from=state.get("iterate_from"),
            )
        except (SystemExit, Exception) as err:  # noqa: BLE001
            paths = []
            print(f"[WARN] Stage3(合同) #{n}: {type(err).__name__}: {err}")

        bucket = ch["stage3"].setdefault("gemini", [])
        for p in _as_strs(paths):
            if p not in bucket:
                bucket.append(p)
        _mark_done(state, "stage3")
        _save_state(run_dir, state)
        print(f"[Stage3] #{n:03d} +{len(paths)}枚 / 累計 gemini {len(bucket)}枚")
        return

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

    if _is_combined(state):
        n = getattr(args, "num", None)
        if not n:
            sys.exit("[ERROR] Stage4(合同): --num で違反修正するキャラを指定してください。")
        key = _char_key(n)
        ch = state["chars"].get(key)
        if not ch or "spec" not in ch:
            sys.exit(f"[ERROR] Stage4(合同): #{n} は先に stage2/stage3 を実行してください。")

        all_rough = ch["stage3"].get("gemini", [])
        if not all_rough:
            sys.exit(f"[ERROR] Stage4(合同): #{n} のラフがありません。先に stage3 を実行してください。")

        s4 = ch["stage4"]
        done_set = set(s4.get("_processed_rough", []))
        pending = [p for p in all_rough if p not in done_set]
        sel = pending[args.offset:]
        if args.limit and args.limit > 0:
            sel = sel[: args.limit]

        if sel:
            corrected = correct_rough_images(
                ch["record"], state["form"],
                rough_results={"gemini": _as_paths(sel)},
                char_spec=ch["spec"],
                prompts=ch["prompts"],
                pipeline_dir=run_dir / f"char_{n:03d}",
                work_key=state["work_key"],
                correction_mode=state.get("correction_mode", "t2i"),
            )
            for k in ("corrected", "passed", "needs_regen"):
                bucket = s4.setdefault(k, [])
                for p in _as_strs(corrected.get(k)):
                    if p not in bucket:
                        bucket.append(p)
            s4["all"] = s4.get("corrected", []) + s4.get("passed", [])
            s4.setdefault("_processed_rough", []).extend(sel)
        else:
            print(f"[Stage4](合同) #{n:03d}: 未処理のラフなし。ベスト選定のみ更新します。")

        # 合成用ベスト 1 枚: 違反なし通過を優先 → 修正済み → 元ラフ先頭
        best = ((s4.get("passed") or [])[:1]
                or (s4.get("corrected") or [])[:1]
                or all_rough[:1])
        ch["best"] = best
        _mark_done(state, "stage4")
        _save_state(run_dir, state)
        best_name = Path(best[0]).name if best else "(none)"
        print(f"[Stage4] #{n:03d} 処理 {len(sel)}枚 / corrected {len(s4['corrected'])} "
              f"passed {len(s4['passed'])} / ベスト → {best_name}")
        return

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

    if _is_combined(state):
        records: list[dict] = []
        bests: list[Path] = []
        missing: list[int] = []
        for n in state["nums"]:
            ch = state["chars"][_char_key(n)]
            records.append(ch["record"])
            b = ch.get("best") or []
            if b:
                bests.append(Path(b[0]))
            else:
                missing.append(n)
        if missing:
            sys.exit(
                f"[ERROR] Stage5(合同): {missing} のベスト未確定。"
                " 先に各キャラの stage3/stage4 を実行してください。"
            )

        composition_prompt = _build_multi_char_composition_prompt(
            records, state["form"], state.get("scene", "")
        )
        synth_dir = run_dir / "stage5_final" / "synth"
        synth = _compose_multi_char(
            records[0], state["form"],
            char_renders=bests,
            composition_prompt=composition_prompt,
            synth_dir=synth_dir,
            work_key=state["work_key"],
            count=args.count,
        )
        s5 = state.setdefault("stage5", {"synth": [], "canva": [], "all": []})
        bucket = s5.setdefault("synth", [])
        for p in _as_strs(synth):
            if p not in bucket:
                bucket.append(p)
        s5["all"] = s5.get("synth", [])
        _mark_done(state, "stage5")
        _save_state(run_dir, state)
        print(f"[Stage5] +{len(synth)}枚 合成 / 累計 完成 {len(s5['all'])}枚 "
              f"(参照: {len(bests)} キャラ)")
        for p in s5["all"]:
            print(f"  FINAL={p}")
        return

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

    if _is_combined(state):
        print(f"run_dir : {run_dir}")
        print(f"mode    : combined / nums={state['nums']} / {state['form']} / "
              f"scene={state.get('scene','')[:40]}")
        print(f"done    : {', '.join(done) or '(none)'}")
        for n in state["nums"]:
            ch = state["chars"][_char_key(n)]
            s4 = ch.get("stage4", {})
            print(f"  #{n:03d} : rough {len(ch.get('stage3',{}).get('gemini',[]))} / "
                  f"s4 corrected {len(s4.get('corrected',[]))} passed {len(s4.get('passed',[]))} "
                  f"/ best {len(ch.get('best',[]))}")
        print(f"stage5  : 合成 {len(state.get('stage5',{}).get('all',[]))}枚")
        return

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
    p1.add_argument("--num", type=int, default=None, help="キャラクター番号 (単体, 例: 57)")
    p1.add_argument("--nums", default=None,
                    help="合同生成: 複数キャラ番号をカンマ区切り (例: 24,42)。2件以上で合同モード")
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
    p2.add_argument("--num", type=int, default=None,
                    help="合同時: 対象キャラを 1 体に限定 (省略時は全キャラ)")
    p2.set_defaults(func=cmd_stage2)

    p3 = sub.add_parser("stage3", help="ラフ生成 (既定 1 枚ずつ追記)")
    _add_run_dir(p3)
    p3.add_argument("--num", type=int, default=None,
                    help="合同時: ラフ生成するキャラ番号 (合同では必須)")
    p3.add_argument("--count", type=int, default=_ROUGH_COUNT_DEFAULT,
                    choices=range(1, 6), help="今回生成する枚数 (1-5, 既定 1)")
    p3.set_defaults(func=cmd_stage3)

    p4 = sub.add_parser("stage4", help="違反修正 (部分処理可)")
    _add_run_dir(p4)
    p4.add_argument("--num", type=int, default=None,
                    help="合同時: 違反修正するキャラ番号 (合同では必須)")
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
