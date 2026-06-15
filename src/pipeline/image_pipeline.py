"""
pipeline/image_pipeline.py — 画像生成パイプライン オーケストレーター (5 ステージ)
Copyright © RadianN_kswg — CC BY-NC 4.0

ワークフロー:
  Stage 1: コマンド解析 + OpenAI/Gemini でベースプロンプト生成
           (シーン未指定時はキャラクターに合ったシーンをランダム生成)
  Stage 2: キャラクター選定 + 創作 DB から原典画像・特徴を取得
  Stage 3: Gemini Imagen + Adobe 非Firefly でラフ 5 案生成
  Stage 4: OpenAI Vision で違反特徴を分析 + Gemini i2i で修正
  Stage 5: Canva で作風調整・仕上げ → 完成画像 3 枚固定生成

使用方法:
    # キャラクター番号で直接指定 (シーン省略 → ランダム生成)
    python -m src.pipeline.image_pipeline --num 57 --form corefolder

    # シーン指定あり
    python -m src.pipeline.image_pipeline --num 57 --form corefolder \\
        --scene "図書館で本を読んでいるシーン" --skip-canva

    # ★ 自然文で指定 (LLM がキャラクター・シーン等を抽出)
    python -m src.pipeline.image_pipeline \\
        --natural "コアフォルダ姿の25(フィズ)がチョコレートを咥えている絵を生成してほしい"

    # ★ 短編ストーリーファイルから指定
    python -m src.pipeline.image_pipeline --story "_ideas/my_scene.txt"

    # ★ 複数キャラクターを一括生成
    python -m src.pipeline.image_pipeline --nums 25,57 --form corefolder

保存先:
    {OUTPUT_BASE_DIR}/{YYYYMMDD}/{YYYYMMDD_HH}/{ts}_pipeline_{form}_num{NNN}/
      stage1_prompt/        — 生成済みプロンプト (openai/gemini/base)
      stage2_db/            — DB サマリー + キャラクタースペック
      stage3_rough/         — Adobe 構図ガイド + Gemini Imagen ラフ 5 案
      stage4_correct/       — 違反分析ログ + 修正済み画像
      stage5_final/         — Canva 仕上げ完成画像 3 枚
      pipeline_summary.json — 全ステージの実行結果まとめ

必要な環境変数 (.env):
    GEMINI_API_KEY             — Gemini / Imagen 用
    OPENAI_API_KEY             — GPT-4o 用 (Stage1/4)
    FIREFLY_CLIENT_ID          — Adobe IMS 認証用 (Lightroom/Photoshop API)
    FIREFLY_CLIENT_SECRET      — Adobe IMS 認証用
    ADOBE_STORAGE_TYPE         — "local" (PIL fallback, デフォルト) / "dropbox" / "s3"
    CANVA_ACCESS_TOKEN         — Canva フィニッシング用 (--skip-canva で不要)
    GEMINI_TEXT_MODEL          — Gemini テキストモデル (デフォルト: gemini-2.5-flash)
    GPT_MODEL                  — OpenAI テキストモデル (デフォルト: gpt-4o)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import build_run_output_dir  # noqa: E402
from src.pipeline.prompt_refiner import refine_prompt_dual, generate_random_scene  # noqa: E402
from src.pipeline.db_collector import collect_character_data  # noqa: E402
from src.pipeline.rough_generator import generate_rough_images, retry_rough_images  # noqa: E402
from src.pipeline.correction_generator import correct_rough_images  # noqa: E402
from src.pipeline.final_generator import generate_final_images  # noqa: E402

_ROUGH_COUNT = 5  # Stage 3: ラフ生成枚数 (固定)


@dataclass
class PipelineResult:
    num: int
    form: str
    work_key: str
    pipeline_dir: str
    scene_used: str = ""
    stage1_prompts: dict = field(default_factory=dict)
    stage2_summary: dict = field(default_factory=dict)
    stage3_paths: dict[str, list[str]] = field(default_factory=dict)
    stage4_paths: dict[str, list[str]] = field(default_factory=dict)
    stage5_paths: dict[str, list[str]] = field(default_factory=dict)
    status: str = "pending"
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0


def run_image_pipeline(
    num: int,
    form: str = "corefolder",
    work_key: str = "#Works_NumberTales",
    out_dir: str | None = None,
    scene: str = "",
    style: str = "",
    composition: str = "",
    background: str = "",
    skip_canva: bool = False,
    correction_mode: str = "t2i",
) -> PipelineResult:
    """画像生成パイプライン全体 (Stage 1→2→3→4→5) を実行する。

    Parameters
    ----------
    num:             キャラクター番号
    form:            形態 ("corefolder" / "humanoid")
    work_key:        作品キー
    out_dir:         出力ベースディレクトリ (None で環境変数 OUTPUT_BASE_DIR)
    scene:           シーン・ポーズ説明 (空の場合はランダム生成)
    style:           作風ヒント
    composition:     構図ヒント
    background:      背景ヒント
    skip_canva:      True なら Stage 5 の Canva フィニッシングをスキップ
    correction_mode: 重度違反時の対処モード ("t2i" | "stage3")
                     "t2i"    — Stage 4 内で T2I フル再生成 (デフォルト)
                     "stage3" — Stage 3 に差し戻してラフを再生成

    Returns
    -------
    PipelineResult — 全ステージの実行結果
    """
    start_time = datetime.now()

    pipeline_dir = build_run_output_dir(
        provider="pipeline",
        num=num,
        form=form,
        base_dir=out_dir,
        timestamp=start_time,
    )
    print(f"\n[Pipeline] start - #{num:03d} {form} / out: {pipeline_dir}")
    print(f"[Pipeline] skip_canva={skip_canva}")

    result = PipelineResult(
        num=num, form=form, work_key=work_key,
        pipeline_dir=str(pipeline_dir),
    )
    print(f"[Pipeline] correction_mode={correction_mode}")

    # ──────────────────────────────────────
    # Stage 1: コマンド解析 + プロンプト生成
    # ──────────────────────────────────────
    print("\n[=] Stage 1: プロンプト生成 (OpenAI + Gemini)")
    stage1_dir = pipeline_dir / "stage1_prompt"
    stage1_dir.mkdir(parents=True, exist_ok=True)

    # Stage 2 でレコードを取得するが、ランダムシーン生成には先にレコードが必要。
    # 軽量な find_character を先行呼び出しし、Stage 2 で再利用する。
    from src.utils import find_character
    _pre_record = find_character(num, work_key)
    if _pre_record is None:
        result.status = "failed"
        result.errors.append(f"キャラクター #{num} ({work_key}) が見つかりません。")
        _save_summary(pipeline_dir, result, start_time)
        return result

    # シーン未指定 → ランダム生成
    if not scene:
        scene = generate_random_scene(_pre_record, form) or ""
        if scene:
            print(f"[Stage1] シーン: {scene} (自動生成)")

    prompts = refine_prompt_dual(
        _pre_record, form,
        scene=scene, style=style, composition=composition, background=background,
    )
    result.scene_used = scene
    result.stage1_prompts = {
        k: (v if isinstance(v, str) else f"[{len(v)} items]")
        for k, v in prompts.items()
        if k not in ("ref_urls", "ref_locals")
    }
    _save_stage1(stage1_dir, prompts)
    print(
        f"[Stage1] done - OpenAI: {len(prompts['openai'])}chars / "
        f"Gemini: {len(prompts['gemini'])}chars"
    )

    # ──────────────────────────────────────
    # Stage 2: キャラクター選定 + DB データ取得
    # ──────────────────────────────────────
    print("\n[=] Stage 2: キャラクター選定 + 創作 DB データ取得")
    char_data = collect_character_data(num, form, pipeline_dir, work_key)
    if char_data is None:
        result.status = "failed"
        result.errors.append(f"Stage 2: キャラクター #{num} のデータ取得に失敗しました。")
        _save_summary(pipeline_dir, result, start_time)
        return result

    record = char_data["record"]
    char_spec = char_data["spec"]
    result.stage2_summary = {
        "char_name": char_spec.get("char_name", ""),
        "ref_url_count": len(char_data["references"]["urls"]),
        "ref_local_count": len(char_data["references"]["local_paths"]),
        "violation_feature_count": len(char_spec["violation_features"]),
    }

    # ──────────────────────────────────────
    # Stage 3: ラフ 5 案生成 (Adobe + Gemini)
    # ──────────────────────────────────────
    print(f"\n[=] Stage 3: ラフ {_ROUGH_COUNT} 案生成 (Adobe 非Firefly 構図ガイド + Gemini Imagen)")
    rough_results = generate_rough_images(
        record, form, prompts=prompts,
        pipeline_dir=pipeline_dir, count=_ROUGH_COUNT, work_key=work_key,
        scene=scene, background=background, style=style,
    )
    result.stage3_paths = {k: [str(p) for p in v] for k, v in rough_results.items()}

    if not rough_results["gemini"]:
        result.errors.append("Stage 3: Gemini ラフ画像が 1 枚も生成できませんでした。")
        result.status = "partial"
        _save_summary(pipeline_dir, result, start_time)
        return result

    # ──────────────────────────────────────
    # Stage 4: 違反特徴の除去 + 構図修正
    # ──────────────────────────────────────
    print("\n[=] Stage 4: 違反特徴の除去 + 構図修正 (OpenAI Vision + Gemini i2i/T2I)")
    corrected_results = correct_rough_images(
        record, form,
        rough_results=rough_results,
        char_spec=char_spec,
        prompts=prompts,
        pipeline_dir=pipeline_dir,
        work_key=work_key,
        correction_mode=correction_mode,
    )

    # Stage 3 差し戻し処理 (correction_mode == "stage3" の場合)
    needs_regen = corrected_results.get("needs_regen") or []
    if correction_mode == "stage3" and needs_regen:
        print(f"\n[=] Stage 3-Regen: {len(needs_regen)} 枚の差し戻し再生成")
        regen_paths = retry_rough_images(
            record, form,
            prompts=prompts,
            pipeline_dir=pipeline_dir,
            count=len(needs_regen),
            work_key=work_key,
        )
        if regen_paths:
            corrected_results["corrected"].extend(regen_paths)
            corrected_results["all"] = (
                corrected_results["corrected"] + corrected_results["passed"]
            )
            corrected_results["regenerated"] = regen_paths
            result.stage3_paths["regen"] = [str(p) for p in regen_paths]
        else:
            print("[WARN] Stage3-Regen: 再生成失敗。元ラフを pass-through に切り替え。")
            corrected_results["passed"].extend(needs_regen)
            corrected_results["all"] = (
                corrected_results["corrected"] + corrected_results["passed"]
            )

    result.stage4_paths = {
        k: [str(p) for p in v]
        for k, v in corrected_results.items()
        if isinstance(v, list)
    }

    if not corrected_results["all"]:
        result.errors.append("Stage 4: 修正済み画像が 0 枚でした。Stage 5 をスキップします。")
        result.status = "partial"
        _save_summary(pipeline_dir, result, start_time)
        return result

    # ──────────────────────────────────────
    # Stage 5: Canva 作風調整 + 仕上げ (3 枚固定)
    # ──────────────────────────────────────
    print("\n[=] Stage 5: Canva 作風調整 + 完成画像生成 (3 枚固定)")
    final_results = generate_final_images(
        record, form,
        corrected_results=corrected_results,
        pipeline_dir=pipeline_dir,
        work_key=work_key,
        skip_canva=skip_canva,
    )
    result.stage5_paths = {k: [str(p) for p in v] for k, v in final_results.items()}

    result.status = (
        "ok" if final_results["all"]
        else "partial" if corrected_results["all"]
        else "failed"
    )
    _save_summary(pipeline_dir, result, start_time)
    return result


def run_multi_pipeline(
    char_params: list[dict],
    out_dir: str | None = None,
    skip_canva: bool = False,
    correction_mode: str = "t2i",
) -> list[PipelineResult]:
    """複数キャラクターのパイプラインをキャラクターごとに順番に実行する。

    Parameters
    ----------
    char_params:     [{"num":int, "form":str, "scene":str, ...}, ...]
    out_dir:         出力ベースディレクトリ
    skip_canva:      True なら Stage 5 Canva をスキップ
    correction_mode: 重度違反時の対処モード ("t2i" | "stage3")

    Returns
    -------
    各キャラクターの PipelineResult のリスト
    """
    results: list[PipelineResult] = []
    print(f"\n[MultiPipeline] {len(char_params)} キャラクターを順番に生成します")

    for i, cp in enumerate(char_params, 1):
        print(f"\n{'=' * 60}")
        print(f"[MultiPipeline] {i}/{len(char_params)}: #{cp['num']:03d} / {cp['form']}")
        print(f"{'=' * 60}")
        result = run_image_pipeline(
            num=cp["num"],
            form=cp.get("form", "corefolder"),
            work_key=cp.get("work_key", "#Works_NumberTales"),
            out_dir=out_dir,
            scene=cp.get("scene", ""),
            style=cp.get("style", ""),
            composition=cp.get("composition", ""),
            background=cp.get("background", ""),
            skip_canva=skip_canva,
            correction_mode=correction_mode,
        )
        results.append(result)

    ok_count = sum(1 for r in results if r.status == "ok")
    print(f"\n[MultiPipeline] 完了: {ok_count}/{len(results)} 成功")
    return results


# ──────────────────────────────────────────
# 内部ユーティリティ
# ──────────────────────────────────────────

def _save_stage1(stage1_dir: Path, prompts: dict) -> None:
    (stage1_dir / "prompt_openai.txt").write_text(
        prompts.get("openai", ""), encoding="utf-8"
    )
    (stage1_dir / "prompt_gemini.txt").write_text(
        prompts.get("gemini", ""), encoding="utf-8"
    )
    (stage1_dir / "prompt_base_dalle.txt").write_text(
        prompts.get("base_dalle", ""), encoding="utf-8"
    )
    meta = {
        "openai_length": len(prompts.get("openai") or ""),
        "gemini_length": len(prompts.get("gemini") or ""),
        "ref_url_count": len(prompts.get("ref_urls") or []),
        "ref_local_count": len(prompts.get("ref_locals") or []),
    }
    (stage1_dir / "stage1_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _save_summary(
    pipeline_dir: Path,
    result: PipelineResult,
    start_time: datetime,
) -> None:
    elapsed = (datetime.now() - start_time).total_seconds()
    result.elapsed_seconds = round(elapsed, 1)
    (pipeline_dir / "pipeline_summary.json").write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[Pipeline] done - status={result.status} / elapsed: {elapsed:.1f}s")
    print(f"[Pipeline] 出力先: {pipeline_dir}")


# ──────────────────────────────────────────
# CLI エントリポイント
# ──────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "画像生成パイプライン (5 ステージ):\n"
            "  Stage1: コマンド解析 + OpenAI/Gemini でプロンプト生成\n"
            "  Stage2: キャラクター選定 + 創作 DB から原典画像・特徴を取得\n"
            "  Stage3: Adobe 非Firefly 構図ガイド + Gemini Imagen でラフ 5 案生成\n"
            "  Stage4: OpenAI Vision で違反分析 + Gemini i2i で修正\n"
            "  Stage5: Canva で作風調整・仕上げ → 完成画像 3 枚固定生成"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # キャラクター指定 (いずれか)
    char_group = parser.add_mutually_exclusive_group()
    char_group.add_argument(
        "--num", type=int,
        help="キャラクター番号 (例: 57)。シーン未指定時はランダム生成。",
    )
    char_group.add_argument(
        "--nums",
        help="複数キャラクター番号 カンマ区切り (例: 25,57)。各キャラクター個別に処理。",
    )
    char_group.add_argument(
        "--natural",
        metavar="TEXT",
        help=(
            "自然文でリクエスト — LLM がキャラクター・シーン等を抽出する。\n"
            "例: 'コアフォルダ姿の25(フィズ)がチョコレートを咥えている絵'"
        ),
    )
    parser.add_argument(
        "--story",
        metavar="FILE",
        help="短編ストーリーファイル — --natural と同様に LLM がパースする。",
    )

    parser.add_argument(
        "--form", choices=["corefolder", "humanoid"], default="corefolder",
        help="生成する形態 (デフォルト: corefolder)",
    )
    parser.add_argument("--work", default="#Works_NumberTales", help="作品キー")
    parser.add_argument(
        "--out", default=None,
        help="出力ベースディレクトリ (省略時は OUTPUT_BASE_DIR / 'output')",
    )
    parser.add_argument(
        "--scene", default="",
        help="シーン・ポーズ説明。省略すると Stage 1 でキャラクターに合ったシーンを自動生成する。",
    )
    parser.add_argument("--style", default="", help="作風ヒント (例: 'watercolor')")
    parser.add_argument("--composition", default="", help="構図ヒント (例: 'bust shot')")
    parser.add_argument("--background", default="", help="背景ヒント")
    parser.add_argument(
        "--skip-canva", action="store_true",
        help="Stage 5 の Canva フィニッシングをスキップ (CANVA_ACCESS_TOKEN 不要)",
    )
    parser.add_argument(
        "--correction-mode", choices=["t2i", "stage3"], default="t2i",
        dest="correction_mode",
        help=(
            "Stage 4 での重度違反時の対処モード (デフォルト: t2i)\n"
            "  t2i:    Stage 4 内で T2I フル再生成\n"
            "  stage3: Stage 3 に差し戻してラフを再生成"
        ),
    )
    parser.add_argument(
        "--prefer-gemini-parse", action="store_true",
        help="--natural / --story のパース時に Gemini を OpenAI より優先する",
    )
    args = parser.parse_args()

    # ──── 入力モード別キャラクターパラメータの収集 ────

    char_params: list[dict] = []

    if args.natural or args.story:
        from src.pipeline.natural_parser import parse_generation_request

        if args.story:
            story_path = Path(args.story)
            if not story_path.exists():
                sys.exit(f"[ERROR] --story ファイルが見つかりません: {args.story}")
            text = story_path.read_text(encoding="utf-8").strip()
            print(f"[INFO] ストーリーファイル読み込み: {args.story} ({len(text)} 文字)")
        else:
            text = args.natural

        char_params = parse_generation_request(
            text, prefer_gemini=args.prefer_gemini_parse
        )
        if not char_params:
            sys.exit("[ERROR] --natural / --story からキャラクターパラメータを抽出できませんでした。")

        # CLI 追加指定をマージ (CLI 指定が優先)
        for cp in char_params:
            if args.scene and not cp.get("scene"):
                cp["scene"] = args.scene
            if args.style and not cp.get("style"):
                cp["style"] = args.style
            if args.composition and not cp.get("composition"):
                cp["composition"] = args.composition
            if args.background and not cp.get("background"):
                cp["background"] = args.background
            if args.form != "corefolder":
                cp["form"] = args.form

    elif args.nums:
        raw_nums = [s.strip() for s in args.nums.split(",") if s.strip()]
        nums: list[int] = []
        for s in raw_nums:
            try:
                nums.append(int(s))
            except ValueError:
                print(f"[WARN] 番号 '{s}' が無効です。スキップします。")
        if not nums:
            sys.exit("[ERROR] --nums に有効な番号がありません。")
        for n in nums:
            char_params.append({
                "num": n,
                "form": args.form,
                "scene": args.scene,
                "style": args.style,
                "composition": args.composition,
                "background": args.background,
                "work_key": args.work,
            })

    elif args.num:
        char_params.append({
            "num": args.num,
            "form": args.form,
            "scene": args.scene,
            "style": args.style,
            "composition": args.composition,
            "background": args.background,
            "work_key": args.work,
        })

    else:
        parser.error("--num / --nums / --natural / --story のいずれかを指定してください。")

    # ──── パイプライン実行 ────

    if len(char_params) == 1:
        cp = char_params[0]
        result = run_image_pipeline(
            num=cp["num"],
            form=cp.get("form", "corefolder"),
            work_key=cp.get("work_key", args.work),
            out_dir=args.out,
            scene=cp.get("scene", ""),
            style=cp.get("style", ""),
            composition=cp.get("composition", ""),
            background=cp.get("background", ""),
            skip_canva=args.skip_canva,
            correction_mode=args.correction_mode,
        )
        print(f"\n[完了] ステータス: {result.status}")
        if result.scene_used:
            print(f"  シーン: {result.scene_used}")
        if result.errors:
            for err in result.errors:
                print(f"  [ERROR] {err}")
        s5 = result.stage5_paths.get("all") or []
        s4_all = result.stage4_paths.get("all") or []
        s3_rough = result.stage3_paths.get("gemini") or []
        if s5:
            print(f"  完成画像 (Stage5): {len(s5)} 枚")
        if s4_all:
            print(f"  修正済みラフ (Stage4): {len(s4_all)} 枚")
        if s3_rough:
            print(f"  Gemini ラフ (Stage3): {len(s3_rough)} 枚")

    else:
        results = run_multi_pipeline(
            char_params=char_params,
            out_dir=args.out,
            skip_canva=args.skip_canva,
            correction_mode=args.correction_mode,
        )
        for res in results:
            status_mark = "OK" if res.status == "ok" else "NG"
            scene_preview = (res.scene_used[:20] + "...") if len(res.scene_used) > 20 else res.scene_used
            print(f"  [{status_mark}] #{res.num:03d} {res.form}: {res.status} / シーン: {scene_preview}")


if __name__ == "__main__":
    main()
