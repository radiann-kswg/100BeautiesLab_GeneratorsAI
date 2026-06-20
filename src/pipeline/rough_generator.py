"""
pipeline/rough_generator.py — Stage 3: Adobe 構図ガイド + Gemini Imagen 大枠生成
Copyright © RadianN_kswg — CC BY-NC 4.0

Stage 1 で加工されたプロンプトを使い、Gemini Imagen でラフを生成する。

役割分担:
  - Adobe (非 Firefly):
      DB の参照画像を Lightroom/Photoshop API (または PIL) で加工し、
      シーン雰囲気・構図イメージを乗せた「構図ガイド画像」を作る。
      Firefly での生成は行わない。
  - Gemini Imagen:
      Gemini 加工プロンプト + DB 参照画像 + 構図ガイドを入力として
      キャラクターの大枠イラストを生成する。

Stage 3 では Gemini T2I/i2i でラフを生成し、Stage 4 で gpt-image-1 外科的修正を行う。
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
    extra_ref_paths: list[str] | None = None,
    iterate_from: str | None = None,
    revisions: "str | list[str] | None" = None,
) -> list[Path]:
    """Gemini Imagen でラフ画像を生成する。

    iterate_from: 前回生成画像のパス。指定時は i2i モードになり、source が参照先頭に差し込まれる。
    revisions:    修正指示（";"/改行区切り文字列 or list）。iterate_from と組み合わせて使用。
    extra_ref_paths: Adobe が作成した構図ガイドを参照画像の末尾に追加する。
    """
    from src.gemini.generate import generate_image

    # iterate_from がある場合、revision block を Stage 1 プロンプト先頭に差し込む。
    # generate_image() の prompt_override は build_gemini_prompt() の revision 処理を迂回するため、
    # ここで明示的にブロックを構築して先頭に付加する。
    final_prompt = prompt_override
    if iterate_from and revisions:
        from src.utils.iterate import parse_revisions
        from src.utils.dataset import _build_revision_block
        revision_items = (
            parse_revisions(revisions) if isinstance(revisions, str) else list(revisions)
        )
        rev_block = _build_revision_block(revision_items)
        if rev_block and final_prompt:
            final_prompt = rev_block + "\n\n" + final_prompt

    try:
        paths = generate_image(
            num=record["data"]["Num"],
            form=form,
            work_key=work_key,
            out_dir=str(stage_dir),
            count=count,
            prompt_override=final_prompt,
            iterate_from=iterate_from,
        )
        # 生成後、extra_ref_paths を run_meta に記録 (Gemini 側では参照添付が既に行われている)
        return paths
    except SystemExit as err:
        print(f"[WARN] Stage2 Gemini: {err}")
        return []
    except Exception as err:
        print(f"[WARN] Stage2 Gemini 生成に失敗: {type(err).__name__}: {err}")
        return []



def _generate_adobe_composition_guide(
    record: dict,
    form: str,
    stage_dir: Path,
    scene: str,
    background: str,
    style: str,
    work_key: str,
) -> list[Path]:
    """Adobe 非 Firefly API (Lightroom/PIL) で構図ガイドを生成する。"""
    from src.adobe.image_ops import create_composition_guide

    try:
        return create_composition_guide(
            record=record,
            form=form,
            stage_dir=stage_dir,
            scene=scene,
            background=background,
            style=style,
            work_key=work_key,
        )
    except Exception as err:
        print(f"[WARN] Stage2 Adobe 構図ガイド生成に失敗: {type(err).__name__}: {err}")
        return []


def retry_rough_images(
    record: dict,
    form: str,
    prompts: dict,
    pipeline_dir: Path,
    count: int,
    work_key: str = "#Works_NumberTales",
    scene: str = "",
) -> list[Path]:
    """Stage 3 差し戻し: 重度違反ラフの代替を再生成する (stage3_rough/regen/ に保存)。

    i2i なしのフル再生成。correction_mode="stage3" 時に image_pipeline から呼ばれる。
    """
    regen_dir = pipeline_dir / "stage3_rough" / "regen"
    regen_dir.mkdir(parents=True, exist_ok=True)
    print(f"[Stage3-Regen] フル再生成 {count} 枚 → {regen_dir}")
    gemini_prompt = prompts.get("base_gemini", "") or prompts.get("gemini", "")
    if scene and "シーン" not in gemini_prompt:
        gemini_prompt = gemini_prompt + f"\n\n[シーン・追加要望]\n- シーン: {scene}"
    paths = _generate_gemini_rough(
        record, form,
        prompt_override=gemini_prompt,
        stage_dir=regen_dir,
        count=count,
        work_key=work_key,
    )
    print(f"[Stage3-Regen] done - {len(paths)} 枚")
    return paths


def generate_rough_images(
    record: dict,
    form: str,
    prompts: dict,
    pipeline_dir: Path,
    count: int = 1,
    work_key: str = "#Works_NumberTales",
    scene: str = "",
    background: str = "",
    style: str = "",
    iterate_from: str | None = None,
    revisions: "str | list[str] | None" = None,
) -> dict[str, list[Path]]:
    """Adobe 構図ガイド + Gemini Imagen でラフ画像を生成する。

    Parameters
    ----------
    record:       キャラクターレコード
    form:         形態 ("corefolder" / "humanoid")
    prompts:      refine_prompt_dual() の返却値。"base_gemini" キーを優先使用
    pipeline_dir: パイプライン出力ルートディレクトリ
    count:        Gemini の生成枚数 (1-4)
    work_key:     作品キー
    scene:        シーン説明（Adobe 構図ガイドの雰囲気づけに使用）
    background:   背景ヒント（同上）
    style:        作風ヒント（同上）
    iterate_from: 前回生成画像のパス。指定時は i2i モードでラフを生成する。
    revisions:    修正指示（";"/改行区切り文字列 or list）。iterate_from と組み合わせて使用。

    Returns
    -------
    {
        "adobe_guide": list[Path]  — Adobe で作成した構図ガイド画像
        "gemini":      list[Path]  — Gemini Imagen が生成したラフ画像
        "all":         list[Path]  — 上記すべての統合リスト
    }
    """
    stage_dir = pipeline_dir / "stage3_rough"
    stage_dir.mkdir(parents=True, exist_ok=True)

    # Step A: Adobe で構図ガイドを作成
    print(f"[Stage3-Adobe] DB 参照画像から構図ガイドを生成中 (form={form})...")
    adobe_guide_paths = _generate_adobe_composition_guide(
        record, form, stage_dir, scene, background, style, work_key
    )
    if adobe_guide_paths:
        print(f"[Stage3-Adobe] done - {len(adobe_guide_paths)} 枚の構図ガイドを作成")
    else:
        print("[Stage3-Adobe] 構図ガイドなし (参照画像不足 or PIL/Adobe 設定未完)。テキスト生成で続行。")

    # Step B: Gemini Imagen でラフ生成 (構図ガイドを参照に追加)
    # base_gemini (形態固定ルール・シーン・尻尾数・識別記号等すべてのブロックを含む) を優先使用する。
    # 短縮版の "gemini" キーは Gemini テキストモデルが 600 token に圧縮した版でシーン等が欠落するため使わない。
    gemini_prompt = prompts.get("base_gemini", "") or prompts.get("gemini", "")
    if scene and "シーン" not in gemini_prompt:
        gemini_prompt = gemini_prompt + f"\n\n[シーン・追加要望]\n- シーン: {scene}"
    mode_label = "i2i" if iterate_from else "T2I"
    print(f"[Stage3-Gemini] Imagen でラフ生成中 (count={count}, mode={mode_label})...")
    gemini_paths = _generate_gemini_rough(
        record, form,
        prompt_override=gemini_prompt,
        stage_dir=stage_dir,
        count=count,
        work_key=work_key,
        iterate_from=iterate_from,
        revisions=revisions,
        extra_ref_paths=[str(p) for p in adobe_guide_paths],
    )

    all_paths = list(adobe_guide_paths) + list(gemini_paths)
    print(
        f"[Stage3] done - 構図ガイド: {len(adobe_guide_paths)} / "
        f"Gemini ラフ: {len(gemini_paths)} / total: {len(all_paths)} files"
    )
    return {
        "adobe_guide": adobe_guide_paths,
        "gemini": gemini_paths,
        "all": all_paths,
    }
