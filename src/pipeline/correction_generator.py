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
) -> list[Path]:
    """違反分析結果を基に Gemini i2i で修正を適用する。"""
    from src.gemini.generate import generate_image

    violations = analysis.get("violations") or []
    comp_issues = analysis.get("composition_issues") or []
    spec_instruction = (
        "[形態修正指示]\n"
        + "\n".join(f"- {v} を除去または修正してください" for v in violations)
        + ("\n[構図修正]\n" + "\n".join(f"- {c}" for c in comp_issues) if comp_issues else "")
    )

    base_prompt = prompts.get("gemini", "")
    correction_prompt = (
        f"{spec_instruction}\n\n[ベースプロンプト (維持すること)]\n{base_prompt}"
        if base_prompt
        else spec_instruction
    )

    correct_subdir = stage_dir / f"rough_{index:02d}_corrected"
    correct_subdir.mkdir(parents=True, exist_ok=True)

    try:
        return generate_image(
            num=record["data"]["Num"],
            form=form,
            work_key=work_key,
            out_dir=str(correct_subdir),
            count=1,
            iterate_from=str(rough_path),
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
) -> dict[str, list[Path]]:
    """Stage 4: ラフ画像の違反特徴を修正し、形態として違和感のない状態にする。

    Parameters
    ----------
    record:       キャラクターレコード
    form:         形態
    rough_results: Stage 3 の結果 (generate_rough_images の返却値)
    char_spec:    Stage 2 で構築したキャラクタースペック
    prompts:      Stage 1 の精錬プロンプト dict
    pipeline_dir: パイプライン出力ルートディレクトリ
    work_key:     作品キー

    Returns
    -------
    {
        "corrected": list[Path]  — 修正が適用された画像
        "passed":    list[Path]  — 違反なし/スキップで通過した画像
        "all":       list[Path]  — corrected + passed (Stage 5 への入力)
    }
    """
    stage_dir = pipeline_dir / "stage4_correct"
    stage_dir.mkdir(parents=True, exist_ok=True)

    rough_paths: list[Path] = rough_results.get("gemini") or []
    if not rough_paths:
        print("[Stage4] ラフ画像がありません。Stage 4 をスキップします。")
        return {"corrected": [], "passed": [], "all": []}

    corrected: list[Path] = []
    passed: list[Path] = []
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

        if skipped:
            print(f"[Stage4] rough_{i:02d}: 分析スキップ (API未設定) → pass-through")
            passed.append(rough_path)
        elif overall_ok and not violations and not comp_issues:
            print(f"[Stage4] rough_{i:02d}: 違反なし → pass-through")
            passed.append(rough_path)
        else:
            issues = violations + comp_issues
            print(f"[Stage4] rough_{i:02d}: 違反 {len(violations)}件・構図問題 {len(comp_issues)}件 → Gemini で修正")
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
            "corrected": bool(corrected_paths if not (skipped or overall_ok) else False),
        })

    _save_analysis_log(stage_dir, analysis_log)

    all_paths = corrected + passed
    print(
        f"[Stage4] done - 修正: {len(corrected)} / 通過: {len(passed)} / total: {len(all_paths)}"
    )
    return {
        "corrected": corrected,
        "passed": passed,
        "all": all_paths,
    }


def _save_analysis_log(stage_dir: Path, log: list[dict]) -> None:
    (stage_dir / "analysis_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8"
    )
