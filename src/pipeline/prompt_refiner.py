"""
pipeline/prompt_refiner.py — Stage 1: コマンド解析 + デュアル LLM プロンプト加工
Copyright © RadianN_kswg — CC BY-NC 4.0

OpenAI (GPT-4o) と Gemini (Flash) の両方でキャラデータベースに基づきプロンプトを加工する。
各モデルの強みを活かし、Stage 3 の各プロバイダに最適化されたプロンプトを生成する:
  - OpenAI 加工結果 → Stage 3/4 Adobe + 修正指示用
  - Gemini 加工結果  → Stage 3/4 Gemini Imagen / i2i 用

シーン未指定時はキャラクターの特徴に合ったランダムシーンを自動生成する。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import build_dalle_prompt, build_gemini_prompt, extract_char_name  # noqa: E402

_RANDOM_SCENE_SYSTEM = (
    "あなたはナンバーテールズシリーズのクリエイティブディレクターです。"
    "キャラクターのデータを基に、そのキャラクターが映えるシーン・ポーズを1つ提案してください。"
    "- 30文字以内で「〜しているシーン」「〜のポーズ」のような日本語表現で返すこと"
    "- キャラクターの形態・特徴と自然に合うシーンを選ぶこと"
    "- 単純な「立っている」は避け、行動・感情・状況が伝わる表現にする"
    "- シーン説明のみ返すこと。JSON・説明文・前置きは不要"
)


def generate_random_scene(record: dict, form: str) -> str:
    """シーン未指定時にキャラクターに合ったシーン説明をランダム生成する。"""
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        return ""

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return ""

    hints = record.get("ai_hints") or {}
    common = hints.get("common") or {}
    form_data = (hints.get("forms") or {}).get(form) or {}
    identity = ", ".join((common.get("identity_tags") or [])[:5])
    form_desc = str(form_data.get("natural_language_description", ""))[:80]
    char_name = extract_char_name(record)

    user_msg = (
        f"キャラクター: {char_name} / 形態: {form}\n"
        f"特徴: {identity}\n"
        f"形態概要: {form_desc}\n"
        "このキャラクターに合ったシーンを1つ提案してください:"
    )

    try:
        text_model = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=text_model,
            contents=user_msg,
            config=genai_types.GenerateContentConfig(
                system_instruction=_RANDOM_SCENE_SYSTEM,
                max_output_tokens=80,
            ),
        )
        scene = (response.text or "").strip().splitlines()[0].strip()
        if scene:
            print(f"[Stage1] ランダムシーン自動生成: {scene}")
            return scene
    except Exception as err:
        print(f"[WARN] ランダムシーン生成に失敗: {err}")
    return ""


def _system_instruction(char_name: str, form: str) -> str:
    return (
        f"You are an expert image generation prompt engineer for the NumberTales series character "
        f"'{char_name}' in {form} form. "
        "Optimize the given base prompt for high-quality character image generation. "
        "CRITICAL: preserve all immutable traits — ear type, tail count, hair color, eye color. "
        "Return ONLY the refined English prompt. No explanations, no markdown, prompt text only."
    )


def _user_message(
    base_prompt: str,
    scene: str,
    style: str,
    composition: str,
    background: str,
    costume: str = "",
) -> str:
    lines = ["Refine this image generation prompt for maximum quality:\n", base_prompt]
    extras: list[str] = []
    if costume:
        extras.append(
            f"Costume variation: {costume} "
            "(override the default outfit while keeping all immutable traits)"
        )
    if scene:
        extras.append(f"Scene/pose: {scene}")
    if style:
        extras.append(f"Art style: {style}")
    if composition:
        extras.append(f"Composition: {composition}")
    if background:
        extras.append(f"Background: {background}")
    if extras:
        lines.append("\nAdditional requirements to incorporate:\n" + "\n".join(extras))
    lines.append("\nReturn only the refined prompt:")
    return "\n".join(lines)


def refine_with_openai(
    record: dict,
    form: str,
    scene: str = "",
    style: str = "",
    composition: str = "",
    background: str = "",
    costume: str = "",
) -> str:
    """GPT-4o でプロンプトを加工して返す。失敗時はベースプロンプト (DALL-E 形式) を返す。"""
    try:
        from openai import OpenAI
    except ImportError:
        print("[WARN] openai パッケージが見つかりません。OpenAI プロンプト加工をスキップします。")
        return ""

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[WARN] OPENAI_API_KEY が未設定です。OpenAI プロンプト加工をスキップします。")
        return ""

    gpt_model = os.environ.get("GPT_MODEL", "gpt-4o")
    char_name = extract_char_name(record)
    base_prompt = build_dalle_prompt(
        record, form, scene=scene, style=style,
        composition=composition, background=background,
    )

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=gpt_model,
            messages=[
                {"role": "system", "content": _system_instruction(char_name, form)},
                {"role": "user", "content": _user_message(
                    base_prompt, scene, style, composition, background, costume)},
            ],
            max_tokens=600,
        )
        result = (response.choices[0].message.content or "").strip()
        return result if result else base_prompt
    except Exception as err:
        print(f"[WARN] OpenAI プロンプト加工に失敗: {err}")
        return base_prompt


def refine_with_gemini(
    record: dict,
    form: str,
    scene: str = "",
    style: str = "",
    composition: str = "",
    background: str = "",
    costume: str = "",
) -> str:
    """Gemini テキストモデルでプロンプトを加工して返す。失敗時はベースプロンプト (Gemini 形式) を返す。"""
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        print("[WARN] google-genai パッケージが見つかりません。Gemini プロンプト加工をスキップします。")
        return ""

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[WARN] GEMINI_API_KEY が未設定です。Gemini プロンプト加工をスキップします。")
        return ""

    text_model = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
    char_name = extract_char_name(record)
    data = build_gemini_prompt(
        record, form, scene=scene, style=style,
        composition=composition, background=background,
    )
    base_prompt = data["prompt"]

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=text_model,
            contents=_user_message(base_prompt, scene, style, composition, background, costume),
            config=genai_types.GenerateContentConfig(
                system_instruction=_system_instruction(char_name, form),
                max_output_tokens=600,
            ),
        )
        result = (response.text or "").strip()
        return result if result else base_prompt
    except Exception as err:
        print(f"[WARN] Gemini プロンプト加工に失敗: {err}")
        return base_prompt


def refine_prompt_dual(
    record: dict,
    form: str,
    scene: str = "",
    style: str = "",
    composition: str = "",
    background: str = "",
    costume: str = "",
) -> dict[str, str | list]:
    """OpenAI + Gemini の両方でプロンプトを加工し、各結果を返す。

    Parameters
    ----------
    costume: 衣装差分の説明（例: '黒いワンピース姿の差分'）。
             空の場合はデフォルト衣装でプロンプトを生成する。

    Returns
    -------
    {
        "openai":      str — Adobe Firefly 用 (OpenAI 加工)
        "gemini":      str — Gemini Imagen 用 (Gemini 加工)
        "base_dalle":  str — DALL-E ベースプロンプト (加工前)
        "base_gemini": str — Gemini ベースプロンプト (加工前)
        "ref_urls":    list[str] — DB 参照画像 URL
        "ref_locals":  list[str] — DB 参照画像ローカルパス
        "costume":     str — 指定衣装差分（デバッグ確認用）
    }
    """
    if costume:
        print(f"[Stage1] 衣装差分指定: {costume}")

    base_dalle = build_dalle_prompt(
        record, form, scene=scene, style=style,
        composition=composition, background=background,
    )
    base_gemini_data = build_gemini_prompt(
        record, form, scene=scene, style=style,
        composition=composition, background=background,
    )
    base_gemini = base_gemini_data["prompt"]

    print("[Stage1] OpenAI (GPT-4o) でプロンプトを加工中...")
    openai_prompt = refine_with_openai(
        record, form, scene=scene, style=style,
        composition=composition, background=background,
        costume=costume,
    )

    print("[Stage1] Gemini でプロンプトを加工中...")
    gemini_prompt = refine_with_gemini(
        record, form, scene=scene, style=style,
        composition=composition, background=background,
        costume=costume,
    )

    return {
        "openai": openai_prompt or base_dalle,
        "gemini": gemini_prompt or base_gemini,
        "base_dalle": base_dalle,
        "base_gemini": base_gemini,
        "ref_urls": base_gemini_data.get("reference_image_urls") or [],
        "ref_locals": base_gemini_data.get("reference_local_paths") or [],
        "costume": costume,
    }
