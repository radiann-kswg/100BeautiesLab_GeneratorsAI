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
    extra_ref_paths: アタリ(SDXL)/Adobe 構図ガイドを Gemini の追加参照
                     (extra_ref_locals) として前方に添付する。個体正確性は
                     プロンプト本文と DB 公式参照画像が担い、アタリは構図/作風の下敷き。
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

    # アタリ/構図ガイドを添付する場合、参照の役割（構図の下敷き／個体はプロンプト・DB優先）を明示する。
    if extra_ref_paths and final_prompt:
        guide_header = (
            "[参照画像の役割 — アタリ（構図・作風の下敷き）]\n"
            "- 添付の参照画像はコアフォルダ形態の構図・レイアウト・作風の方向性を示すアタリです。\n"
            "  シルエット・配置・塗りの雰囲気の下敷きとして参考にしてください。\n"
            "- 個体の色・番号・固有アクセサリなどの識別要素は本プロンプトと（あれば）DB公式参照画像に従い、\n"
            "  アタリ側の配色・崩れ・線の乱れは引き継がないこと。\n\n"
        )
        final_prompt = guide_header + final_prompt

    try:
        paths = generate_image(
            num=record["data"]["Num"],
            form=form,
            work_key=work_key,
            out_dir=str(stage_dir),
            count=count,
            prompt_override=final_prompt,
            iterate_from=iterate_from,
            extra_ref_locals=extra_ref_paths or None,
        )
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


def _generate_sdxl_rough(
    record: dict,
    form: str,
    stage_dir: Path,
    count: int,
    work_key: str,
    scene: str,
) -> list[Path]:
    """SDXL+LoRA (GCE VM SSH バッチ) でコアフォルダのアタリを生成する (B案・アタリ用)。

    出力は Gemini ラフ生成の構図参照 (extra_ref_locals) として使う下敷きで、
    Stage4/5 の補正・合成対象には流さない。失敗しても Gemini ラフのみで続行できるよう、
    例外はここで吸収して空リストを返す。
    """
    from src.sdxl.generate import generate_image as sdxl_generate

    sdxl_dir = stage_dir / "sdxl_guide"
    try:
        return sdxl_generate(
            num=record["data"]["Num"],
            form=form,
            work_key=work_key,
            count=count,
            scene_tags=scene,
            run_dir_override=sdxl_dir,
        )
    except SystemExit as err:
        print(f"[WARN] Stage3 SDXL: {err}")
        return []
    except Exception as err:
        print(f"[WARN] Stage3 SDXL 生成に失敗 (Gemini ラフのみで続行): {type(err).__name__}: {err}")
        return []


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
    rough_provider: str = "gemini",
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
    rough_provider: ラフ生成プロバイダ ("gemini" | "sdxl-guide")。
                    "sdxl-guide" は SDXL でコアフォルダのアタリ(構図/作風の下敷き)を生成し、
                    Gemini ラフの追加参照(extra_ref_locals)として渡す。個体正確性は Gemini+DB が担う。
                    GCE VM 起動を伴う (課金注意・docs/usage-generation.md 参照)。
                    SDXL は i2i 非対応のため、iterate_from 指定時も Gemini 側のみ i2i になる。

    Returns
    -------
    {
        "adobe_guide": list[Path]  — Adobe で作成した構図ガイド画像 (Gemini 参照に添付)
        "gemini":      list[Path]  — Gemini Imagen が生成したラフ画像 (Stage4/5 へ渡る本体)
        "sdxl_guide":  list[Path]  — SDXL が生成したアタリ (Gemini 参照に添付。Stage4/5 には流さない)
        "all":         list[Path]  — 上記すべての統合リスト (空判定/表示用)
    }
    """
    stage_dir = pipeline_dir / "stage3_rough"
    stage_dir.mkdir(parents=True, exist_ok=True)
    use_gemini = rough_provider in ("gemini", "sdxl-guide")
    use_sdxl_guide = rough_provider == "sdxl-guide"

    # Step A: Adobe で構図ガイドを作成 (Gemini 参照に添付する下敷き)
    print(f"[Stage3-Adobe] DB 参照画像から構図ガイドを生成中 (form={form})...")
    adobe_guide_paths = _generate_adobe_composition_guide(
        record, form, stage_dir, scene, background, style, work_key
    )
    if adobe_guide_paths:
        print(f"[Stage3-Adobe] done - {len(adobe_guide_paths)} 枚の構図ガイドを作成")
    else:
        print("[Stage3-Adobe] 構図ガイドなし (参照画像不足 or PIL/Adobe 設定未完)。テキスト生成で続行。")

    # Step B: SDXL+LoRA でコアフォルダのアタリを生成 (Gemini より先に作り、参照として渡す)
    # GCE VM SSH バッチのため課金注意。アタリは 1 枚 (個体正確性は Gemini+DB が担うため下敷きは 1 枚で十分)。
    sdxl_guide_paths: list[Path] = []
    if use_sdxl_guide:
        print("[Stage3-SDXL] コアフォルダのアタリ(構図/作風の下敷き)を生成中 (VM経由)...")
        sdxl_guide_paths = _generate_sdxl_rough(
            record, form,
            stage_dir=stage_dir,
            count=1,
            work_key=work_key,
            scene=scene,
        )

    # Step C: Gemini Imagen でラフ生成 (アタリ + Adobe 構図ガイドを追加参照として添付)
    # base_gemini (形態固定ルール・シーン・尻尾数・識別記号等すべてのブロックを含む) を優先使用する。
    # 短縮版の "gemini" キーは Gemini テキストモデルが 600 token に圧縮した版でシーン等が欠落するため使わない。
    gemini_prompt = prompts.get("base_gemini", "") or prompts.get("gemini", "")
    if scene and "シーン" not in gemini_prompt:
        gemini_prompt = gemini_prompt + f"\n\n[シーン・追加要望]\n- シーン: {scene}"
    # 追加参照は「アタリ(SDXL)を先頭・Adobe 構図ガイドを後続」で最大 2 枚に絞る。
    # extra_ref_locals は ref_limit を 5 に増やすが、DB 公式参照(=個体の正解)の枠を残すため。
    guide_refs = (
        [str(p) for p in sdxl_guide_paths] + [str(p) for p in adobe_guide_paths]
    )[:2]
    gemini_paths: list[Path] = []
    if use_gemini:
        mode_label = "i2i" if iterate_from else "T2I"
        print(
            f"[Stage3-Gemini] Imagen でラフ生成中 "
            f"(count={count}, mode={mode_label}, guide_refs={len(guide_refs)})..."
        )
        gemini_paths = _generate_gemini_rough(
            record, form,
            prompt_override=gemini_prompt,
            stage_dir=stage_dir,
            count=count,
            work_key=work_key,
            iterate_from=iterate_from,
            revisions=revisions,
            extra_ref_paths=guide_refs,
        )

    all_paths = list(adobe_guide_paths) + list(sdxl_guide_paths) + list(gemini_paths)
    print(
        f"[Stage3] done - 構図ガイド: {len(adobe_guide_paths)} / "
        f"SDXL アタリ: {len(sdxl_guide_paths)} / Gemini ラフ: {len(gemini_paths)} / "
        f"total: {len(all_paths)} files"
    )
    return {
        "adobe_guide": adobe_guide_paths,
        "gemini": gemini_paths,
        "sdxl_guide": sdxl_guide_paths,
        "all": all_paths,
    }
