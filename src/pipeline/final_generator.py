"""
pipeline/final_generator.py — Stage 5: マルチ参照合成 + Canva 仕上げ (3 枚固定)
Copyright © RadianN_kswg — CC BY-NC 4.0

Stage 4 修正済みのラフ全枚（最大 5 枚）を Gemini にマルチ参照として渡し、
全案を俯瞰した 3 枚の合成完成画像を生成する。その後 Canva で作風調整する。

  Stage 5a (合成): Gemini に全ラフを同時参照させ 3 枚の統合案を生成
                   → stage5_final/synth/ に保存
  Stage 5b (Canva): 合成画像を Canva でデザイン化・書き出し (3 枚固定)
                   → stage5_final/ に保存
  --skip-canva 指定時は Stage 5b をスキップし合成画像をそのまま最終出力とする
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_FINAL_IMAGE_COUNT = 3  # 完成画像枚数 (固定)


# ──────────────────────────────────────────
# Stage 5a: Gemini マルチ参照合成
# ──────────────────────────────────────────

def _build_synthesis_prompt(base_prompt: str, rough_count: int) -> str:
    """全ラフを俯瞰して完成画像を合成するための指示ヘッダーを base_prompt に付加する。"""
    header = (
        f"[Stage5 合成指示 — 添付 {rough_count} 枚のラフを俯瞰して統合]\n"
        "- 添付した全ラフ案を参照し、各案の優れた点を組み合わせた完成画像を 1 枚生成する\n"
        "- 形態・番号・固有アクセサリなど全案に共通する識別要素を最優先で維持する\n"
        "- 構図・ポーズ・表情は全案の中で最もキャラクターらしいバリエーションを採用する\n"
        "- 作風・線画・塗りのスタイルは先頭の参照画像群（違反なし素案）を最も重視すること\n"
        "- ラフ段階の粗さ・線引き・テキストは最終出力に含めず、完成イラストとして仕上げる\n\n"
    )
    return header + base_prompt


def _synthesize_with_gemini(
    record: dict,
    form: str,
    rough_paths: list[Path],
    base_prompt: str,
    synth_dir: Path,
    work_key: str,
    count: int = _FINAL_IMAGE_COUNT,
) -> list[Path]:
    """Stage 4 全ラフをマルチ参照として Gemini で合成完成画像を生成する。

    rough_paths の全ファイルを extra_ref_locals として渡し、
    「全案俯瞰」の合成プロンプトで count 枚を順次生成する。
    """
    from src.gemini.generate import generate_image

    synth_dir.mkdir(parents=True, exist_ok=True)
    synth_prompt = _build_synthesis_prompt(base_prompt, len(rough_paths))
    extra_locals = [str(p) for p in rough_paths if p.exists()]
    inter_sleep = float(os.environ.get("GEMINI_IMAGE_SLEEP", "6"))

    results: list[Path] = []
    for i in range(count):
        if i > 0:
            print(f"[Stage5-Synth] レートリミット対策: {inter_sleep:.0f}秒待機 ({i + 1}/{count})...")
            time.sleep(inter_sleep)
        print(f"[Stage5-Synth] ({i + 1}/{count}) ラフ {len(extra_locals)} 枚から合成中...")
        try:
            paths = generate_image(
                num=record["data"]["Num"],
                form=form,
                work_key=work_key,
                out_dir=str(synth_dir),
                count=1,
                prompt_override=synth_prompt,
                extra_ref_locals=extra_locals,
            )
            results.extend(paths)
        except SystemExit as err:
            print(f"[WARN] Stage5-Synth ({i + 1}): {err}")
        except Exception as err:
            print(f"[WARN] Stage5-Synth ({i + 1}): {type(err).__name__}: {err}")

    return results


# ──────────────────────────────────────────
# Stage 5b: Canva 書き出し
# ──────────────────────────────────────────

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


# ──────────────────────────────────────────
# メイン関数
# ──────────────────────────────────────────

def generate_final_images(
    record: dict,
    form: str,
    corrected_results: dict[str, list[Path]],
    pipeline_dir: Path,
    work_key: str = "#Works_NumberTales",
    skip_canva: bool = False,
    prompts: dict | None = None,
) -> dict[str, list[Path]]:
    """Stage 4 修正済み画像を全枚俯瞰して合成し、Canva で仕上げた完成画像を 3 枚生成する。

    Parameters
    ----------
    record:            キャラクターレコード
    form:              形態
    corrected_results: Stage 4 の結果 (correct_rough_images の返却値)
    pipeline_dir:      パイプライン出力ルートディレクトリ
    work_key:          作品キー
    skip_canva:        True なら Canva をスキップし合成画像をそのまま最終出力とする
    prompts:           Stage 1 プロンプト dict (base_gemini キーを合成プロンプトに使用)

    Returns
    -------
    {
        "synth": list[Path]  — Gemini 合成完成画像 (stage5_final/synth/)
        "canva": list[Path]  — Canva 書き出し画像 (stage5_final/)
        "all":   list[Path]  — 最終出力 (canva があれば canva, なければ synth)
    }
    """
    stage_dir = pipeline_dir / "stage5_final"
    stage_dir.mkdir(parents=True, exist_ok=True)

    # Stage 4 全出力を収集。
    # passed（違反なし素案）を先頭に置きスタイルアンカーとして重視させる。
    # corrected（i2i 修正済み）は後続に置き、識別要素の補完として使う。
    all_stage4: list[Path] = []
    for p in (corrected_results.get("passed") or []):
        if p.exists() and p not in all_stage4:
            all_stage4.append(p)
    for p in (corrected_results.get("corrected") or []):
        if p.exists() and p not in all_stage4:
            all_stage4.append(p)

    if not all_stage4:
        print("[WARN] Stage5: 入力画像が見つかりません。Stage 5 をスキップします。")
        return {"synth": [], "canva": [], "all": []}

    print(
        f"[Stage5] 仕上げ対象: Stage4 全 {len(all_stage4)} 枚を俯瞰して"
        f" {_FINAL_IMAGE_COUNT} 枚合成"
    )

    # Stage 5a: Gemini マルチ参照合成
    base_prompt = (prompts or {}).get("base_gemini", "")
    synth_dir = stage_dir / "synth"
    synth_images = _synthesize_with_gemini(
        record, form,
        rough_paths=all_stage4,
        base_prompt=base_prompt,
        synth_dir=synth_dir,
        work_key=work_key,
        count=_FINAL_IMAGE_COUNT,
    )

    if not synth_images:
        print(
            "[WARN] Stage5-Synth 失敗。Stage 4 先頭"
            f" {_FINAL_IMAGE_COUNT} 枚をフォールバックとして使用します。"
        )
        synth_images = all_stage4[:_FINAL_IMAGE_COUNT]

    print(f"[Stage5-Synth] done - {len(synth_images)} 枚合成完了")

    if skip_canva:
        print("[INFO] Stage5: --skip-canva のため Canva をスキップします。合成画像を最終出力とします。")
        return {"synth": synth_images, "canva": [], "all": synth_images}

    # Stage 5b: Canva 作風調整
    canva_final: list[Path] = []
    for i, src in enumerate(synth_images, 1):
        paths = _export_canva(record, form, src, stage_dir, work_key, i)
        canva_final.extend(paths)

    all_paths = canva_final if canva_final else synth_images
    print(
        f"[Stage5] done - 合成: {len(synth_images)} 枚 / Canva: {len(canva_final)} 枚"
        f" / 最終: {len(all_paths)} 枚"
    )
    return {
        "synth": synth_images,
        "canva": canva_final,
        "all": all_paths,
    }
