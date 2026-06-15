"""
pipeline/natural_parser.py — 自然文・短編ストーリーからパイプラインパラメータを抽出
Copyright © RadianN_kswg — CC BY-NC 4.0

「コアフォルダ姿の25(フィズ)がチョコレートを咥えている絵を生成してほしい」のような
自然文や短編ストーリーから、画像生成パイプラインのパラメータを抽出する。

GPT-4o を一次パーサーとして使用し、Gemini をフォールバックとして用いる。
複数キャラクター指定にも対応。

使用方法:
    from src.pipeline.natural_parser import parse_generation_request

    params_list = parse_generation_request(
        "コアフォルダ姿の25(フィズ)がチョコレートを咥えている絵を生成してほしい"
    )
    # → [{"num": 25, "form": "corefolder", "scene": "チョコレートを咥えているシーン", ...}]

CLI から呼ぶ場合:
    python -m src.pipeline.natural_parser "コアフォルダ姿の25(フィズ)が..."
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

_SYSTEM_PROMPT = """\
あなたは「ナンバーテールズ」キャラクターイラスト生成システムのパラメータ抽出AIです。
ユーザーの自然文・短編ストーリーから、画像生成パイプラインに渡すパラメータを抽出してください。

ナンバーテールズのキャラクターは1〜100番の番号を持つ妖獣型ポータブルヒューマノイドです。
「57(イズナ)」「25(フィズ)」「22(フジ)」のように「番号(名前)」形式で表記されることが多いです。
番号のみ・名前のみの記述も可能です（例: 「フィズ」→25、「イズナ」→57 等、文脈で特定してください）。

以下のJSON形式で返してください（説明文なし、JSONのみ）:
{"characters": [
  {
    "num": <キャラクター番号 (整数, 1〜100)>,
    "form": <"corefolder" または "humanoid">,
    "scene": <シーン・ポーズの説明（できるだけ日本語で、空なら ""）>,
    "style": <作風ヒント（空なら ""）>,
    "composition": <構図ヒント（空なら ""）>,
    "background": <背景ヒント（空なら ""）>,
    "work_key": "#Works_NumberTales"
  }
]}

【形態判定ルール】
- 「コアフォルダ姿/形態」「CF姿」「コアフォルダ」→ "corefolder"
- 「ヒューマノイド姿/形態」「人型」「HM姿」→ "humanoid"
- 明記なし → "corefolder"（デフォルト）

【シーン抽出のコツ】
- 「〜している」「〜のシーン」「〜の絵」のような動作・状況記述をsceneに入れる
- 場所や雰囲気は background に移す（例: 「図書館で」→ background: "図書館"）
- ショートストーリーの場合、複数キャラクターが登場すれば複数エントリを返す

【重要】
- 抽出できないキャラ番号 (範囲外・曖昧) はスキップしてください
- 複数キャラクターが明示されている場合は複数エントリを返してください
"""

_COREFOLDER_WORDS = ("コアフォルダ", "CF姿", "CF形態", "corefolder", "core folder")
_HUMANOID_WORDS = ("ヒューマノイド", "人型", "HM姿", "HM形態", "humanoid")

# キャラ番号を「数字(名前)」「数字番」「#数字」などのパターンで抽出
_NUM_PATTERNS = [
    re.compile(r'(?<!\d)(\d{1,2})(?:\s*[（(]\s*[\w぀-鿿]+\s*[)）])'),  # 57(イズナ)
    re.compile(r'(?<!\d)(\d{1,2})\s*番(?:機|号|目)?'),  # 57番機
    re.compile(r'#\s*(\d{1,2})(?!\d)'),  # #57
]


def _detect_form(text: str) -> str:
    lower = text.lower()
    for word in _HUMANOID_WORDS:
        if word.lower() in lower:
            return "humanoid"
    for word in _COREFOLDER_WORDS:
        if word.lower() in lower:
            return "corefolder"
    return "corefolder"


def _strip_markdown_json(raw: str) -> str:
    raw = re.sub(r"^```(?:json|JSON)?\s*", "", raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE).strip()
    # 前後に余分なテキストがある場合、最初の [ or { から最後の ] or } まで抽出
    for open_c, close_c in (("[", "]"), ("{", "}")):
        start = raw.find(open_c)
        end = raw.rfind(close_c)
        if start != -1 and end != -1 and end > start:
            return raw[start : end + 1]
    return raw


def _parse_with_openai(text: str) -> list[dict] | None:
    try:
        from openai import OpenAI
    except ImportError:
        return None

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    model = os.environ.get("GPT_MODEL", "gpt-4o")
    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            max_tokens=1000,
        )
        raw = _strip_markdown_json(response.choices[0].message.content or "")
        parsed = json.loads(raw)
        return _extract_characters_list(parsed)
    except Exception as err:
        print(f"[WARN] OpenAI natural parse に失敗: {err}")
        return None


def _parse_with_gemini(text: str) -> list[dict] | None:
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        return None

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    model = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=text,
            config=genai_types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                max_output_tokens=1000,
            ),
        )
        raw = _strip_markdown_json(response.text or "")
        parsed = json.loads(raw)
        return _extract_characters_list(parsed)
    except Exception as err:
        print(f"[WARN] Gemini natural parse に失敗: {err}")
        return None


def _extract_characters_list(parsed: object) -> list[dict] | None:
    """GPT/Gemini の返却値から characters リストを取り出す。"""
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        for key in ("characters", "result", "results", "items"):
            if isinstance(parsed.get(key), list):
                return parsed[key]
        # 値がリストである最初のキーを使う
        for v in parsed.values():
            if isinstance(v, list):
                return v
    return None


def _simple_extract(text: str) -> list[dict]:
    """LLM なしで正規表現による最低限の抽出（緊急フォールバック）。"""
    found_nums: list[int] = []
    for pattern in _NUM_PATTERNS:
        for m in pattern.finditer(text):
            n = int(m.group(1))
            if 1 <= n <= 100 and n not in found_nums:
                found_nums.append(n)

    if not found_nums:
        return []

    form = _detect_form(text)
    scene = text.strip()[:120]
    return [
        {
            "num": n,
            "form": form,
            "scene": scene,
            "style": "",
            "composition": "",
            "background": "",
            "work_key": "#Works_NumberTales",
        }
        for n in found_nums
    ]


def _normalize_entry(entry: object) -> dict | None:
    if not isinstance(entry, dict):
        return None
    try:
        num = int(entry.get("num", 0))
    except (ValueError, TypeError):
        return None
    if not (1 <= num <= 100):
        return None

    raw_form = str(entry.get("form", "")).strip().lower()
    form = "humanoid" if "humanoid" in raw_form else "corefolder"

    return {
        "num": num,
        "form": form,
        "scene": str(entry.get("scene", "")).strip(),
        "style": str(entry.get("style", "")).strip(),
        "composition": str(entry.get("composition", "")).strip(),
        "background": str(entry.get("background", "")).strip(),
        "work_key": str(entry.get("work_key", "") or "#Works_NumberTales").strip()
                    or "#Works_NumberTales",
    }


def parse_generation_request(
    text: str,
    prefer_gemini: bool = False,
) -> list[dict]:
    """自然文・短編ストーリーからパイプラインパラメータのリストを抽出する。

    Parameters
    ----------
    text:           入力テキスト（日本語 or 英語）
    prefer_gemini:  True の場合、OpenAI より先に Gemini を試みる

    Returns
    -------
    [{"num": int, "form": str, "scene": str, "style": str,
      "composition": str, "background": str, "work_key": str}, ...]
    各フィールドは正規化・バリデーション済み。
    """
    snippet = text[:80] + ("..." if len(text) > 80 else "")
    print(f"[NaturalParser] 入力: {snippet}")

    if prefer_gemini:
        raw = _parse_with_gemini(text) or _parse_with_openai(text)
    else:
        raw = _parse_with_openai(text) or _parse_with_gemini(text)

    if raw is None:
        print("[NaturalParser] LLM パース失敗。正規表現フォールバックを使用します。")
        raw = _simple_extract(text)

    results: list[dict] = []
    for entry in (raw or []):
        normalized = _normalize_entry(entry)
        if normalized:
            results.append(normalized)

    if not results:
        print("[NaturalParser] キャラクターパラメータを抽出できませんでした。")
    else:
        print(f"[NaturalParser] 抽出完了: {len(results)} 件")
        for r in results:
            scene_preview = r["scene"][:40] + ("..." if len(r["scene"]) > 40 else "")
            print(f"  -> #{r['num']:03d} / {r['form']} / シーン: {scene_preview}")

    return results


def main() -> None:
    if len(sys.argv) < 2:
        print("使用方法: python -m src.pipeline.natural_parser <自然文テキスト>")
        print('例: python -m src.pipeline.natural_parser "コアフォルダ姿の25(フィズ)がチョコレートを咥えている絵"')
        sys.exit(1)

    text = " ".join(sys.argv[1:])
    results = parse_generation_request(text)
    if results:
        print("\n[結果 JSON]")
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("[結果] 抽出できませんでした。")
        sys.exit(1)


if __name__ == "__main__":
    main()
