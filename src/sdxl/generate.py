"""
sdxl/generate.py — Illustrious-XL + 作風LoRA ラフ生成 (B案・単体プロバイダ CLI)
Copyright © RadianN_kswg — CC BY-NC 4.0

使用例:
    # dry-run (gcloud コマンドの確認のみ・課金なし)
    python -m src.sdxl.generate --num 57 --form corefolder --dry-run

    # 本番 (VM 起動を伴う。事前に RUN 予定を共有すること)
    python -m src.sdxl.generate --num 57 --form corefolder --count 3 \
        --scene-tags "reading a book, library"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_SDXL_MODEL_LABEL = "illustrious-xl-v0.1 + nt-corefolder-v1 (epoch4)"


def generate_image(
    num: int | str,
    form: str = "corefolder",
    work_key: str = "#Works_NumberTales",
    out_dir: str | None = None,
    count: int = 3,
    scene_tags: str = "",
    extra_tags: "list[str] | None" = None,
    seed: int | None = None,
    keep_vm: bool = False,
    dry_run: bool = False,
    run_dir_override: "Path | None" = None,
) -> list[Path]:
    """SDXL+LoRA でラフ画像を生成する (VM SSH バッチ)。

    run_dir_override: パイプライン (Stage 3) から呼ぶ際に、ステージ配下の
                      実行フォルダを直接指定するためのフック。
    """
    from src.utils import apply_generation_gate, find_character
    from src.utils.paths import build_run_output_dir
    from src.utils.run_log import finalize_run_logs, initialize_run_logs
    from src.sdxl.client import SdxlVmClient
    from src.sdxl.prompt_map import build_sdxl_prompt

    record = find_character(num, work_key)
    if record is None:
        raise SystemExit(f"キャラクター #{num} ({work_key}) が見つかりません。")

    # AI 学習/生成オプトアウト・ゲート（権利軸=中止、充填軸=警告のうえ続行）
    proceed, ai_gate = apply_generation_gate(record, usage="image", num=num, printer=print)
    if not proceed:
        return []

    positive, negative = build_sdxl_prompt(
        record, form, scene_tags=scene_tags, extra_tags=extra_tags
    )

    if run_dir_override is not None:
        run_dir = Path(run_dir_override)
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        run_dir = build_run_output_dir(provider="sdxl", num=num, form=form, base_dir=out_dir)

    initialize_run_logs(
        run_dir,
        provider="sdxl",
        num=num,
        form=form,
        work_key=work_key,
        model=_SDXL_MODEL_LABEL,
        prompt_text=f"{positive}\n\n[negative]\n{negative}",
        meta={
            "backend": "gce-vm-ssh-batch",
            "scene_tags": scene_tags,
            "seed": seed,
            "count": count,
            "dry_run": dry_run,
            "ai_training_gate": ai_gate,
        },
    )

    client = SdxlVmClient(dry_run=dry_run)
    errors: list[str] = []
    images: list[Path] = []
    try:
        images = client.generate(
            prompt=positive,
            negative=negative,
            out_dir=run_dir,
            count=count,
            seed=seed,
            keep_vm=keep_vm,
        )
        status = "success" if images or dry_run else "empty"
    except Exception as err:
        errors.append(f"{type(err).__name__}: {err}")
        status = "failed"
        print(f"[ERROR] sdxl 生成失敗: {err}")

    finalize_run_logs(
        run_dir,
        status=status,
        results=[p.name for p in images],
        errors=errors,
    )
    if status == "failed":
        return []
    return images


def main() -> None:
    parser = argparse.ArgumentParser(description="SDXL+LoRA ラフ生成 (GCE VM SSH バッチ)")
    parser.add_argument("--num", required=True)
    parser.add_argument("--form", default="corefolder", choices=["corefolder", "humanoid"])
    parser.add_argument("--work-key", default="#Works_NumberTales", dest="work_key")
    parser.add_argument("--out", default=None, dest="out_dir")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument(
        "--scene-tags", default="", dest="scene_tags",
        help="シーンのタグ列 (英語推奨。例: 'reading a book, library')",
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--keep-vm", action="store_true", dest="keep_vm",
        help="生成後に VM を停止しない (連続実行時用。課金継続に注意)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="gcloud コマンドの表示のみ (VM 操作・課金なし)",
    )
    args = parser.parse_args()

    images = generate_image(
        num=args.num,
        form=args.form,
        work_key=args.work_key,
        out_dir=args.out_dir,
        count=args.count,
        scene_tags=args.scene_tags,
        seed=args.seed,
        keep_vm=args.keep_vm,
        dry_run=args.dry_run,
    )
    for p in images:
        print(p)


if __name__ == "__main__":
    main()
