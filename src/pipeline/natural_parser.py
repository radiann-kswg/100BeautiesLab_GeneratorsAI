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

# ──────────────────────────────────────────────────────────────
# DB パス
# ──────────────────────────────────────────────────────────────
_DB_PRIMARY_PATH = (
    _PROJECT_ROOT / "_creations-ai" / "creations-db" / "data"
    / "Works_NumberTales" / "DataBases" / "db_Primary.json"
)
_MANIFEST_PATH = _PROJECT_ROOT / "_creations-ai" / "ai-dataset" / "manifest.jsonl"

# ──────────────────────────────────────────────────────────────
# システムプロンプト (ベース)
# ──────────────────────────────────────────────────────────────
_SYSTEM_PROMPT_BASE = """\
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

# ──────────────────────────────────────────────────────────────
# 名前 → Num DB 引き当て
# ──────────────────────────────────────────────────────────────
_NAME_LOOKUP_CACHE: dict[str, str] | None = None
_CHARS_WITH_IMAGES_CACHE: list[dict] | None = None


def _extract_name_aliases(name_field: str) -> list[str]:
    """Name / SPCodeName フィールドから検索可能な別名を抽出する。

    "バイナ\\n2(ツギ)"  → ["バイナ", "ツギ"]
    "22(フジ)"         → ["フジ"]
    "バイナリ,二進"     → ["バイナリ", "二進"]
    """
    aliases: list[str] = []
    for part in re.split(r'[\n,、]', name_field):
        part = part.strip()
        if not part:
            continue
        # 括弧内の名前を抽出（先頭が非数字のものだけ）
        for m in re.finditer(r'[（(]([^\d）)][^）)]*)[)）]', part):
            inner = m.group(1).strip()
            if inner and len(inner) >= 2:
                aliases.append(inner)
        # 括弧・先頭番号を除いた純名称部分
        bare = re.sub(r'^\d[\d\-]*\s*', '', part).strip()
        bare = re.sub(r'[（(][^）)]*[)）]', '', bare).strip()
        if bare and len(bare) >= 2 and not bare.isdigit():
            aliases.append(bare)
    return list(dict.fromkeys(aliases))  # dedup, preserve order


def _build_name_lookup() -> dict[str, str]:
    """DB から「名前エイリアス → Num文字列」の辞書を構築する（キャッシュ付き）。

    Returns: e.g. {"バイナ": "2-alt", "フジ": "22", "イズナ": "57", ...}
    """
    global _NAME_LOOKUP_CACHE
    if _NAME_LOOKUP_CACHE is not None:
        return _NAME_LOOKUP_CACHE

    lookup: dict[str, str] = {}
    if not _DB_PRIMARY_PATH.exists():
        _NAME_LOOKUP_CACHE = lookup
        return lookup

    try:
        records = json.loads(_DB_PRIMARY_PATH.read_bytes().decode("utf-8"))
        if isinstance(records, dict):
            records = records.get("records", [])
        for r in records:
            num = r.get("Num")
            if num is None:
                continue
            num_str = str(num)
            for field in ("Name", "SPCodeName"):
                val = r.get(field) or ""
                for alias in _extract_name_aliases(val):
                    if alias not in lookup:
                        lookup[alias] = num_str
    except Exception as err:
        print(f"[WARN] キャラクター名辞書の構築に失敗: {err}")

    _NAME_LOOKUP_CACHE = lookup
    return lookup


def _find_name_matches(text: str, lookup: dict[str, str]) -> dict[str, str]:
    """テキスト中に含まれる既知のキャラ名を検索する。

    同じ Num への複数マッチは最長エイリアスを採用。
    Returns: {alias: num_str}
    """
    matched_per_num: dict[str, str] = {}  # num_str → alias (最長を保持)
    for alias in sorted(lookup, key=len, reverse=True):
        if len(alias) < 2:
            continue
        if alias in text:
            num_str = lookup[alias]
            # 同一 num_str に対して、より長いエイリアスを優先
            existing = matched_per_num.get(num_str, "")
            if len(alias) > len(existing):
                matched_per_num[num_str] = alias
    return {alias: num_str for num_str, alias in matched_per_num.items()}


def _get_chars_with_images() -> list[dict]:
    """manifest から画像を持つキャラクター一覧を返す (キャッシュ付き)。

    Returns: [{"Num": str, "Name": str}, ...] (Num の数値順)
    """
    global _CHARS_WITH_IMAGES_CACHE
    if _CHARS_WITH_IMAGES_CACHE is not None:
        return _CHARS_WITH_IMAGES_CACHE

    chars: list[dict] = []
    if not _MANIFEST_PATH.exists():
        _CHARS_WITH_IMAGES_CACHE = chars
        return chars

    try:
        for line in _MANIFEST_PATH.read_bytes().decode("utf-8").splitlines():
            r = json.loads(line)
            if r.get("_type") != "character":
                continue
            if not r.get("images"):
                continue
            d = r.get("data") or {}
            num = d.get("Num")
            name = d.get("Name_JP") or d.get("Name") or ""
            name_en = d.get("Name_EN") or ""
            if num is not None:
                chars.append({"Num": str(num), "Name": name, "Name_EN": name_en})
    except Exception as err:
        print(f"[WARN] 画像ありキャラクター一覧の取得に失敗: {err}")

    # Num が整数のものを先に、文字列 ID を後に並べる
    def _sort_key(c: dict) -> tuple[int, str]:
        try:
            return (0, f"{int(c['Num']):05d}")
        except ValueError:
            return (1, c["Num"])

    chars.sort(key=_sort_key)
    _CHARS_WITH_IMAGES_CACHE = chars
    return chars


def _confirm_character_dialog(name_hint: str, chars: list[dict]) -> str | None:
    """不明 / 未対応のキャラクター名をユーザーに確認する（TTY のみインタラクティブ）。

    Returns: 選択された Num 文字列、またはスキップ時は None
    """
    print(f"\n[確認] '{name_hint}' の対象キャラクターを特定できませんでした。")
    if not chars:
        print("  候補なし。スキップします。")
        return None

    # Num が 1〜100 の整数で画像ありのものだけ表示 (最大 30 件)
    int_chars = [
        c for c in chars
        if str(c["Num"]).isdigit() and 1 <= int(c["Num"]) <= 100
    ][:30]
    if not int_chars:
        print("  画像ありキャラクターが見つかりません。スキップします。")
        return None

    print("  画像が存在するキャラクターの中から選択してください:")
    for i, c in enumerate(int_chars, 1):
        name_jp = (c.get("Name_JP") or c.get("Name") or "").strip()
        name_en = (c.get("Name_EN") or "").strip()
        name_disp = f"{name_jp} / {name_en}" if name_jp and name_en else name_en or name_jp
        line = f"    {i:2d}. #{int(c['Num']):>3}  {name_disp}"
        try:
            print(line)
        except UnicodeEncodeError:
            enc = sys.stdout.encoding or "utf-8"
            print(line.encode(enc, errors="replace").decode(enc))
    print("     0. スキップ（このキャラクターを除外）")

    if not sys.stdin.isatty():
        print("  [非インタラクティブ] 自動スキップします。")
        return None

    try:
        raw = input("  番号を入力 > ").strip()
        idx = int(raw)
        if idx == 0:
            return None
        if 1 <= idx <= len(int_chars):
            selected = int_chars[idx - 1]
            sel_jp = (selected.get("Name_JP") or selected.get("Name") or "").strip()
            sel_en = (selected.get("Name_EN") or "").strip()
            sel_name = f"{sel_jp} / {sel_en}" if sel_jp and sel_en else sel_en or sel_jp
            sel_line = f"  選択: #{selected['Num']} {sel_name}"
            try:
                print(sel_line)
            except UnicodeEncodeError:
                enc = sys.stdout.encoding or "utf-8"
                print(sel_line.encode(enc, errors="replace").decode(enc))
            return selected["Num"]
    except (ValueError, KeyboardInterrupt, EOFError):
        pass

    print("  スキップします。")
    return None


# ──────────────────────────────────────────────────────────────
# システムプロンプト構築（名前ヒント注入）
# ──────────────────────────────────────────────────────────────

def _build_system_prompt(integer_name_hints: dict[str, str] | None = None) -> str:
    """システムプロンプトを構築する。integer_name_hints がある場合は優先マッピングを注入する。

    integer_name_hints: {alias: num_str (整数のみ)} e.g. {"ハツカ": "20", "フジ": "22"}
    """
    if not integer_name_hints:
        return _SYSTEM_PROMPT_BASE

    lines = [
        _SYSTEM_PROMPT_BASE,
        "\n[重要: テキスト内で確認されたキャラクター名と番号の対応 — 必ずこれを使用してください]",
    ]
    for alias, num_str in integer_name_hints.items():
        lines.append(f'- "{alias}" → num: {num_str}')

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# LLM パーサー
# ──────────────────────────────────────────────────────────────

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
    for open_c, close_c in (("[", "]"), ("{", "}")):
        start = raw.find(open_c)
        end = raw.rfind(close_c)
        if start != -1 and end != -1 and end > start:
            return raw[start : end + 1]
    return raw


def _parse_with_openai(text: str, system_prompt: str) -> list[dict] | None:
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
                {"role": "system", "content": system_prompt},
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


def _parse_with_gemini(text: str, system_prompt: str) -> list[dict] | None:
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
                system_instruction=system_prompt,
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
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        for key in ("characters", "result", "results", "items"):
            if isinstance(parsed.get(key), list):
                return parsed[key]
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


def _correct_llm_results(
    raw: list[dict],
    integer_hints: dict[str, str],
) -> list[dict]:
    """LLM 結果の num が name lookup の解決結果と食い違う場合に修正する。

    integer_hints: {alias: num_str (整数)} — テキスト内で確認されたマッピング
    """
    if not integer_hints:
        return raw

    # 期待される num_str のセット
    expected: dict[int, str] = {int(ns): alias for alias, ns in integer_hints.items() if ns.isdigit()}
    actual_nums = {int(e.get("num", 0)) for e in raw if isinstance(e.get("num"), (int, float))}

    corrected = []
    for entry in raw:
        corrected.append(entry)

    # 期待される num が LLM に含まれていなければ追加 (form はテキストから推定済み)
    for expected_num, alias in expected.items():
        if expected_num not in actual_nums:
            print(f"  [NameCorrect] '{alias}' → #{expected_num:03d} を LLM 結果に追加")
            corrected.append({
                "num": expected_num,
                "form": "corefolder",  # 後で form 修正ロジックに任せる
                "scene": "",
                "style": "", "composition": "", "background": "",
                "work_key": "#Works_NumberTales",
            })

    return corrected


# ──────────────────────────────────────────────────────────────
# メイン
# ──────────────────────────────────────────────────────────────

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

    # ── 名前引き当て ──
    lookup = _build_name_lookup()
    name_matches = _find_name_matches(text, lookup)  # {alias: num_str}

    # 整数 ID と特殊 ID (2-alt 等) に分類
    integer_hints: dict[str, str] = {}   # {alias: num_str}  — LLM プロンプトに注入
    special_ids: dict[str, str] = {}     # {alias: num_str}  — ダイアログ処理
    for alias, num_str in name_matches.items():
        if num_str.isdigit() and 1 <= int(num_str) <= 100:
            integer_hints[alias] = num_str
        else:
            special_ids[alias] = num_str

    if integer_hints:
        print(f"[NaturalParser] 名前引き当て (整数ID): "
              + ", ".join(f'"{a}"→#{ns}' for a, ns in integer_hints.items()))
    if special_ids:
        print(f"[NaturalParser] 名前引き当て (特殊ID): "
              + ", ".join(f'"{a}"→{ns}' for a, ns in special_ids.items()))

    # ── 特殊 ID の処理: 文字列 num のままパイプラインへ直接渡す ──
    extra_from_special: list[dict] = []
    for alias, num_str in special_ids.items():
        form = _detect_form_for_alias(text, alias)
        print(f"[NaturalParser] '{alias}' → Num={num_str!r} / {form} をパイプラインへ追加します。")
        extra_from_special.append({
            "num": num_str,
            "form": form,
            "scene": "",
            "style": "", "composition": "", "background": "",
            "work_key": "#Works_NumberTales",
        })

    # ── LLM パース (名前ヒントを注入) ──
    system_prompt = _build_system_prompt(integer_hints or None)

    if prefer_gemini:
        raw = _parse_with_gemini(text, system_prompt) or _parse_with_openai(text, system_prompt)
    else:
        raw = _parse_with_openai(text, system_prompt) or _parse_with_gemini(text, system_prompt)

    if raw is None:
        print("[NaturalParser] LLM パース失敗。正規表現フォールバックを使用します。")
        raw = _simple_extract(text)

    # ── LLM 結果の名前整合性チェック ──
    raw = _correct_llm_results(raw or [], integer_hints)

    # ── 正規化 ──
    results: list[dict] = []
    seen_nums: set[int | str] = set()
    for entry in raw:
        normalized = _normalize_entry(entry)
        if normalized and normalized["num"] not in seen_nums:
            results.append(normalized)
            seen_nums.add(normalized["num"])

    # 特殊IDキャラを追加（重複チェック）
    for entry in extra_from_special:
        if entry["num"] not in seen_nums:
            results.append(entry)
            seen_nums.add(entry["num"])

    # ── 未解決名前のダイアログ (DB に存在しない名前が疑われる場合) ──
    # 数値的に特定できず name_matches にも含まれないキャラクターが
    # LLM によって hallucinate された可能性を検出し、ユーザーに確認する。
    if integer_hints:
        expected_nums = {int(ns) for ns in integer_hints.values()}
        actual_nums = {r["num"] for r in results}
        missing = expected_nums - actual_nums
        if missing:
            for num in missing:
                alias = next((a for a, ns in integer_hints.items() if int(ns) == num), str(num))
                print(f"[NaturalParser] '{alias}' (#{num:03d}) が結果に含まれていません。追加します。")
                form = _detect_form_for_alias(text, alias)
                results.append({
                    "num": num,
                    "form": form,
                    "scene": "",
                    "style": "", "composition": "", "background": "",
                    "work_key": "#Works_NumberTales",
                })

    if not results:
        print("[NaturalParser] キャラクターパラメータを抽出できませんでした。")
    else:
        print(f"[NaturalParser] 抽出完了: {len(results)} 件")
        for r in results:
            scene_preview = r["scene"][:40] + ("..." if len(r["scene"]) > 40 else "")
            num_d = f"{r['num']:03d}" if isinstance(r["num"], int) else r["num"]
            print(f"  -> #{num_d} / {r['form']} / シーン: {scene_preview}")

    return results


def _detect_form_for_alias(text: str, alias: str) -> str:
    """テキスト中でエイリアス周辺の形態を判定する。

    「コアフォルダ姿のバイナ」→ "corefolder"
    「ヒューマノイド姿のバイナ」→ "humanoid"

    前方優先: エイリアス前の 25 文字を先にチェックし、そこで確定しなければ
    直後 5 文字のみを補助的に参照する。隣接キャラの形態記述を誤検知しにくい。
    """
    idx = text.find(alias)
    if idx == -1:
        return _detect_form(text)

    before = text[max(0, idx - 25): idx]
    lower_before = before.lower()
    for word in _HUMANOID_WORDS:
        if word.lower() in lower_before:
            return "humanoid"
    for word in _COREFOLDER_WORDS:
        if word.lower() in lower_before:
            return "corefolder"

    # 前方で確定しなければ後方 5 文字のみ（隣接キャラの記述を拾わないよう短く）
    after = text[idx + len(alias): idx + len(alias) + 5]
    return _detect_form(after)


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
