"""
pipeline/final_generator.py — Stage 5: Canva 作風調整 + 完成画像生成 (3 枚固定)
Copyright © RadianN_kswg — CC BY-NC 4.0

Stage 4 で修正済みの画像を入力に、Canva で作風調整・仕上げを行い完成画像を生成する。

  - 修正済み画像 (Stage 4 出力) から 3 枚を選び、それぞれ Canva でデザイン化・書き出し (3 枚固定)
  - --skip-canva 指定時は Canva をスキップし、修正済み画像をそのまま最終出力とする
  - 最終出力は stage5_final/ に保存
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_FINAL_IMAGE_COUNT = 3  # Canva で仕上げる完成画像枚数 (固定)


def _export_canva(
    record: dict,
    form: str,
    source_image: Path,
    stage_dir: Path,
    work_key: str,
    index: int,
) -> list[Path]:
    """Canva Connect API で画像をデザイン化して書き出す。"""
    from src.canva.generate import export_via_canva

    num = record["data"]["Num"]
    char_name = record["data"].get("Name", f"#{num:03d}")
    print(f"[Stage5-Canva] ({index}) デザイン化・書き出し中 (入力: {source_image.name})...")
    try:
        return export_via_canva(
            num=num,
            form=form,
            work_key=work_key,
            out_dir=str(stage_dir),
            from_image=str(source_image),
            title=f"NumberTales #{num:03d} {char_name} {form} [pipeline-v{index}]",
        )
    except SystemExit as err:
        print(f"[WARN] Stage5 Canva ({index}): {err}")
        return []
    except Exception as err:
        print(f"[WARN] Stage5 Canva ({index}) 書き出しに失敗: {type(err).__name__}: {err}")
        return []


def generate_final_images(
    record: dict,
    form: str,
    corrected_results: dict[str, list[Path]],
    pipeline_dir: Path,
    work_key: str = "#Works_NumberTales",
    skip_canva: bool = False,
) -> dict[str, list[Path]]:
    """Stage 4 修正済み画像を Canva で仕上げ、完成画像を 3 枚生成する。

    Parameters
    ----------
    record:            キャラクターレコード
    form:              形態
    corrected_results: Stage 4 の結果 (correct_rough_images の返却値)
    pipeline_dir:      パイプライン出力ルートディレクトリ
    work_key:          作品キー
    skip_canva:        True なら Canva をスキップし修正済み画像をそのまま最終出力とする

    Returns
    -------
    {"canva": list[Path], "all": list[Path]}
    """
    stage_dir = pipeline_dir / "stage5_final"
    stage_dir.mkdir(parents=True, exist_ok=True)

    # Stage 4 の全出力から最大 _FINAL_IMAGE_COUNT 枚を選ぶ
    # 修正済み画像を優先し、pass-through 画像で補完
    source_candidates: list[Path] = []
    for p in (corrected_results.get("corrected") or []):
        if p.exists() and p not in source_candidates:
            source_candidates.append(p)
    for p in (corrected_results.get("passed") or []):
        if p.exists() and p not in source_candidates:
            source_candidates.append(p)

    sources = source_candidates[:_FINAL_IMAGE_COUNT]

    if not sources:
        print("[WARN] Stage5: 入力画像が見つかりません。Stage 5 をスキップします。")
        return {"canva": [], "all": []}

    print(f"[Stage5] 仕上げ対象: {len(sources)} 枚 / {_FINAL_IMAGE_COUNT} 枚固定")

    if skip_canva:
        print("[INFO] Stage5: --skip-canva のため Canva をスキップします。修正済み画像を最終出力とします。")
        return {"canva": [], "all": sources}

    canva_final: list[Path] = []
    for i, src in enumerate(sources, 1):
        paths = _export_canva(record, form, src, stage_dir, work_key, i)
        canva_final.extend(paths)

    all_paths = canva_final if canva_final else sources
    print(
        f"[Stage5] done - Canva 書き出し: {len(canva_final)} 枚 / 最終出力: {len(all_paths)} 枚"
    )
    return {
        "canva": canva_final,
        "all": all_paths,
    }
