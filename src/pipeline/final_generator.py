"""
pipeline/final_generator.py — Stage 3: Gemini i2i キャラデザイン寄せ + Canva フィニッシング
Copyright © RadianN_kswg — CC BY-NC 4.0

Stage 2 のラフ画像を起点に本生成を行う 2 ステップ:

  1. Gemini i2i:
     Stage 2 の最良ラフを iterate-from として Gemini に渡し、
     DB 参照画像 + 加工済みプロンプトでキャラクターの原典デザインに寄せる。

  2. Canva フィニッシング:
     Gemini 精錬後の画像（なければ最良ラフ）を Canva Connect API で
     デザイン化・書き出しする。
     ※ Claude アプリの Canva MCP ツール経由でも同等の操作が可能
       (mcp__claude_ai_Canva__generate-design など)。
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _refine_gemini_i2i(
    record: dict,
    form: str,
    rough_path: Path,
    prompt_override: str,
    stage_dir: Path,
    work_key: str,
) -> list[Path]:
    """Gemini i2i でラフ画像をキャラクターデザインに寄せる。"""
    from src.gemini.generate import generate_image

    print(f"[Stage3-Gemini] i2i 精錬中 (起点: {rough_path.name})...")
    try:
        return generate_image(
            num=record["data"]["Num"],
            form=form,
            work_key=work_key,
            out_dir=str(stage_dir),
            count=1,
            iterate_from=str(rough_path),
            prompt_override=prompt_override,
        )
    except SystemExit as err:
        print(f"[WARN] Stage3 Gemini i2i: {err}")
        return []
    except Exception as err:
        print(f"[WARN] Stage3 Gemini i2i に失敗: {type(err).__name__}: {err}")
        return []


def _export_canva(
    record: dict,
    form: str,
    source_image: Path,
    stage_dir: Path,
    work_key: str,
) -> list[Path]:
    """Canva Connect API で画像をデザイン化して書き出す。"""
    from src.canva.generate import export_via_canva

    num = record["data"]["Num"]
    char_name = record["data"].get("Name", f"#{num:03d}")
    print(f"[Stage3-Canva] デザイン化・書き出し中 (入力: {source_image.name})...")
    try:
        return export_via_canva(
            num=num,
            form=form,
            work_key=work_key,
            out_dir=str(stage_dir),
            from_image=str(source_image),
            title=f"NumberTales #{num:03d} {char_name} {form} [pipeline]",
        )
    except SystemExit as err:
        print(f"[WARN] Stage3 Canva: {err}")
        return []
    except Exception as err:
        print(f"[WARN] Stage3 Canva 書き出しに失敗: {type(err).__name__}: {err}")
        return []


def generate_final_images(
    record: dict,
    form: str,
    rough_results: dict[str, list[Path]],
    prompts: dict,
    pipeline_dir: Path,
    work_key: str = "#Works_NumberTales",
    skip_canva: bool = False,
) -> dict[str, list[Path]]:
    """Gemini i2i でラフを精錬し、Canva でフィニッシングする。

    Parameters
    ----------
    record:        キャラクターレコード
    form:          形態
    rough_results: Stage 2 の結果 (generate_rough_images の返却値)
    prompts:       Stage 1 の精錬プロンプト dict (「gemini」キーを使用)
    pipeline_dir:  パイプライン出力ルートディレクトリ
    work_key:      作品キー
    skip_canva:    True なら Canva 書き出しをスキップ

    Returns
    -------
    {"gemini": list[Path], "canva": list[Path], "all": list[Path]}
    """
    stage_dir = pipeline_dir / "stage3_final"
    stage_dir.mkdir(parents=True, exist_ok=True)

    # 起点画像: Gemini ラフ優先、なければ Adobe ラフ
    gemini_roughs = rough_results.get("gemini") or []
    adobe_roughs = rough_results.get("adobe") or []
    best_rough: Path | None = (
        next((p for p in gemini_roughs if p.exists()), None)
        or next((p for p in adobe_roughs if p.exists()), None)
    )

    gemini_final: list[Path] = []
    if best_rough:
        gemini_final = _refine_gemini_i2i(
            record, form,
            rough_path=best_rough,
            prompt_override=prompts.get("gemini", ""),
            stage_dir=stage_dir,
            work_key=work_key,
        )
    else:
        print("[WARN] Stage3: ラフ画像が見つかりません。Gemini i2i をスキップします。")

    # Canva の入力: Gemini 精錬後 > 最良ラフ
    canva_source = (
        next((p for p in gemini_final if p.exists()), None)
        or best_rough
    )
    canva_final: list[Path] = []
    if skip_canva:
        print("[INFO] Stage3: --skip-canva のため Canva をスキップします。")
    elif canva_source and canva_source.exists():
        canva_final = _export_canva(
            record, form,
            source_image=canva_source,
            stage_dir=stage_dir,
            work_key=work_key,
        )
    else:
        print("[WARN] Stage3: Canva の入力画像が見つかりません。Canva をスキップします。")

    all_paths = list(gemini_final) + list(canva_final)
    print(
        f"[Stage3] done - Gemini: {len(gemini_final)} / "
        f"Canva: {len(canva_final)} / total: {len(all_paths)} files"
    )
    return {
        "gemini": gemini_final,
        "canva": canva_final,
        "all": all_paths,
    }
