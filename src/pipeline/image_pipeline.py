"""
pipeline/image_pipeline.py — 画像生成パイプライン オーケストレーター
Copyright © RadianN_kswg — CC BY-NC 4.0

Stage 1→2→3 を順番に実行し、各中間成果物をパイプラインディレクトリに保存する。

ワークフロー:
  Stage 1: OpenAI (GPT-4o) + Gemini でプロンプトを加工
  Stage 2: Gemini Imagen + Adobe Firefly でラフ画像を生成
  Stage 3: Gemini i2i でキャラデザイン寄せ → Canva でフィニッシング

使用方法:
    python -m src.pipeline.image_pipeline --num 57 --form corefolder
    python -m src.pipeline.image_pipeline --num 57 --form corefolder \\
        --scene "図書館で本を読んでいるシーン" --count 2 --skip-canva

保存先:
    {OUTPUT_BASE_DIR}/{YYYYMMDD}/{YYYYMMDD_HH}/{ts}_pipeline_{form}_num{NNN}/
      stage1_prompt/          — 加工済みプロンプト (openai/gemini/base)
      stage2_rough/           — Gemini Imagen + Adobe Firefly ラフ画像
      stage3_final/           — Gemini i2i 精錬 + Canva 書き出し
      pipeline_summary.json   — 全ステージの実行結果まとめ

必要な環境変数 (.env):
    GEMINI_API_KEY             — Gemini / Imagen 用
    OPENAI_API_KEY             — GPT-4o 用
    FIREFLY_CLIENT_ID          — Adobe Firefly 用
    FIREFLY_CLIENT_SECRET      — Adobe Firefly 用
    CANVA_ACCESS_TOKEN         — Canva フィニッシング用 (--skip-canva で不要)
    GEMINI_TEXT_MODEL          — Gemini テキストモデル (デフォルト: gemini-2.0-flash-001)
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

from src.utils import build_run_output_dir, find_character  # noqa: E402
from src.pipeline.prompt_refiner import refine_prompt_dual  # noqa: E402
from src.pipeline.rough_generator import generate_rough_images  # noqa: E402
from src.pipeline.final_generator import generate_final_images  # noqa: E402


@dataclass
class PipelineResult:
    num: int
    form: str
    work_key: str
    pipeline_dir: str
    stage1_prompts: dict = field(default_factory=dict)
    stage2_paths: dict[str, list[str]] = field(default_factory=dict)
    stage3_paths: dict[str, list[str]] = field(default_factory=dict)
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
    count: int = 1,
    skip_canva: bool = False,
) -> PipelineResult:
    """画像生成パイプライン全体 (Stage 1→2→3) を実行する。

    Parameters
    ----------
    num:        キャラクター番号
    form:       形態 ("corefolder" / "humanoid")
    work_key:   作品キー
    out_dir:    出力ベースディレクトリ (None で環境変数 OUTPUT_BASE_DIR)
    scene:      シーン・ポーズ説明
    style:      作風ヒント
    composition: 構図ヒント
    background: 背景ヒント
    count:      各プロバイダの生成枚数 (1-4)
    skip_canva: True なら Stage 3 の Canva フィニッシングをスキップ

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
    print(f"\n[Pipeline] start - #{num} {form} / out: {pipeline_dir}")
    print(f"[Pipeline] count={count} skip_canva={skip_canva}")

    result = PipelineResult(
        num=num, form=form, work_key=work_key,
        pipeline_dir=str(pipeline_dir),
    )

    record = find_character(num, work_key)
    if record is None:
        result.status = "failed"
        result.errors.append(f"キャラクター #{num} ({work_key}) が見つかりません。")
        _save_summary(pipeline_dir, result, start_time)
        return result

    char_name = record["data"].get("Name", f"#{num}")
    print(f"[Pipeline] キャラクター: {char_name} / 形態: {form}")

    # Stage 1: プロンプト加工
    print("\n[=] Stage 1: プロンプト加工 (OpenAI + Gemini)")
    stage1_dir = pipeline_dir / "stage1_prompt"
    stage1_dir.mkdir(parents=True, exist_ok=True)

    prompts = refine_prompt_dual(
        record, form,
        scene=scene, style=style, composition=composition, background=background,
    )
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

    # Stage 2: ラフ画像生成
    print("\n[=] Stage 2: ラフ画像生成 (Gemini Imagen + Adobe Firefly)")
    rough_results = generate_rough_images(
        record, form, prompts=prompts,
        pipeline_dir=pipeline_dir, count=count, work_key=work_key,
    )
    result.stage2_paths = {k: [str(p) for p in v] for k, v in rough_results.items()}

    if not rough_results["all"]:
        result.errors.append("Stage 2: ラフ画像が 1 枚も生成できませんでした。")
        result.status = "partial"
        _save_summary(pipeline_dir, result, start_time)
        return result

    # Stage 3: 本生成
    print("\n[=] Stage 3: 本生成 (Gemini i2i + Canva)")
    final_results = generate_final_images(
        record, form,
        rough_results=rough_results,
        prompts=prompts,
        pipeline_dir=pipeline_dir,
        work_key=work_key,
        skip_canva=skip_canva,
    )
    result.stage3_paths = {k: [str(p) for p in v] for k, v in final_results.items()}

    result.status = (
        "ok" if final_results["all"]
        else "partial" if rough_results["all"]
        else "failed"
    )
    _save_summary(pipeline_dir, result, start_time)
    return result


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "画像生成パイプライン (3 ステージ):\n"
            "  Stage1: OpenAI+Gemini でプロンプト加工\n"
            "  Stage2: Gemini Imagen + Adobe Firefly でラフ生成\n"
            "  Stage3: Gemini i2i でデザイン寄せ → Canva でフィニッシング"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--num", type=int, required=True, help="キャラクター番号 (例: 57)")
    parser.add_argument(
        "--form", choices=["corefolder", "humanoid"], default="corefolder",
        help="生成する形態 (デフォルト: corefolder)",
    )
    parser.add_argument("--work", default="#Works_NumberTales", help="作品キー")
    parser.add_argument(
        "--out", default=None,
        help="出力ベースディレクトリ (省略時は OUTPUT_BASE_DIR / 'output')",
    )
    parser.add_argument("--scene", default="", help="シーン・ポーズ説明")
    parser.add_argument("--style", default="", help="作風ヒント (例: 'watercolor')")
    parser.add_argument("--composition", default="", help="構図ヒント (例: 'bust shot')")
    parser.add_argument("--background", default="", help="背景ヒント")
    parser.add_argument(
        "--count", type=int, default=1, choices=range(1, 5),
        help="各プロバイダの生成枚数 1-4 (デフォルト: 1)",
    )
    parser.add_argument(
        "--skip-canva", action="store_true",
        help="Stage 3 の Canva フィニッシングをスキップ (CANVA_ACCESS_TOKEN 不要になる)",
    )
    args = parser.parse_args()

    result = run_image_pipeline(
        num=args.num,
        form=args.form,
        work_key=args.work,
        out_dir=args.out,
        scene=args.scene,
        style=args.style,
        composition=args.composition,
        background=args.background,
        count=args.count,
        skip_canva=args.skip_canva,
    )

    print(f"\n[完了] ステータス: {result.status}")
    if result.errors:
        for err in result.errors:
            print(f"  [ERROR] {err}")

    stage3_all = result.stage3_paths.get("all") or []
    stage2_all = result.stage2_paths.get("all") or []
    if stage3_all:
        print(f"  本生成: {len(stage3_all)} 件")
    if stage2_all:
        print(f"  ラフ生成: {len(stage2_all)} 枚")


if __name__ == "__main__":
    main()
