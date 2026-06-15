"""
pipeline/correction_generator.py — Stage 4: 違反特徴の除去 + 構図修正
Copyright © RadianN_kswg — CC BY-NC 4.0

Stage 3 のラフ5案を入力に、以下の2ステップで修正を行う:

  1. 分析 (OpenAI Vision):
     各ラフ画像をキャラクタースペックと照合し、
     「形態として存在しない特徴」「構図の破綻」を列挙する。
     (OPENAI_API_KEY 未設定の場合はスキップし Gemini のみで修正)

  2. 修正 (Gemini i2i):
     分析結果の違反リストを修正指示に変換し、Gemini i2i で適用する。
     違反なし・分析スキップのラフはそのまま pass-through する。

出力: stage4_correct/ に修正済み画像を保存。
Stage 5 はここで生成された画像 (最大 5 枚) を受け取り、3 枚を仕上げる。
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

# 違反件数がこの値以上なら i2i ではなく T2I（フル再生成）に切り替える。
# i2i は元画像の構造を維持するため、全身humanoidのような根本的な形態誤りを
# 1回では修正しきれない。T2I にすることで形態をリセットする。
_SEVERE_VIOLATION_THRESHOLD = 3

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ──────────────────────────────────────────
# OpenAI Vision による違反分析
# ──────────────────────────────────────────

def _analyze_rough_with_openai(image_path: Path, spec: dict) -> dict:
    """OpenAI Vision でラフ画像の違反特徴・構図問題を分析する。

    Returns
    -------
    {
        "violations": list[str],         — 存在すべきでない特徴
        "composition_issues": list[str], — 構図の破綻
        "overall_ok": bool,
        "skipped": bool,
    }
    """
    try:
        from openai import OpenAI
    except ImportError:
        return {"violations": [], "composition_issues": [], "overall_ok": True, "skipped": True}

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"violations": [], "composition_issues": [], "overall_ok": True, "skipped": True}

    if not image_path.exists():
        return {"violations": [], "composition_issues": [], "overall_ok": True, "skipped": True}

    gpt_model = os.environ.get("GPT_MODEL", "gpt-4o")
    form = spec.get("form", "corefolder")
    violation_list = "\n".join(f"- {v}" for v in spec.get("violation_features", []))
    immutable = ", ".join(spec.get("immutable_traits") or [])
    char_name = spec.get("char_name", "Unknown")

    system = (
        f"あなたはナンバーテールズキャラクター「{char_name}」の{form}形態イラストの品質検査AIです。\n"
        "画像に対して以下を確認し、**JSONのみ**を返してください（説明文・マークダウン不要）:\n"
        '{"violations": ["違反内容1", ...], "composition_issues": ["構図問題1", ...], "overall_ok": true}'
    )
    user = (
        f"このイラストを検査してください。\n"
        f"形態: {form}\n"
        f"不変特徴 (必ず存在するべき): {immutable}\n"
        f"以下の要素が存在する場合は violations に追加してください:\n{violation_list}\n\n"
        "構図として明らかに破綻している点があれば composition_issues に追加してください。\n"
        "問題がなければ overall_ok: true として violations と composition_issues は空リストにしてください。"
    )

    ext = image_path.suffix.lstrip(".").lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/png")
    img_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=gpt_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": [
                    {"type": "text", "text": user},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                ]},
            ],
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        raw = (response.choices[0].message.content or "{}").strip()
        result = json.loads(raw)
        result.setdefault("violations", [])
        result.setdefault("composition_issues", [])
        result.setdefault("overall_ok", True)
        result["skipped"] = False
        return result
    except Exception as err:
        print(f"[WARN] Stage4 OpenAI Vision 分析失敗: {err}")
        return {"violations": [], "composition_issues": [], "overall_ok": True, "skipped": True}


# ──────────────────────────────────────────
# Gemini i2i による修正適用
# ──────────────────────────────────────────

def _apply_correction_gemini(
    record: dict,
    form: str,
    rough_path: Path,
    analysis: dict,
    prompts: dict,
    stage_dir: Path,
    work_key: str,
    index: int,
    use_t2i: bool = False,
) -> list[Path]:
    """違反分析結果を基に Gemini で修正を適用する。

    use_t2i=True の場合は i2i をスキップして T2I（フル再生成）を行う。
    違反が重篤（_SEVERE_VIOLATION_THRESHOLD 以上）な場合に使用する。
    """
    from src.gemini.generate import generate_image

    violations = analysis.get("violations") or []
    comp_issues = analysis.get("composition_issues") or []
    # T2I はフル再生成なので全仕様を含む base_gemini を使う。
    # i2i はソース画像がスタイルアンカーになるため、修正ターゲットのみに絞った短いプロンプトを使う。
    # base_gemini を i2i に使うと「別のポーズで描いてください」という再生成指示が競合し作風が崩れる。
    base_prompt = prompts.get("base_gemini", "") or prompts.get("gemini", "")

    if use_t2i:
        avoid_note = ""
        if violations:
            avoid_items = "; ".join(violations[:4])
            avoid_note = f"\n\n[特に避けること (前回生成で検出された違反)]\n- {avoid_items}"
        correction_prompt = base_prompt + avoid_note
        iterate_path = None
        print(f"[Stage4] rough_{index:02d}: 違反 {len(violations)} 件 → T2I (フル再生成)")
    else:
        # i2i 専用: 最小限の修正指示のみ。ソース画像の作風・構図を最大限維持させる。
        hints = record.get("ai_hints") or {}
        _common = hints.get("common") or {}
        identity_tags = ", ".join(((_common.get("identity_tags") or []) + (_common.get("immutable_traits") or []))[:6])
        num_val = (record.get("data") or {}).get("Num", "?")

        fix_lines = "\n".join(f"- {v} を除去または修正" for v in violations)
        comp_lines = (
            "\n[構図修正]\n" + "\n".join(f"- {c}" for c in comp_issues) if comp_issues else ""
        )
        correction_prompt = (
            "[i2i 最小修正 — 入力画像の作風・構図・フォルムを最大限維持すること]\n"
            "以下の違反のみを修正し、それ以外は入力画像に忠実に保つこと。\n\n"
            f"[修正対象]\n{fix_lines}{comp_lines}\n\n"
            "[維持すること]\n"
            f"- 形態: {form}\n"
            f"- 識別要素: {identity_tags}\n"
            f"- キャラクター番号: #{num_val}\n"
            "- 作風（線の太さ・塗りスタイル）は入力画像に合わせること\n"
            "- 画像内にテキスト・文字・ラベルを一切描かないこと"
        )
        iterate_path = str(rough_path)

    correct_subdir = stage_dir / f"rough_{index:02d}_corrected"
    correct_subdir.mkdir(parents=True, exist_ok=True)

    try:
        return generate_image(
            num=record["data"]["Num"],
            form=form,
            work_key=work_key,
            out_dir=str(correct_subdir),
            count=1,
            iterate_from=iterate_path,
            prompt_override=correction_prompt,
        )
    except SystemExit as err:
        print(f"[WARN] Stage4 Gemini 修正 (rough_{index:02d}): {err}")
        return []
    except Exception as err:
        print(f"[WARN] Stage4 Gemini 修正に失敗 (rough_{index:02d}): {type(err).__name__}: {err}")
        return []


# ──────────────────────────────────────────
# メイン関数
# ──────────────────────────────────────────

def correct_rough_images(
    record: dict,
    form: str,
    rough_results: dict[str, list[Path]],
    char_spec: dict,
    prompts: dict,
    pipeline_dir: Path,
    work_key: str = "#Works_NumberTales",
    correction_mode: str = "t2i",
) -> dict[str, list[Path]]:
    """Stage 4: ラフ画像の違反特徴を修正し、形態として違和感のない状態にする。

    Parameters
    ----------
    record:          キャラクターレコード
    form:            形態
    rough_results:   Stage 3 の結果 (generate_rough_images の返却値)
    char_spec:       Stage 2 で構築したキャラクタースペック
    prompts:         Stage 1 の精錬プロンプト dict
    pipeline_dir:    パイプライン出力ルートディレクトリ
    work_key:        作品キー
    correction_mode: 重度違反時の対処モード
                     "t2i"    — Stage 4 内で T2I フル再生成 (デフォルト)
                     "stage3" — Stage 3 に差し戻し (image_pipeline が再生成)

    Returns
    -------
    {
        "corrected":   list[Path]  — 修正が適用された画像
        "passed":      list[Path]  — 違反なし/スキップで通過した画像
        "needs_regen": list[Path]  — Stage 3 差し戻し対象 (stage3 モード時のみ)
        "all":         list[Path]  — corrected + passed (Stage 5 への入力)
    }
    """
    stage_dir = pipeline_dir / "stage4_correct"
    stage_dir.mkdir(parents=True, exist_ok=True)

    rough_paths: list[Path] = rough_results.get("gemini") or []
    if not rough_paths:
        print("[Stage4] ラフ画像がありません。Stage 4 をスキップします。")
        return {"corrected": [], "passed": [], "needs_regen": [], "all": []}

    corrected: list[Path] = []
    passed: list[Path] = []
    needs_regen: list[Path] = []
    analysis_log: list[dict] = []

    for i, rough_path in enumerate(rough_paths, 1):
        if not rough_path.exists():
            print(f"[Stage4] rough_{i:02d}: ファイルが見つかりません。スキップ。")
            continue

        print(f"[Stage4] ({i}/{len(rough_paths)}) {rough_path.name} を分析中...")
        analysis = _analyze_rough_with_openai(rough_path, char_spec)

        violations = analysis.get("violations") or []
        comp_issues = analysis.get("composition_issues") or []
        overall_ok = analysis.get("overall_ok", True)
        skipped = analysis.get("skipped", False)
        corrected_paths: list[Path] = []
        is_stage3_regen = False

        if skipped:
            print(f"[Stage4] rough_{i:02d}: 分析スキップ (API未設定) → pass-through")
            passed.append(rough_path)
        elif overall_ok and not violations and not comp_issues:
            print(f"[Stage4] rough_{i:02d}: 違反なし → pass-through")
            passed.append(rough_path)
        else:
            issues = violations + comp_issues
            is_severe = len(violations) >= _SEVERE_VIOLATION_THRESHOLD
            is_stage3_regen = is_severe and correction_mode == "stage3"
            use_t2i = is_severe and correction_mode == "t2i"

            if is_stage3_regen:
                print(
                    f"[Stage4] rough_{i:02d}: 違反 {len(violations)} 件"
                    f" → Stage 3 差し戻し予約 (correction_mode=stage3)"
                )
                needs_regen.append(rough_path)
            else:
                mode_label = "T2I (形態リセット)" if use_t2i else "i2i (部分修正)"
                print(
                    f"[Stage4] rough_{i:02d}: 違反 {len(violations)}件・構図問題 {len(comp_issues)}件"
                    f" → {mode_label}"
                )
                for issue in issues[:5]:
                    print(f"           - {issue}")

                corrected_paths = _apply_correction_gemini(
                    record, form,
                    rough_path=rough_path,
                    analysis=analysis,
                    prompts=prompts,
                    stage_dir=stage_dir,
                    work_key=work_key,
                    index=i,
                    use_t2i=use_t2i,
                )
                if corrected_paths:
                    corrected.extend(corrected_paths)
                else:
                    print(f"[WARN] Stage4 rough_{i:02d}: 修正失敗 → 元ラフを pass-through")
                    passed.append(rough_path)

        analysis_log.append({
            "rough_index": i,
            "file": rough_path.name,
            "violations": violations,
            "composition_issues": comp_issues,
            "overall_ok": overall_ok,
            "skipped": skipped,
            "corrected": bool(corrected_paths),
            "stage3_regen": is_stage3_regen,
        })

    _save_analysis_log(stage_dir, analysis_log)

    all_paths = corrected + passed
    regen_count = len(needs_regen)
    print(
        f"[Stage4] done - 修正: {len(corrected)} / 通過: {len(passed)}"
        + (f" / Stage3差し戻し: {regen_count}" if regen_count else "")
        + f" / total: {len(all_paths)}"
    )
    return {
        "corrected": corrected,
        "passed": passed,
        "needs_regen": needs_regen,
        "all": all_paths,
    }


def _save_analysis_log(stage_dir: Path, log: list[dict]) -> None:
    (stage_dir / "analysis_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8"
    )
