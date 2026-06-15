"""
pipeline/rough_generator.py — Stage 2: Gemini Imagen + Adobe Firefly ラフ画像生成
Copyright © RadianN_kswg — CC BY-NC 4.0

Stage 1 で加工されたプロンプトを使い、2 つのプロバイダで並行してラフ画像を生成する:
  - Gemini Imagen: Gemini 加工プロンプト + DB 参照画像
  - Adobe Firefly: OpenAI 加工プロンプト

ラフ画像はその後 Stage 3 の Gemini i2i / Canva フィニッシングへ渡される。
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _generate_gemini_rough(
    record: dict,
    form: str,
    prompt_override: str,
    stage_dir: Path,
    count: int,
    work_key: str,
) -> list[Path]:
    """Gemini Imagen でラフ画像を生成する。"""
    from src.gemini.generate import generate_image

    try:
        return generate_image(
            num=record["data"]["Num"],
            form=form,
            work_key=work_key,
            out_dir=str(stage_dir),
            count=count,
            prompt_override=prompt_override,
        )
    except SystemExit as err:
        print(f"[WARN] Stage2 Gemini: {err}")
        return []
    except Exception as err:
        print(f"[WARN] Stage2 Gemini 生成に失敗: {type(err).__name__}: {err}")
        return []


def _generate_adobe_rough(
    record: dict,
    form: str,
    prompt_override: str,
    stage_dir: Path,
    count: int,
    work_key: str,
) -> list[Path]:
    """Adobe Firefly でラフ画像を生成する。"""
    from src.adobe.generate import generate_image_firefly

    try:
        return generate_image_firefly(
            num=record["data"]["Num"],
            form=form,
            work_key=work_key,
            out_dir=str(stage_dir),
            count=count,
            prompt_override=prompt_override,
        )
    except SystemExit as err:
        print(f"[WARN] Stage2 Adobe: {err}")
        return []
    except Exception as err:
        print(f"[WARN] Stage2 Adobe 生成に失敗: {type(err).__name__}: {err}")
        return []


def generate_rough_images(
    record: dict,
    form: str,
    prompts: dict,
    pipeline_dir: Path,
    count: int = 1,
    work_key: str = "#Works_NumberTales",
) -> dict[str, list[Path]]:
    """Gemini Imagen + Adobe Firefly の両方でラフ画像を生成する。

    Parameters
    ----------
    record:       キャラクターレコード
    form:         形態 ("corefolder" / "humanoid")
    prompts:      refine_prompt_dual() の返却値。"gemini" / "openai" キーを使用
    pipeline_dir: パイプライン出力ルートディレクトリ
    count:        各プロバイダの生成枚数 (1-4)
    work_key:     作品キー

    Returns
    -------
    {"gemini": list[Path], "adobe": list[Path], "all": list[Path]}
    """
    stage_dir = pipeline_dir / "stage2_rough"
    stage_dir.mkdir(parents=True, exist_ok=True)

    print(f"[Stage2-Gemini] Imagen でラフ生成中 (count={count})...")
    gemini_paths = _generate_gemini_rough(
        record, form,
        prompt_override=prompts.get("gemini", ""),
        stage_dir=stage_dir, count=count, work_key=work_key,
    )

    print(f"[Stage2-Adobe] Firefly でラフ生成中 (count={count})...")
    adobe_paths = _generate_adobe_rough(
        record, form,
        prompt_override=prompts.get("openai", ""),
        stage_dir=stage_dir, count=count, work_key=work_key,
    )

    all_paths = list(gemini_paths) + list(adobe_paths)
    print(
        f"[Stage2] done - Gemini: {len(gemini_paths)} / "
        f"Adobe: {len(adobe_paths)} / total: {len(all_paths)} imgs"
    )
    return {
        "gemini": gemini_paths,
        "adobe": adobe_paths,
        "all": all_paths,
    }
