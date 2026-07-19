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
    {OUTPUT_BASE_DIR}/{YYYYMMDD}/{ts}_pipeline_{form}_num{NNN}/   ← 1 実行 = 1 フォルダ
      stage1_prompt/        — 生成済みプロンプト (openai/gemini/base)
      stage2_db/            — DB サマリー + キャラクタースペック
      stage3_rough/         — Adobe 構図ガイド + Gemini Imagen ラフ 5 案
      stage4_correct/       — 違反分析ログ + 修正済み画像
      stage5_final/         — Canva 仕上げ完成画像 3 枚
      pipeline_summary.json — 全ステージの実行結果まとめ

    各ステージ配下の子生成 (Gemini/Canva) は日付フォルダを作らず
    ``{stageN}/{ts}_{provider}_{form}_num{NNN}/`` のようにフラットに配置される
    (旧レイアウトの {YYYYMMDD}/{YYYYMMDD_HH}/ 再ネストは廃止)。

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
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import build_run_output_dir, extract_char_name  # noqa: E402
from src.pipeline.prompt_refiner import refine_prompt_dual, generate_random_scene  # noqa: E402
from src.pipeline.db_collector import collect_character_data  # noqa: E402
from src.pipeline.rough_generator import generate_rough_images, retry_rough_images  # noqa: E402
from src.pipeline.correction_generator import correct_rough_images  # noqa: E402
from src.pipeline.final_generator import generate_final_images  # noqa: E402

_ROUGH_COUNT = 5               # Stage 3 (単体): ラフ生成枚数
_MULTI_ROUGH_PER_CHAR = 3     # Stage 3 (合同): キャラクターごとのラフ枚数
_STAGE3_COMP_ROUGH_COUNT = 2   # Stage 3 comp rough: 全体構図ラフ枚数（探索フェーズ）
_STAGE5_SYNTH_COUNT = 2        # Stage 5: 最終合成バリアント枚数（仕上げフェーズ）


def _fmt_num(num: int | str | None) -> str:
    """num を 3 桁表示 or そのまま文字列に変換する。

    int/float のみゼロパディングする: 22 → "022"
    str は型を保持する: "2-alt" → "2-alt"  "000" → "000"
    None は "000" フォールバック（プログラムエラー時の安全網）
    """
    if num is None:
        return "000"
    if isinstance(num, float):
        return f"{int(num):03d}"
    if isinstance(num, int):
        return f"{num:03d}"
    # 文字列 Num はそのまま保持。isdigit() 変換は行わない
    return str(num).strip()


@dataclass
class MultiCharPipelineResult:
    """複数キャラクターを1枚に合同生成するパイプラインの結果。"""
    nums: list[int | str]
    forms: list[str]      # キャラ別形態リスト (nums と同順)
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


@dataclass
class PipelineResult:
    num: int | str
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
    num: int | str,
    form: str = "corefolder",
    work_key: str = "#Works_NumberTales",
    out_dir: str | None = None,
    scene: str = "",
    style: str = "",
    composition: str = "",
    background: str = "",
    costume: str = "",
    field_overrides: dict[str, str] | None = None,
    skip_canva: bool = False,
    correction_mode: str = "t2i",
    iterate_from: str | None = None,
    revisions: "str | list[str] | None" = None,
    rough_provider: str = "gemini",
    stage_callback: "Callable[[str, dict, str], None] | None" = None,
) -> PipelineResult:
    """画像生成パイプライン全体 (Stage 1→2→3→4→5) を実行する。

    Parameters
    ----------
    num:             キャラクター番号
    form:            形態 ("corefolder" / "humanoid")
    work_key:        作品キー
    out_dir:         出力ベースディレクトリ (None で環境変数 OUTPUT_BASE_DIR)
    scene:           シーン・ポーズ説明 (空の場合は revisions → ランダム生成の順でフォールバック)
    style:           作風ヒント
    composition:     構図ヒント
    background:      背景ヒント
    costume:         衣装差分の説明 (例: '黒いワンピース姿の差分')。空ならデフォルト衣装。
    field_overrides: RaceType 等の曖昧フィールド（複数候補から1つ選ぶ必要があるもの）の
                     明示上書き指定 (例: {"RaceType": "最終的な設計目標"})。
                     未指定フィールドはシーン文脈をもとに LLM が自動判定する。
    skip_canva:      True なら Stage 5 の Canva フィニッシングをスキップ
    correction_mode: 重度違反時の対処モード ("t2i" | "stage3")
                     "t2i"    — Stage 4 内で T2I フル再生成 (デフォルト)
                     "stage3" — Stage 3 に差し戻してラフを再生成
    iterate_from:    前回生成画像のパス (ファイルまたはrun-dir、またはGCS URL)。
                     指定時は Stage 3 が i2i モードになる。Stage 4/5 は通常通り実行。
    revisions:       修正指示 (";"/改行区切り文字列 or list)。iterate_from と組み合わせて使用。
    rough_provider:  Stage 3 のラフ生成プロバイダ ("gemini" | "sdxl" | "both")。
                     "sdxl"/"both" は GCE VM 起動を伴う (課金注意)。既定は "gemini"。
    stage_callback:  ステージ完了時コールバック: (stage_name, stage_paths_dict, pipeline_dir_str) → None。
                     Stage3/4 完了直後に呼ばれ、GCS 中間アップロードや部分結果保存に利用される。

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
    print(f"\n[Pipeline] start - #{_fmt_num(num)} {form} / out: {pipeline_dir}")
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
    from src.utils import apply_generation_gate, find_character
    _pre_record = find_character(num, work_key)
    if _pre_record is None:
        result.status = "failed"
        result.errors.append(f"キャラクター #{num} ({work_key}) が見つかりません。")
        _save_summary(pipeline_dir, result, start_time)
        return result

    # AI 学習/生成オプトアウト・ゲート（権利軸=skip、充填軸=警告のうえ続行）
    _proceed, _ai_gate = apply_generation_gate(
        _pre_record, usage="image", num=num, printer=print
    )
    if not _proceed:
        result.status = "skipped"
        result.errors.append(f"ai_training opt-out: {_ai_gate['reason']}")
        _save_summary(pipeline_dir, result, start_time)
        return result

    # シーン未指定 → まず revisions (i2i 修正指示) をシーン文脈の代わりに使う。
    # i2i (--iterate-from) はシーン未指定で revisions のみ指定されることが多く、
    # revisions に「完成形態で」等の状態変化指示が書かれていても、シーン未指定のままだと
    # RaceType/Height_cm 等の曖昧フィールド解決に届かないため。
    if not scene and revisions:
        _revisions_text = (
            "; ".join(str(r) for r in revisions if str(r).strip())
            if isinstance(revisions, (list, tuple)) else str(revisions)
        ).strip()
        if _revisions_text:
            scene = _revisions_text
            print(f"[Stage1] シーン: revisions から補完 ({scene[:60]})")

    # それでも未指定 → ランダム生成
    if not scene:
        scene = generate_random_scene(_pre_record, form) or ""
        if scene:
            print(f"[Stage1] シーン: {scene} (自動生成)")

    prompts = refine_prompt_dual(
        _pre_record, form,
        scene=scene, style=style, composition=composition, background=background,
        costume=costume, field_overrides=field_overrides,
    )
    result.scene_used = scene
    result.stage1_prompts = {
        k: (v if isinstance(v, str) else f"[{len(v)} items]")
        for k, v in prompts.items()
        if k not in ("ref_urls", "ref_locals")
    }
    if iterate_from:
        result.stage1_prompts["iterate_from"] = iterate_from
        result.stage1_prompts["revisions"] = (
            revisions if isinstance(revisions, list)
            else [r for r in (revisions or "").replace(";", "\n").splitlines() if r.strip()]
        )
    _save_stage1(stage1_dir, prompts)
    i2i_label = f" [i2i: {iterate_from}]" if iterate_from else ""
    print(
        f"[Stage1] done - OpenAI: {len(prompts['openai'])}chars / "
        f"Gemini: {len(prompts['gemini'])}chars{i2i_label}"
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
    stage3_mode = f"i2i ({iterate_from})" if iterate_from else "T2I"
    print(f"\n[=] Stage 3: ラフ {_ROUGH_COUNT} 案生成 (mode={stage3_mode}, provider={rough_provider})")
    rough_results = generate_rough_images(
        record, form, prompts=prompts,
        pipeline_dir=pipeline_dir, count=_ROUGH_COUNT, work_key=work_key,
        scene=scene, background=background, style=style,
        iterate_from=iterate_from, revisions=revisions,
        rough_provider=rough_provider,
    )
    result.stage3_paths = {k: [str(p) for p in v] for k, v in rough_results.items()}
    if stage_callback:
        try:
            stage_callback("stage3", result.stage3_paths, str(pipeline_dir))
        except Exception as _cb_err:
            print(f"[WARN] stage_callback(stage3) error: {_cb_err}")

    if not rough_results["all"]:
        result.errors.append(
            "Stage 3: ラフ画像が 1 枚も生成できませんでした (Gemini・OpenAI ともに失敗)。"
        )
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
            scene=scene,
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
    if stage_callback:
        try:
            stage_callback("stage4", result.stage4_paths, str(pipeline_dir))
        except Exception as _cb_err:
            print(f"[WARN] stage_callback(stage4) error: {_cb_err}")

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
        prompts=prompts,
    )
    result.stage5_paths = {k: [str(p) for p in v] for k, v in final_results.items()}

    result.status = (
        "ok" if final_results["all"]
        else "partial" if corrected_results["all"]
        else "failed"
    )
    _save_summary(pipeline_dir, result, start_time)
    return result


def _build_multi_char_composition_prompt(
    records: list[dict],
    forms_map: dict[int | str, str],
    scene: str,
    has_comp_rough: bool = False,
) -> str:
    """Stage 3 comp rough / Stage 5 合成用: キャラクター単体レンダーをもとに1枚に合成するプロンプトを生成する。
    skip_db_refs=True と組み合わせて使用し、実際のキャラクターレンダーのみを参照させる。
    forms_map は {キャラ番号: "corefolder" | "humanoid"} のマッピング。
    has_comp_rough=True のとき、参照1 を構図ガイドとして扱い参照2以降をキャラデザインに割り当てる。
    """
    def _char_label(r: dict) -> str:
        d = r.get("data") or {}
        raw_num = d.get("Num")
        return extract_char_name(r, fallback=f"#{_fmt_num(raw_num)}")

    def _get_num_key(r: dict) -> int | str:
        d = r.get("data") or {}
        raw = d.get("Num")
        if isinstance(raw, float):
            return int(raw)
        return raw

    form_rules: list[str] = []
    for r in records:
        n = _get_num_key(r)
        char_form = forms_map.get(n, "corefolder")
        label = _char_label(r)
        if char_form == "humanoid":
            form_rules.append(
                f"- {label}: humanoid 形態（人型シルエット）、腕は2本・手は2つ"
            )
        else:
            form_rules.append(
                f"- {label}: corefolder 形態（球体クッション型シルエット）、人型の腕・手・脚・足を描かない"
            )

    if has_comp_rough:
        # 参照1=構図ガイド、参照2以降=各キャラデザイン という役割分担を明示
        char_list = "\n".join(
            f"- 参照{i + 2}: {_char_label(r)} の完成イラスト（キャラクターデザインの正解）"
            for i, r in enumerate(records)
        )
        lines = [
            "[Stage 5 合成 — 構図ラフを採用してキャラクターデザインを反映した完成画像を生成]",
            "添付の参照画像を使い、1 枚の完成イラストを生成してください。",
            "",
            "[参照画像の役割と優先度]",
            "- 参照1 (構図ガイド): 全キャラクターの空間配置・サイズ比・ポーズ関係・画角のガイド。",
            "  この画像の構図・レイアウトを最優先で採用してください。",
            char_list,
            "",
            "[合成指示]",
            "- 参照1の構図（各キャラの位置・サイズ比・ポーズ・画角）を忠実に維持する",
            "- 各キャラクターの外見・色・識別要素は参照2以降のデザインに忠実に描く",
            "- 全員が画面内に完全に収まること（頭・胴・下半身のいずれもフレームアウト禁止）",
            "- 作風・線画・塗りスタイルは全参照画像に揃えること",
        ]
    else:
        char_list = "\n".join(
            f"- 参照{i + 1}: {_char_label(r)} の完成イラスト"
            for i, r in enumerate(records)
        )
        lines = [
            "[マルチキャラクター合成 — 添付レンダーをもとに全員を 1 枚に]",
            "添付の参照画像（各キャラクターの完成イラスト）を参考に、",
            "全員が同じシーンに自然に配置された 1 枚の画像を生成してください。",
            "",
            "[添付参照画像の内訳]",
            char_list,
            "",
            "[合成指示]",
            "- 全員を 1 枚の構図に自然に収める（全員が画面内に完全に収まること）",
            "- 各キャラクターの形態・番号・識別要素を添付参照に忠実に維持する",
            "- 作風・線画・塗りスタイルは添付参照画像に揃えること",
        ]

    lines += [
        "",
        "[キャラクター別形態ルール]",
        *form_rules,
        "",
        "[共通作風]",
        "Cute, Deformed, Chibi, Thick lines, Pastel colors, Cel shading, Simple background",
        "",
    ]
    if scene:
        lines += [f"[シーン]", f"- {scene}", ""]
    lines.append(
        "[絶対禁止] 画像内に文字・テキスト・ラベルを一切描かないこと。"
        " Do NOT render any text, words, labels, or signs in the image."
    )
    return "\n".join(lines)


def _compose_multi_char(
    base_record: dict,
    form: str,
    char_renders: list[Path],
    composition_prompt: str,
    synth_dir: Path,
    work_key: str,
    count: int = 3,
) -> list[Path]:
    """Stage 5: 各キャラクターの単体完成レンダーを Gemini マルチ参照で 1 枚に合成する。

    skip_db_refs=True でDB参照を除外し、char_renders のみを参照させることで
    スタイルのブレを防ぐ。
    """
    from src.gemini.generate import generate_image

    synth_dir.mkdir(parents=True, exist_ok=True)
    render_strs = [str(p) for p in char_renders if p.exists()]
    inter_sleep = float(os.environ.get("GEMINI_IMAGE_SLEEP", "6"))

    results: list[Path] = []
    for i in range(count):
        if i > 0:
            print(f"[Stage5-Compose] レートリミット対策: {inter_sleep:.0f}秒待機 ({i + 1}/{count})...")
            time.sleep(inter_sleep)
        print(f"[Stage5-Compose] ({i + 1}/{count}) キャラクターレンダー {len(render_strs)} 枚から合成中...")
        try:
            paths = generate_image(
                num=base_record["data"]["Num"],
                form=form,
                work_key=work_key,
                out_dir=str(synth_dir),
                count=1,
                prompt_override=composition_prompt,
                extra_ref_locals=render_strs,
                skip_db_refs=True,  # キャラレンダーが参照なので DB 画像は不要
            )
            results.extend(paths)
        except SystemExit as err:
            print(f"[WARN] Stage5-Compose ({i + 1}): {err}")
        except Exception as err:
            print(f"[WARN] Stage5-Compose ({i + 1}): {type(err).__name__}: {err}")
    return results


def run_combined_pipeline(
    nums: list[int | str],
    form: str = "corefolder",
    forms: "list[str] | None" = None,
    work_key: str = "#Works_NumberTales",
    out_dir: str | None = None,
    scene: str = "",
    style: str = "",
    composition: str = "",
    background: str = "",
    costume: str = "",
    field_overrides: dict[str, str] | None = None,
    skip_canva: bool = False,
    correction_mode: str = "t2i",
    iterate_from: str | None = None,
    revisions: "str | list[str] | None" = None,
    stage_callback: "Callable[[str, dict, str], None] | None" = None,
) -> MultiCharPipelineResult:
    """複数キャラクターを 1 枚に合同生成するパイプライン (Stage 1→2→3→4→5)。

    Stage 3-4 はキャラクターごとに個別生成・違反修正を行い、
    Stage 5 で各キャラクターの完成レンダーを Gemini マルチ参照で 1 枚に合成する。

    Parameters
    ----------
    nums:            キャラクター番号リスト (2 件以上)
    form:            全キャラ共通の形態 (forms 未指定時のフォールバック)
    forms:           キャラ別形態リスト (nums と同順)。指定時は form より優先。
                     長さが nums より短い場合は末尾を form で補完する。
                     例: nums=[X, 20], forms=["corefolder", "humanoid"] で
                     Xをコアフォルダ・ハツカをヒューマノイドにして1枚合成できる。
    work_key:        作品キー
    out_dir:         出力ベースディレクトリ
    scene:           シーン (空の場合は先頭キャラから自動生成)
    skip_canva:      True なら Stage 5 Canva をスキップ
    correction_mode: Stage 4 重度違反時の対処モード ("t2i" | "stage3")

    出力ディレクトリ構成
    --------------------
    pipeline_dir/
      stage1_prompt/           — 統合プロンプト
      char_NNN/stage3_rough/   — キャラクターごとのラフ (各 _MULTI_ROUGH_PER_CHAR 枚)
      char_NNN/stage2_db/      — キャラクターごとの DB サマリー
      char_NNN/stage4_correct/ — キャラクターごとの違反修正結果
      stage3_comp_rough/       — 全キャラ構図ラフ (Stage3 と同時に _STAGE3_COMP_ROUGH_COUNT 枚, 探索)
      stage5_final/            — 全キャラ合成完成画像 _STAGE5_SYNTH_COUNT 枚 (仕上げ)

    Returns
    -------
    MultiCharPipelineResult
    """
    from src.utils import apply_generation_gate, find_character
    from src.gemini.generate import generate_image

    # キャラ別形態マップを構築する。forms が指定されていればそれを優先し、
    # 不足分は form で補完する。
    _resolved_forms: list[str] = []
    for i in range(len(nums)):
        if forms and i < len(forms):
            _resolved_forms.append(str(forms[i]).strip().lower() or form)
        else:
            _resolved_forms.append(form)
    forms_map: dict[int | str, str] = {n: _resolved_forms[i] for i, n in enumerate(nums)}

    start_time = datetime.now()
    primary_form = _resolved_forms[0]
    pipeline_dir = build_run_output_dir(
        provider="pipeline",
        num=nums[0],
        form=primary_form,
        base_dir=out_dir,
        timestamp=start_time,
        nums=nums,
    )
    nums_label = "+".join(f"#{_fmt_num(n)}" for n in nums)
    forms_label = "+".join(_resolved_forms)
    print(f"\n[CombinedPipeline] start - {nums_label} ({forms_label}) → 1 枚合同生成 / out: {pipeline_dir}")
    print(f"[CombinedPipeline] skip_canva={skip_canva} / correction_mode={correction_mode}")

    result = MultiCharPipelineResult(
        nums=nums, forms=_resolved_forms, work_key=work_key,
        pipeline_dir=str(pipeline_dir),
    )

    # ── Stage 2: 全キャラクターのレコード + スペック収集 ──
    print(f"\n[=] Stage 2: {len(nums)} キャラクターのレコード + DB データ収集")
    records: list[dict] = []
    char_data_map: dict[int | str, dict] = {}
    for n in nums:
        rec = find_character(n, work_key)
        if rec is None:
            result.status = "failed"
            result.errors.append(f"キャラクター #{n} ({work_key}) が見つかりません。")
            _save_summary(pipeline_dir, result, start_time)
            return result
        # AI 学習/生成オプトアウト・ゲート。合同絵は部分生成できないため、
        # 1 人でも権利軸オプトアウトなら合同全体を中止。充填軸は警告のうえ続行。
        _proceed, _ai_gate = apply_generation_gate(rec, usage="image", num=n, printer=print)
        if not _proceed:
            result.status = "skipped"
            result.errors.append(f"ai_training opt-out (#{_fmt_num(n)}): {_ai_gate['reason']}")
            _save_summary(pipeline_dir, result, start_time)
            return result
        records.append(rec)
        char_dir = pipeline_dir / f"char_{_fmt_num(n)}"
        char_data = collect_character_data(n, forms_map[n], char_dir, work_key)
        if char_data is None:
            result.status = "failed"
            result.errors.append(f"Stage 2: #{n} DB データ取得に失敗しました。")
            _save_summary(pipeline_dir, result, start_time)
            return result
        char_data_map[n] = char_data
        print(f"  [Stage2] #{_fmt_num(n)} {extract_char_name(rec, fallback='')} ({forms_map[n]}) — OK")

    result.stage2_summary = {
        "char_names": [extract_char_name(r, fallback="") for r in records],
        "num_chars": len(records),
    }

    # ── Stage 1: シーン補完 + キャラクターごとのプロンプト生成 ──
    print("\n[=] Stage 1: シーン補完 + キャラクターごとのプロンプト生成")
    if not scene and revisions:
        _revisions_text = (
            "; ".join(str(r) for r in revisions if str(r).strip())
            if isinstance(revisions, (list, tuple)) else str(revisions)
        ).strip()
        if _revisions_text:
            scene = _revisions_text
            print(f"[Stage1] シーン: revisions から補完 ({scene[:60]})")
    if not scene:
        scene = generate_random_scene(records[0], forms_map[nums[0]]) or ""
        if scene:
            print(f"[Stage1] シーン: {scene} (先頭キャラから自動生成)")

    per_char_prompts: dict[int, dict] = {}
    for rec in records:
        n = rec["data"]["Num"]
        prompts = refine_prompt_dual(
            rec, forms_map[n], scene=scene, style=style,
            composition=composition, background=background,
            costume=costume, field_overrides=field_overrides,
        )
        per_char_prompts[n] = prompts

    result.scene_used = scene
    result.stage1_prompts = {
        "scene": scene,
        "char_count": len(records),
        "char_names": [extract_char_name(r, fallback="") for r in records],
    }
    if iterate_from:
        result.stage1_prompts["iterate_from"] = iterate_from
        result.stage1_prompts["revisions"] = (
            revisions if isinstance(revisions, list)
            else [r for r in (revisions or "").replace(";", "\n").splitlines() if r.strip()]
        )
    stage1_dir = pipeline_dir / "stage1_prompt"
    stage1_dir.mkdir(parents=True, exist_ok=True)
    for rec in records:
        n = rec["data"]["Num"]
        char_stage1_dir = stage1_dir / f"char_{_fmt_num(n)}"
        char_stage1_dir.mkdir(parents=True, exist_ok=True)
        _save_stage1(char_stage1_dir, per_char_prompts[n])
    print(f"[Stage1] done - {len(records)} キャラクター分のプロンプト生成完了")

    # ── Stage 3: キャラクターごとに個別ラフ生成 (_MULTI_ROUGH_PER_CHAR 枚) ──
    stage3_mode = f"i2i ({iterate_from})" if iterate_from else "T2I"
    print(
        f"\n[=] Stage 3: キャラクターごとに個別ラフ生成"
        f" ({_MULTI_ROUGH_PER_CHAR} 枚/キャラ, 計 {len(nums) * _MULTI_ROUGH_PER_CHAR} 枚"
        f", mode={stage3_mode})"
    )
    # revision block は per-char の base_prompt 先頭に共通で差し込む
    _rev_block: str = ""
    if iterate_from and revisions:
        from src.utils.iterate import parse_revisions
        from src.utils.dataset import _build_revision_block
        _rev_items = (
            parse_revisions(revisions) if isinstance(revisions, str) else list(revisions)
        )
        _rev_block = _build_revision_block(_rev_items)

    per_char_roughs: dict[int | str, list[Path]] = {}
    inter_char_sleep = float(os.environ.get("GEMINI_INTER_CHAR_SLEEP", "30"))

    for i, rec in enumerate(records):
        n = rec["data"]["Num"]
        if isinstance(n, float):
            n = int(n)
        if i > 0:
            # 直前キャラクターの生成直後にスタートするとレートリミットで失敗するため待機する
            print(f"  [Stage3] キャラクター切り替え待機: {inter_char_sleep:.0f}秒...")
            time.sleep(inter_char_sleep)

        rough_dir = pipeline_dir / f"char_{_fmt_num(n)}" / "stage3_rough"
        rough_dir.mkdir(parents=True, exist_ok=True)
        base_prompt = (per_char_prompts[n].get("base_gemini", "")
                       or per_char_prompts[n].get("gemini", ""))
        if _rev_block and base_prompt:
            base_prompt = _rev_block + "\n\n" + base_prompt
        char_form = forms_map[n]
        print(f"  [Stage3] #{_fmt_num(n)} ({char_form}) ラフ {_MULTI_ROUGH_PER_CHAR} 枚生成中...")
        try:
            paths = generate_image(
                num=n, form=char_form, work_key=work_key,
                out_dir=str(rough_dir),
                count=_MULTI_ROUGH_PER_CHAR,
                prompt_override=base_prompt,
                skip_ref_urls=True,  # DB URL を Gemini サーバーが取得できないケースを回避
                iterate_from=iterate_from,  # 指定時は前回合成画像を参照先頭に差し込む
            )
        except (SystemExit, Exception) as err:
            paths = []
            result.errors.append(f"Stage 3 char#{n}: {err}")
        per_char_roughs[n] = paths
        if not paths:
            result.errors.append(
                f"Stage 3 char#{n}: ラフ 0 枚 — API エラーまたはレートリミットの可能性"
            )
        print(f"  [Stage3] #{_fmt_num(n)} — {len(paths)} 枚生成完了")

    all_stage3 = [p for paths in per_char_roughs.values() for p in paths]
    result.stage3_paths = {
        f"char_{_fmt_num(n)}": [str(p) for p in per_char_roughs.get(n, [])] for n in nums
    }
    result.stage3_paths["all"] = [str(p) for p in all_stage3]
    print(f"[Stage3] done - 合計 {len(all_stage3)} 枚")

    # ── Stage 3 終了時コールバック（comp rough が確定する前の中間通知） ──
    if stage_callback and all_stage3:
        try:
            stage_callback("stage3", result.stage3_paths, str(pipeline_dir))
        except Exception as _cb_err:
            print(f"[WARN] stage_callback(stage3) error: {_cb_err}")

    # ── Stage 3 続き: 全キャラクターが揃う構図ラフを 1 枚同時生成 ──
    # 単体ラフとは別に全員が同じシーンに収まる構図を先行確認するためのラフ。
    # Stage 5 最終合成の前段として i2i の起点にも使える。
    # 全員の単体ラフが 1 枚以上揃っている場合のみ実行する。
    comp_rough_paths: list[Path] = []
    all_have_rough = all(bool(per_char_roughs.get(n)) for n in nums)
    if all_have_rough:
        print(f"\n  [Stage3-CompRough] 全キャラ構図ラフを同時生成 ({_STAGE3_COMP_ROUGH_COUNT} 枚, 探索)...")
        time.sleep(inter_char_sleep)  # レートリミット対策
        comp_rough_dir = pipeline_dir / "stage3_comp_rough"
        comp_rough_dir.mkdir(parents=True, exist_ok=True)
        comp_ref_images = [per_char_roughs[n][0] for n in nums]
        comp_rough_prompt = _build_multi_char_composition_prompt(records, forms_map, scene)
        try:
            comp_rough_paths = _compose_multi_char(
                records[0], primary_form,
                char_renders=comp_ref_images,
                composition_prompt=comp_rough_prompt,
                synth_dir=comp_rough_dir,
                work_key=work_key,
                count=_STAGE3_COMP_ROUGH_COUNT,
            )
            print(f"  [Stage3-CompRough] {len(comp_rough_paths)} 枚生成完了")
        except Exception as err:
            print(f"  [WARN] Stage3-CompRough: {type(err).__name__}: {err}")
    else:
        print(f"\n  [Stage3-CompRough] 一部キャラのラフが未生成のためスキップ")
    result.stage3_paths["composition_rough"] = [str(p) for p in comp_rough_paths]

    # マルチキャラ合成には全キャラのラフが必要。1 人でも欠けたら中断する。
    failed_chars = [n for n in nums if not per_char_roughs.get(n)]
    if failed_chars:
        failed_label = " / ".join(f"#{_fmt_num(n)}" for n in failed_chars)
        result.errors.append(
            f"Stage 3: {failed_label} のラフ生成に失敗しました。"
            " 全キャラクターのラフが揃わないと合同合成ができません。"
        )
        result.status = "partial"
        _save_summary(pipeline_dir, result, start_time)
        return result

    # ── Stage 4: キャラクターごとに個別違反修正 ──
    print(f"\n[=] Stage 4: キャラクターごとに違反修正 (OpenAI Vision + Gemini i2i/T2I)")
    per_char_best: list[Path] = []  # Stage 5 に渡す各キャラのベスト 1 枚
    all_stage4_paths: dict[str, list[str]] = {}

    for rec in records:
        n = rec["data"]["Num"]
        if isinstance(n, float):
            n = int(n)
        rough_paths = per_char_roughs.get(n) or []
        if not rough_paths:
            print(f"  [Stage4] #{_fmt_num(n)}: ラフなしのためスキップ")
            continue

        char_dir = pipeline_dir / f"char_{_fmt_num(n)}"
        rough_results = {"gemini": rough_paths, "adobe_guide": [], "all": rough_paths}
        corrected = correct_rough_images(
            rec, forms_map[n],
            rough_results=rough_results,
            char_spec=char_data_map[n]["spec"],
            prompts=per_char_prompts[n],
            pipeline_dir=char_dir,
            work_key=work_key,
            correction_mode=correction_mode,
        )
        all_stage4_paths[f"char_{_fmt_num(n)}"] = [str(p) for p in corrected.get("all") or []]

        # ベスト 1 枚: 違反なし通過画像を優先、なければ修正済みの先頭
        best = (corrected.get("passed") or [])[:1] or (corrected.get("corrected") or [])[:1]
        if best:
            per_char_best.extend(best)
            print(f"  [Stage4] #{_fmt_num(n)}: ベスト 1 枚選定 → {best[0].name}")
        else:
            # 修正も通過もなければ元ラフの先頭をフォールバック
            per_char_best.extend(rough_paths[:1])
            print(f"  [Stage4] #{_fmt_num(n)}: フォールバック → {rough_paths[0].name}")

    result.stage4_paths = all_stage4_paths
    result.stage4_paths["best_per_char"] = [str(p) for p in per_char_best]
    print(f"[Stage4] done - 合成用ベスト: {len(per_char_best)} 枚 ({', '.join(p.name for p in per_char_best)})")
    if stage_callback:
        try:
            stage_callback("stage4", result.stage4_paths, str(pipeline_dir))
        except Exception as _cb_err:
            print(f"[WARN] stage_callback(stage4) error: {_cb_err}")

    # ── Stage 5: ベストレンダーを Gemini マルチ参照で 1 枚に合成 ──
    # comp_rough があれば先頭参照として差し込み、構図ガイドとして Gemini に渡す。
    has_comp_rough = bool(comp_rough_paths)
    stage5_refs = ([comp_rough_paths[0]] if has_comp_rough else []) + per_char_best
    _comp_note = " + 構図ラフ参照あり" if has_comp_rough else ""
    print(f"\n[=] Stage 5: キャラクター完成レンダー {len(per_char_best)} 枚を合成 ({_STAGE5_SYNTH_COUNT} 枚, 仕上げ){_comp_note}")
    composition_prompt = _build_multi_char_composition_prompt(
        records, forms_map, scene, has_comp_rough=has_comp_rough
    )
    stage5_dir = pipeline_dir / "stage5_final"
    synth_images = _compose_multi_char(
        records[0], primary_form,
        char_renders=stage5_refs,
        composition_prompt=composition_prompt,
        synth_dir=stage5_dir / "synth",
        work_key=work_key,
        count=_STAGE5_SYNTH_COUNT,
    )
    print(f"[Stage5] done - {len(synth_images)} 枚合成完了")

    result.stage5_paths = {
        "synth": [str(p) for p in synth_images],
        "canva": [],
        "all": [str(p) for p in synth_images],
    }
    result.status = (
        "ok" if synth_images
        else "partial" if all_stage3
        else "failed"
    )
    _save_summary(pipeline_dir, result, start_time)
    print(f"\n[CombinedPipeline] done - {nums_label} / status={result.status}")
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
        print(f"[MultiPipeline] {i}/{len(char_params)}: #{_fmt_num(cp['num'])} / {cp['form']}")
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
        "field_overrides": prompts.get("field_overrides") or {},
        "field_resolutions": prompts.get("field_resolutions") or {},
    }
    (stage1_dir / "stage1_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _save_summary(
    pipeline_dir: Path,
    result: "PipelineResult | MultiCharPipelineResult",
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

def _resolve_num_arg(raw: str) -> int | str:
    """--num / --nums 引数をキャラクター ID に変換する。
    "57" → 57  "2-alt" → "2-alt"  "バイナ" → "2-alt"  "フジ" → 22
    名前解決に失敗した場合は文字列 ID として返す。
    """
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)
    try:
        from src.pipeline.natural_parser import _build_name_lookup
        lookup = _build_name_lookup()
        if raw in lookup:
            num_str = lookup[raw]
            return int(num_str) if num_str.isdigit() else num_str
    except Exception:
        pass
    try:
        return int(raw)
    except ValueError:
        return raw


def _maybe_prompt_ambiguous_fields_interactively(
    char_params: list[dict], default_work_key: str, non_interactive: bool
) -> None:
    """実ターミナル (TTY) 上でのみ、RaceType 等の曖昧フィールドを対話確認する。

    char_params の各要素を必要に応じて in-place で更新する
    (scene 未指定なら確定させ、必要なら field_overrides を設定する)。
    非TTY (エージェント経由の Bash 実行・MCP の Cloud Run ジョブ) では即座に no-op で戻る。
    """
    if non_interactive or not sys.stdin.isatty():
        return

    from src.utils import find_character
    from src.utils.dataset import _AMBIGUOUS_FIELD_SPECS, describe_ambiguous_field_resolutions

    for cp in char_params:
        form = cp.get("form", "corefolder")
        applicable_specs = [s for s in _AMBIGUOUS_FIELD_SPECS if form in s.forms]
        if not applicable_specs:
            continue

        record = find_character(cp["num"], cp.get("work_key", default_work_key))
        if record is None:
            continue

        existing_overrides: dict[str, str] = dict(cp.get("field_overrides") or {})

        if not cp.get("scene"):
            cp["scene"] = generate_random_scene(record, form) or ""
            # ↑ ここで scene を確定させておくことで、後段の Stage1 が別のランダムシーンを
            #   再生成して自動判定と食い違う事態を防ぐ。

        resolutions = describe_ambiguous_field_resolutions(
            record, form, scene=cp["scene"], field_overrides=existing_overrides
        )
        for spec in applicable_specs:
            if spec.field_name in existing_overrides:
                continue  # 既に明示指定済み
            info = resolutions.get(spec.field_name)
            if not info or len(info.get("candidates") or []) < 2:
                continue  # 曖昧ではない

            candidates = info["candidates"]
            print(f"\n[確認] #{cp['num']} の「{spec.label_ja}」候補が複数あります:")
            for i, c in enumerate(candidates, start=1):
                marker = " <- 自動選択" if c.get("value") == info.get("value") else ""
                print(f"  {i}) {c.get('value')} — {c.get('about_JP', '')}{marker}")
            print(f"  自動判定理由: {info.get('reasoning') or '(なし)'}")

            try:
                choice = input("  Enter で確定 / 番号で上書き > ").strip()
            except (EOFError, KeyboardInterrupt):
                choice = ""
            if choice:
                try:
                    idx = int(choice) - 1
                except ValueError:
                    idx = -1
                if 0 <= idx < len(candidates):
                    existing_overrides[spec.field_name] = str(candidates[idx].get("value", ""))
                    print(f"  → 上書き: {existing_overrides[spec.field_name]}")
                else:
                    print("  無効な入力のため自動選択を使用します。")

        if existing_overrides:
            cp["field_overrides"] = existing_overrides


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
        "--num", type=str,
        help="キャラクター番号・特殊ID・キャラ名 (例: 57 / '2-alt' / 'バイナ')。シーン未指定時はランダム生成。",
    )
    char_group.add_argument(
        "--nums",
        help=(
            "複数キャラクター番号 カンマ区切り (例: 25,57)。"
            "2 件以上指定すると全員を 1 枚に合同生成する (マルチキャラクターシーン)。"
        ),
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
        "--costume", default="",
        help=(
            "衣装差分の説明。デフォルト衣装から変更する場合に指定する。\n"
            "例: '黒いワンピース姿の差分' / 'summer school uniform variation'"
        ),
    )
    parser.add_argument(
        "--field-override", action="append", default=None, dest="field_override",
        metavar="FIELD=VALUE",
        help=(
            "RaceType 等の曖昧フィールド（複数候補から1つ選ぶ必要があるもの）を明示指定する。\n"
            "繰り返し指定可能。未指定フィールドはシーン文脈から LLM が自動判定する。\n"
            "例: --field-override RaceType=最終的な設計目標 --field-override Height_cm=190"
        ),
    )
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
        "--iterate-from", default=None, dest="iterate_from",
        metavar="PATH",
        help=(
            "前回生成画像 (ファイルパスまたは run-dir) を起点に i2i モードで Stage 3 を実行する。\n"
            "Stage 4 (違反修正) / Stage 5 (Canva) は通常通り走る。\n"
            "例: output/20260616/.../num057_corefolder_01.jpg"
        ),
    )
    parser.add_argument(
        "--revisions", default=None,
        metavar="TEXT",
        help=(
            "修正指示。';' または改行で複数項目に分割される。--iterate-from と組み合わせて使用。\n"
            "例: '尻尾は元のまま; 表情だけ笑顔にして'"
        ),
    )
    parser.add_argument(
        "--rough-provider", default="gemini", dest="rough_provider",
        choices=["gemini", "sdxl-guide", "sdxl", "both"],
        help=(
            "Stage 3 のラフ生成プロバイダ (既定: gemini)。\n"
            "  sdxl-guide: SDXL でコアフォルダのアタリ(構図/作風の下敷き)を生成し、\n"
            "              Gemini ラフの追加参照に渡す (個体正確性は Gemini+DB が担う・GCE VM 課金注意)\n"
            "  sdxl / both: 旧・併走ピアモード (非推奨)。警告のうえ sdxl-guide に読み替える。\n"
            "単体キャラ実行のみ対応。合同 (--nums) では gemini 固定。"
        ),
    )
    parser.add_argument(
        "--prefer-gemini-parse", action="store_true",
        help="--natural / --story のパース時に Gemini を OpenAI より優先する",
    )
    parser.add_argument(
        "--non-interactive", action="store_true", dest="non_interactive",
        help=(
            "実ターミナル (TTY) 実行時でも、曖昧フィールドの対話確認プロンプトを出さない。\n"
            "CI・スクリプト等、TTY はあるが対話させたくない場合に指定する。"
        ),
    )
    args = parser.parse_args()

    # 旧・併走ピアモード (sdxl/both) は廃止。sdxl-guide (アタリ→Gemini参照) に読み替える。
    if args.rough_provider in ("sdxl", "both"):
        print(
            f"[WARN] --rough-provider {args.rough_provider} は廃止されました。"
            "sdxl-guide (SDXL アタリを Gemini の構図参照に使う) に読み替えます。"
        )
        args.rough_provider = "sdxl-guide"

    field_override: dict[str, str] = {}
    for kv in (args.field_override or []):
        if "=" not in kv:
            sys.exit(f"[ERROR] --field-override は FIELD=VALUE 形式で指定してください: {kv!r}")
        k, v = kv.split("=", 1)
        k = k.strip()
        if not k:
            sys.exit(f"[ERROR] --field-override のフィールド名が空です: {kv!r}")
        field_override[k] = v.strip()

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
            if args.costume and not cp.get("costume"):
                cp["costume"] = args.costume
            if field_override and not cp.get("field_overrides"):
                cp["field_overrides"] = dict(field_override)
            if args.form != "corefolder":
                cp["form"] = args.form

    elif args.nums:
        raw_nums = [s.strip() for s in args.nums.split(",") if s.strip()]
        nums: list[int | str] = [_resolve_num_arg(s) for s in raw_nums]
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
                "costume": args.costume,
                "field_overrides": dict(field_override),
                "work_key": args.work,
            })

    elif args.num:
        char_params.append({
            "num": _resolve_num_arg(args.num),
            "form": args.form,
            "scene": args.scene,
            "style": args.style,
            "composition": args.composition,
            "background": args.background,
            "costume": args.costume,
            "field_overrides": dict(field_override),
            "work_key": args.work,
        })

    else:
        parser.error("--num / --nums / --natural / --story のいずれかを指定してください。")

    _maybe_prompt_ambiguous_fields_interactively(
        char_params, default_work_key=args.work, non_interactive=args.non_interactive
    )

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
            costume=cp.get("costume", args.costume),
            field_overrides=cp.get("field_overrides") or field_override,
            skip_canva=args.skip_canva,
            correction_mode=args.correction_mode,
            iterate_from=args.iterate_from,
            revisions=args.revisions,
            rough_provider=args.rough_provider,
        )
        print(f"\n[完了] ステータス: {result.status}")
        if result.scene_used:
            print(f"  シーン: {result.scene_used}")
        if result.errors:
            for err in result.errors:
                print(f"  [ERROR] {err}")
        s5 = result.stage5_paths.get("all") or []
        s4_all = result.stage4_paths.get("all") or []
        s3_gemini = result.stage3_paths.get("gemini") or []
        if s5:
            print(f"  完成画像 (Stage5): {len(s5)} 枚")
        if s4_all:
            print(f"  修正済みラフ (Stage4): {len(s4_all)} 枚")
        if s3_gemini:
            print(f"  ラフ (Stage3): Gemini {len(s3_gemini)} 枚")
        s3_sdxl_guide = result.stage3_paths.get("sdxl_guide") or []
        if s3_sdxl_guide:
            print(f"  アタリ (Stage3): SDXL {len(s3_sdxl_guide)} 枚 (Gemini 参照用)")

    else:
        # 2 件以上の --nums → 全員を 1 枚に合同生成
        if args.rough_provider != "gemini":
            print("[WARN] --rough-provider (sdxl-guide) は合同生成 (--nums) では未対応です。gemini で続行します。")
        combined_nums = [cp["num"] for cp in char_params]
        combined_scene = char_params[0].get("scene", "") or args.scene
        combined_forms = [cp.get("form", args.form) for cp in char_params]
        res = run_combined_pipeline(
            nums=combined_nums,
            forms=combined_forms,
            form=combined_forms[0],
            work_key=char_params[0].get("work_key", args.work),
            out_dir=args.out,
            scene=combined_scene,
            style=char_params[0].get("style", args.style),
            composition=char_params[0].get("composition", args.composition),
            background=char_params[0].get("background", args.background),
            costume=char_params[0].get("costume", args.costume),
            field_overrides=char_params[0].get("field_overrides") or field_override,
            skip_canva=args.skip_canva,
            correction_mode=args.correction_mode,
            iterate_from=args.iterate_from,
            revisions=args.revisions,
        )
        nums_label = "+".join(f"#{_fmt_num(n)}" for n in res.nums)
        scene_preview = (res.scene_used[:24] + "...") if len(res.scene_used) > 24 else res.scene_used
        print(f"\n[完了] {nums_label} / ステータス: {res.status} / シーン: {scene_preview}")
        if res.errors:
            for err in res.errors:
                print(f"  [ERROR] {err}")
        s5 = res.stage5_paths.get("all") or []
        s3 = res.stage3_paths.get("gemini") or []
        if s5:
            print(f"  完成画像 (Stage5): {len(s5)} 枚")
        if s3:
            print(f"  Gemini ラフ (Stage3): {len(s3)} 枚")


if __name__ == "__main__":
    main()
