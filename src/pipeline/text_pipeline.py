"""
pipeline/text_pipeline.py — マルチ LLM テキスト生成パイプライン
Copyright © RadianN_kswg — CC BY-NC 4.0

GPT-4o (プライマリ生成) と Gemini (クロスレビュー・改善) を組み合わせ、
キャラクターの不変特徴への整合性と文章品質を高める。

ワークフロー:
  Step 1: キャラクターデータベースを読み込む
  Step 2: OpenAI (GPT-4o) でプライマリテキストを生成
  Step 3: Gemini がキャラクター特徴の正確性と文章品質をレビュー・改善
  Step 4: 最終テキストとして出力・保存

使用方法:
    # シーン文章を生成
    python -m src.pipeline.text_pipeline --num 57 --mode scene \\
        --prompt "図書館で先輩と本を読んでいるシーン"

    # キャラクター紹介文を生成
    python -m src.pipeline.text_pipeline --num 57 --mode description

    # イラストキャプションを生成
    python -m src.pipeline.text_pipeline --num 57 --mode caption \\
        --prompt "夕暮れの研究所テラスで一人たたずむシーン"

モード:
    scene       — キャラクターが登場するシーン文章 (創作向け)
    description — キャラクター紹介・外見描写 (Wiki/DB 向け)
    caption     — イラストキャプション / alt-text (100文字以内)

保存先:
    {OUTPUT_BASE_DIR}/{YYYYMMDD}/{ts}_textpipeline_{form}_num{NNN}_scene/
      primary_openai.txt  — GPT-4o 生成テキスト
      reviewed_gemini.txt — Gemini レビュー後テキスト
      final.txt           — 最終テキスト (= reviewed_gemini)
      run_meta.json       — 実行メタデータ

必要な環境変数 (.env):
    OPENAI_API_KEY         — GPT-4o 用
    GEMINI_API_KEY         — Gemini レビュー用
    GPT_MODEL              — OpenAI テキストモデル (デフォルト: gpt-4o)
    GEMINI_TEXT_MODEL      — Gemini テキストモデル (デフォルト: gemini-2.0-flash-001)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import (  # noqa: E402
    apply_generation_gate,
    build_run_output_dir,
    find_character,
)


_SYSTEM_MESSAGES: dict[str, str] = {
    "scene": (
        "You are a creative writer for the NumberTales series. "
        "Write vivid, engaging scene descriptions in Japanese. "
        "All immutable character traits (ear type, tail count, hair color, eye color) "
        "MUST be accurately reflected. "
        "Keep the tone warm, lively, and consistent with the series' world setting."
    ),
    "description": (
        "You are a character description writer for the NumberTales series. "
        "Write accurate, engaging character introductions in Japanese. "
        "All immutable traits (ear type, tail count, hair color, eye color) "
        "MUST be accurately described. Be precise about appearance details."
    ),
    "caption": (
        "You are an illustration caption writer for the NumberTales series. "
        "Write concise, descriptive captions in Japanese suitable for image alt-text. "
        "All key visual elements must be accurately described. "
        "Keep it under 100 characters."
    ),
}

_USER_TEMPLATES: dict[str, str] = {
    "scene": (
        "キャラクター「{name}」({form}形態)の登場するシーン文章を書いてください。\n\n"
        "[キャラクター情報]\n{char_summary}\n\n"
        "[リクエスト]\n{user_prompt}\n\n"
        "自然で生き生きとした日本語の短編シーン文章（200〜400字程度）を書いてください。"
    ),
    "description": (
        "キャラクター「{name}」({form}形態)の紹介・外見描写を書いてください。\n\n"
        "[キャラクター情報]\n{char_summary}\n\n"
        "不変特徴（耳の種類・尻尾の本数・髪色・瞳色）を正確に含めた\n"
        "日本語の紹介文（150〜300字程度）を書いてください。"
    ),
    "caption": (
        "キャラクター「{name}」({form}形態)のイラストキャプションを書いてください。\n\n"
        "[キャラクター情報]\n{char_summary}\n\n"
        "[シーン・状況]\n{user_prompt}\n\n"
        "100文字以内の簡潔な日本語キャプションのみを出力してください。"
    ),
}

_GEMINI_REVIEW_SYSTEM = (
    "You are a quality reviewer for NumberTales character text content in Japanese. "
    "Review the provided text for: "
    "(1) Accuracy of immutable character traits — these MUST be correct, "
    "(2) Consistency with the NumberTales world setting, "
    "(3) Quality and naturalness of Japanese writing. "
    "Return ONLY the improved Japanese text. No review comments, no explanations."
)


def _build_char_summary(record: dict) -> str:
    data = record.get("data") or {}
    hints = record.get("ai_hints") or {}
    common = hints.get("common") or {}

    lines: list[str] = []
    name = data.get("Name_JP") or data.get("Name")
    num = data.get("Num")
    if name:
        lines.append(f"名前: {name}" + (f" (#{num})" if num else ""))
    immutable = common.get("immutable_traits") or []
    if immutable:
        # (corefolder) / (humanoid) の形態注記はテキスト文脈では不要なので除去して表示する
        immutable_display = [re.sub(r"\s*\((corefolder|humanoid)\)\s*$", "", t) for t in immutable]
        lines.append(f"不変特徴: {', '.join(immutable_display)}")
    identity = common.get("identity_tags") or []
    if identity:
        lines.append(f"識別記号: {', '.join(identity)}")
    natural_desc = (common.get("natural_language_description") or "").strip()
    if natural_desc:
        lines.append(f"外見: {natural_desc}")
    return "\n".join(lines)


def _generate_openai(
    record: dict,
    form: str,
    mode: str,
    user_prompt: str,
) -> str:
    """GPT-4o でプライマリテキストを生成する。失敗時は空文字を返す。"""
    try:
        from openai import OpenAI
    except ImportError:
        print("[WARN] openai パッケージが見つかりません。スキップします。")
        return ""

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[WARN] OPENAI_API_KEY が未設定です。OpenAI 生成をスキップします。")
        return ""

    gpt_model = os.environ.get("GPT_MODEL", "gpt-4o")
    name = record["data"].get("Name_JP") or record["data"].get("Name") or "Unknown"
    char_summary = _build_char_summary(record)
    template = _USER_TEMPLATES.get(mode, _USER_TEMPLATES["scene"])
    user_msg = template.format(
        name=name, form=form,
        char_summary=char_summary,
        user_prompt=user_prompt or "（指定なし）",
    )
    system_msg = _SYSTEM_MESSAGES.get(mode, _SYSTEM_MESSAGES["scene"])

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=gpt_model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=800,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as err:
        print(f"[WARN] OpenAI テキスト生成に失敗: {err}")
        return ""


def _review_gemini(
    record: dict,
    primary_text: str,
    mode: str,
) -> str:
    """Gemini でプライマリテキストをクロスレビュー・改善する。失敗時は primary_text をそのまま返す。"""
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        print("[WARN] google-genai パッケージが見つかりません。Gemini レビューをスキップします。")
        return primary_text

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[WARN] GEMINI_API_KEY が未設定です。Gemini レビューをスキップします。")
        return primary_text

    text_model = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
    hints = record.get("ai_hints") or {}
    common = hints.get("common") or {}
    immutable = common.get("immutable_traits") or []
    name = record["data"].get("Name_JP") or record["data"].get("Name") or "Unknown"

    immutable_display = [re.sub(r"\s*\((corefolder|humanoid)\)\s*$", "", t) for t in immutable]
    review_prompt = (
        f"以下は「{name}」というキャラクターについての{mode}テキストです。\n\n"
        "[このキャラクターの不変特徴（必ず正確に反映すること）]\n"
        + ("\n".join(f"- {t}" for t in immutable_display) or "- （未設定）")
        + f"\n\n[レビュー対象テキスト]\n{primary_text}\n\n"
        "上記テキストをレビューし、改善したテキストのみを出力してください。"
        "（レビューコメント・説明文は不要）"
    )

    client = genai.Client(api_key=api_key)
    # gemini-2.5-flash は thinking に大量トークンを消費するため無効化
    thinking_cfg = None
    if "gemini-2.5" in text_model or "gemini-2.0" in text_model:
        try:
            thinking_cfg = genai_types.ThinkingConfig(thinking_budget=0)
        except AttributeError:
            pass  # SDK が ThinkingConfig を持たない旧バージョンでは無視

    try:
        cfg = genai_types.GenerateContentConfig(
            system_instruction=_GEMINI_REVIEW_SYSTEM,
            max_output_tokens=4096,
            **({"thinking_config": thinking_cfg} if thinking_cfg else {}),
        )
        response = client.models.generate_content(
            model=text_model,
            contents=review_prompt,
            config=cfg,
        )
        result = (response.text or "").strip()
        # 文末記号（。！？）で終わっていない = 途中で切れている
        _SENTENCE_ENDS = ("。", "！", "？", ".", "!", "?", "」", "』")
        is_truncated = result and not result.endswith(_SENTENCE_ENDS)
        is_too_short = result and len(result) < len(primary_text) * 0.5
        if is_truncated or is_too_short:
            print(
                f"[WARN] Gemini レビュー応答が不完全 ({len(result)}chars, "
                f"末尾={result[-4:] if result else ''!r})。OpenAI 生成結果を使用します。"
            )
            return primary_text
        return result if result else primary_text
    except Exception as err:
        print(f"[WARN] Gemini レビューに失敗: {err}")
        return primary_text


def run_text_pipeline(
    num: int,
    form: str = "corefolder",
    mode: str = "scene",
    user_prompt: str = "",
    work_key: str = "#Works_NumberTales",
    out_dir: str | None = None,
) -> dict:
    """マルチ LLM テキスト生成パイプラインを実行する。

    Parameters
    ----------
    num:        キャラクター番号
    form:       形態
    mode:       "scene" / "description" / "caption"
    user_prompt: シーン・状況説明 (scene/caption モードで使用)
    work_key:   作品キー
    out_dir:    出力ベースディレクトリ

    Returns
    -------
    {
        "primary":    str — GPT-4o 生成テキスト
        "reviewed":   str — Gemini レビュー後テキスト
        "final":      str — 最終テキスト
        "output_dir": str — 出力ディレクトリパス
    }
    """
    start_time = datetime.now()
    output_dir = build_run_output_dir(
        provider="textpipeline",
        num=num,
        form=form,
        base_dir=out_dir,
        suffix=mode,
        timestamp=start_time,
    )
    print(f"\n[TextPipeline] start - #{num} {form} mode={mode}")
    print(f"[TextPipeline] 出力先: {output_dir}")

    record = find_character(num, work_key)
    if record is None:
        print(f"[ERROR] キャラクター #{num} ({work_key}) が見つかりません。")
        return {
            "primary": "", "reviewed": "", "final": "[キャラクター未発見]",
            "output_dir": str(output_dir),
        }

    # AI 学習/生成オプトアウト・ゲート（テキスト用途。権利軸=中止、充填軸=警告のうえ続行）。
    # 本パイプラインは shipped 済みだが従来ゲート無しだったため棚卸しで是正。
    proceed, ai_gate = apply_generation_gate(record, usage="text", num=num, printer=print)
    if not proceed:
        return {
            "primary": "", "reviewed": "",
            "final": f"[ai-optout: {ai_gate['reason']}]",
            "output_dir": str(output_dir),
        }

    char_name = record["data"].get("Name_JP") or record["data"].get("Name") or f"#{num}"
    print(f"[TextPipeline] キャラクター: {char_name}")

    # Step 2: GPT-4o でプライマリ生成
    print(f"[TextPipeline/Step2] OpenAI GPT-4o で {mode} テキスト生成中...")
    primary = _generate_openai(record, form, mode, user_prompt)
    if not primary:
        print("[WARN] OpenAI テキスト生成に失敗しました。Gemini のみで処理します。")
        primary = f"[OpenAI 生成失敗: {char_name} / {form} / {mode}]"

    # Step 3: Gemini でクロスレビュー・改善
    print("[TextPipeline/Step3] Gemini でクロスレビュー中...")
    reviewed = _review_gemini(record, primary, mode)

    final = reviewed or primary
    elapsed = (datetime.now() - start_time).total_seconds()

    # 保存
    (output_dir / "primary_openai.txt").write_text(primary, encoding="utf-8")
    (output_dir / "reviewed_gemini.txt").write_text(reviewed, encoding="utf-8")
    (output_dir / "final.txt").write_text(final, encoding="utf-8")
    meta = {
        "num": num,
        "form": form,
        "mode": mode,
        "work_key": work_key,
        "character_name": char_name,
        "user_prompt": user_prompt,
        "primary_length": len(primary),
        "reviewed_length": len(reviewed),
        "final_length": len(final),
        "elapsed_seconds": round(elapsed, 1),
        "models": {
            "openai": os.environ.get("GPT_MODEL", "gpt-4o"),
            "gemini": os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash"),
        },
        "ai_training_gate": ai_gate,
    }
    (output_dir / "run_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[TextPipeline] done - {elapsed:.1f}s / final: {len(final)}chars")

    return {
        "primary": primary,
        "reviewed": reviewed,
        "final": final,
        "output_dir": str(output_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "マルチ LLM テキスト生成パイプライン:\n"
            "  Step2: OpenAI GPT-4o でプライマリ生成\n"
            "  Step3: Gemini でクロスレビュー・改善"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--num", type=int, required=True, help="キャラクター番号 (例: 57)")
    parser.add_argument(
        "--form", choices=["corefolder", "humanoid"], default="corefolder",
        help="形態 (デフォルト: corefolder)",
    )
    parser.add_argument(
        "--mode",
        choices=["scene", "description", "caption"],
        default="scene",
        help=(
            "生成モード: "
            "scene=シーン文章 / description=外見描写 / caption=イラストキャプション"
        ),
    )
    parser.add_argument(
        "--prompt", default="",
        help="シーン・状況説明 (scene/caption モードで有効)",
    )
    parser.add_argument("--work", default="#Works_NumberTales", help="作品キー")
    parser.add_argument(
        "--out", default=None,
        help="出力ベースディレクトリ (省略時は OUTPUT_BASE_DIR / 'output')",
    )
    args = parser.parse_args()

    result = run_text_pipeline(
        num=args.num,
        form=args.form,
        mode=args.mode,
        user_prompt=args.prompt,
        work_key=args.work,
        out_dir=args.out,
    )

    print("\n[最終テキスト]")
    print("─" * 60)
    print(result["final"])
    print("─" * 60)
    print(f"保存先: {result['output_dir']}")


if __name__ == "__main__":
    main()
