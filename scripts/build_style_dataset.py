"""
scripts/build_style_dataset.py — コアフォルダ全体の作風傾向データセットビルダー
Copyright © RadianN_kswg — CC BY-NC 4.0

全キャラクターのコアフォルダ参照画像を Gemini Vision で分析し、
ナンバーテールズの「作風共通傾向」をデータセットとして抽出する。

生成されるデータは `_ideas/form_common_datasets/Works_NumberTales.json` に保存され、
`src/utils/dataset.py` の `_build_form_common_dataset_block()` が自動的に読み込んで
プロンプトに組み込む。これにより、全キャラクターの生成時に
「原典イラストの作風傾向」が共通プロンプトとして注入される。

実行方法:
    python scripts/build_style_dataset.py
    python scripts/build_style_dataset.py --form corefolder --max-chars 20 --dry-run
    python scripts/build_style_dataset.py --output _ideas/form_common_datasets/Works_NumberTales.json

必要な環境変数:
    GEMINI_API_KEY  — Gemini Vision 分析に使用
    GEMINI_TEXT_MODEL — テキストモデル (デフォルト: gemini-2.5-flash)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from src.utils import collect_reference_images, get_characters  # noqa: E402

_DEFAULT_OUTPUT = "_ideas/form_common_datasets/Works_NumberTales.json"

# Gemini Vision に渡すシステム指示
_ANALYSIS_SYSTEM = """\
あなたはイラスト作風分析の専門家です。
提供された画像群（ナンバーテールズのキャラクターイラスト）を見て、
複数の画像に共通する作風・画風の傾向を分析してください。

以下の点を具体的に分析してください:
1. 線の太さ・スタイル (太い/細い/フラット/シェーディングあり等)
2. 色彩の傾向 (鮮やか/パステル/落ち着いた/モノトーン等)
3. 背景の傾向 (シンプル/白背景/グラデーション等)
4. 陰影の表現方法 (セル塗り/グラデーション/アニメ塗り等)
5. タッチ・雰囲気 (可愛い系/かっこいい系/デフォルメ等)
6. 構図の傾向 (バストアップ多め/全身/正面向き多め等)

回答は以下のJSON形式で返してください (説明文なし):
{
  "line_style": "<線のスタイル説明>",
  "color_tendency": "<色彩傾向の説明>",
  "background_style": "<背景スタイルの説明>",
  "shading_style": "<陰影表現の説明>",
  "overall_mood": "<全体の雰囲気・タッチ>",
  "composition_tendency": "<構図の傾向>",
  "keywords_en": ["<英語キーワード1>", "<英語キーワード2>", ...],
  "keywords_ja": ["<日本語キーワード1>", "<日本語キーワード2>", ...]
}
"""

_SYNTHESIS_SYSTEM = """\
あなたはイラスト作風データセットの編集者です。
複数のキャラクターの作風分析結果を受け取り、共通する傾向を統合してください。

入力: 複数の分析結果のリスト (JSON 配列)
出力: 統合された作風データセット (以下の JSON 形式)

{
  "preferred_art_style": ["<英語での作風説明1>", "<英語での作風説明2>"],
  "forms": {
    "corefolder": {
      "definition_ja": "<コアフォルダ形態の定義（日本語）>",
      "definition_en": "<corefolder form definition (English)>",
      "surface_description_ja": "<表面・質感の説明（日本語）>",
      "surface_description_en": "<surface texture description (English)>",
      "silhouette_summary_ja": "<シルエット要約（日本語）>",
      "silhouette_summary_en": "<silhouette summary (English)>",
      "required_shape_keywords": ["<必須形状キーワード(英語)>"],
      "disallow_cross_form_keywords": ["<別形態混入禁止キーワード(英語)>"],
      "common_equipment": ["<共通装備(英語)>"],
      "texture_traits": ["<質感特徴(英語)>"],
      "function_traits": ["<機能・振る舞い(英語)>"]
    },
    "humanoid": {
      "definition_ja": "<ヒューマノイド形態の定義（日本語）>",
      "definition_en": "<humanoid form definition (English)>",
      "surface_description_ja": "",
      "surface_description_en": "",
      "silhouette_summary_ja": "<シルエット要約（日本語）>",
      "silhouette_summary_en": "<silhouette summary (English)>",
      "required_shape_keywords": [],
      "disallow_cross_form_keywords": [],
      "common_equipment": [],
      "texture_traits": [],
      "function_traits": []
    }
  },
  "style_analysis_summary": {
    "line_style": "<統合後の線スタイル>",
    "color_tendency": "<統合後の色彩傾向>",
    "overall_mood": "<統合後の全体雰囲気>",
    "keywords_en": ["<代表キーワード(英語)>"],
    "analyzed_character_count": <分析したキャラクター数>,
    "analyzed_form": "<分析した形態>"
  }
}

既存の定義を尊重しつつ、作風分析で得た傾向を preferred_art_style と
style_analysis_summary に反映してください。
説明文なし・JSONのみを返してください。
"""

import re as _re


def _extract_json_from_response(raw: str) -> str:
    """Gemini レスポンスから JSON 部分だけを取り出す。

    Markdown fence (```json ... ``` や ``` ... ```) や
    前後の説明文を除去し、最初の `{` から最後の `}` までを返す。
    """
    # Markdown fence を削除
    raw = _re.sub(r"^```(?:json|JSON)?\s*", "", raw, flags=_re.MULTILINE)
    raw = _re.sub(r"\s*```$", "", raw, flags=_re.MULTILINE).strip()

    # { ... } の範囲を抽出（前後に余分なテキストがある場合の対策）
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start : end + 1]
    return raw


def _analyze_images_with_gemini(
    image_paths: list[str],
    char_num: int,
) -> dict | None:
    """Gemini Vision で参照画像を分析して作風データを返す。"""
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        print("[ERROR] google-genai がインストールされていません。")
        return None

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY が設定されていません。")
        return None

    model = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)

    # 分析用のパーツを構築 (最大 3 枚)
    parts: list[object] = [
        genai_types.Part.from_text(
            text=f"キャラクター #{char_num:03d} のイラスト {len(image_paths[:3])} 枚を分析してください。"
        )
    ]
    for path_str in image_paths[:3]:
        p = Path(path_str)
        if not p.exists():
            continue
        mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
        try:
            parts.append(genai_types.Part.from_bytes(data=p.read_bytes(), mime_type=mime))
        except Exception as err:
            print(f"[WARN] 画像読み込み失敗 {p.name}: {err}")

    if len(parts) <= 1:
        print(f"[WARN] #{char_num:03d}: 読み込める画像がありません。スキップします。")
        return None

    try:
        response = client.models.generate_content(
            model=model,
            contents=parts,
            config=genai_types.GenerateContentConfig(
                system_instruction=_ANALYSIS_SYSTEM,
                max_output_tokens=1500,
            ),
        )
        raw = (response.text or "").strip()
        raw = _extract_json_from_response(raw)
        result = json.loads(raw)
        result["char_num"] = char_num
        return result
    except Exception as err:
        print(f"[WARN] #{char_num:03d} 分析失敗: {err}")
        return None


def _synthesize_style_data(
    analyses: list[dict],
    form: str,
    existing_dataset: dict | None,
) -> dict:
    """複数の分析結果を Gemini でまとめて作風データセットを生成する。"""
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        return _build_fallback_dataset(analyses, form)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _build_fallback_dataset(analyses, form)

    model = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)

    # 既存データを含める
    existing_json = json.dumps(existing_dataset or {}, ensure_ascii=False, indent=2)
    analyses_json = json.dumps(analyses, ensure_ascii=False, indent=2)

    user_message = (
        f"以下は {len(analyses)} キャラクターの {form} 形態イラスト作風分析結果です。\n\n"
        f"【分析結果】\n{analyses_json}\n\n"
        f"【既存のデータセット（更新元）】\n{existing_json}\n\n"
        "上記を統合した作風データセットを生成してください。"
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=user_message,
            config=genai_types.GenerateContentConfig(
                system_instruction=_SYNTHESIS_SYSTEM,
                max_output_tokens=3000,
            ),
        )
        raw = (response.text or "").strip()
        raw = _extract_json_from_response(raw)
        return json.loads(raw)
    except Exception as err:
        print(f"[WARN] データセット統合失敗: {err}. フォールバックデータを使用します。")
        return _build_fallback_dataset(analyses, form)


def _build_fallback_dataset(analyses: list[dict], form: str) -> dict:
    """Gemini 統合失敗時のフォールバック: 分析結果から直接集計する。"""
    all_keywords_en: list[str] = []
    all_moods: list[str] = []
    for a in analyses:
        all_keywords_en.extend(a.get("keywords_en") or [])
        mood = a.get("overall_mood")
        if mood:
            all_moods.append(mood)

    # 上位キーワードを集計
    from collections import Counter
    top_keywords = [k for k, _ in Counter(all_keywords_en).most_common(8)]

    return {
        "preferred_art_style": top_keywords[:4],
        "forms": {
            form: {
                "definition_ja": f"{form}形態の共通作風データ",
                "definition_en": f"Common art style for {form} form",
                "surface_description_ja": "",
                "surface_description_en": "",
                "silhouette_summary_ja": "",
                "silhouette_summary_en": "",
                "required_shape_keywords": top_keywords[4:],
                "disallow_cross_form_keywords": [],
                "common_equipment": [],
                "texture_traits": [],
                "function_traits": [],
            }
        },
        "style_analysis_summary": {
            "keywords_en": top_keywords,
            "overall_mood": all_moods[0] if all_moods else "",
            "analyzed_character_count": len(analyses),
            "analyzed_form": form,
        },
    }


def build_style_dataset(
    form: str = "corefolder",
    work_key: str = "#Works_NumberTales",
    max_chars: int = 30,
    output_path: str = _DEFAULT_OUTPUT,
    dry_run: bool = False,
    sleep_between: float = 1.5,
) -> dict:
    """全キャラクターの参照画像を分析し、作風データセットを生成する。

    Parameters
    ----------
    form:           分析対象の形態
    work_key:       作品キー
    max_chars:      最大分析キャラクター数 (API コスト制限用)
    output_path:    保存先 JSON パス
    dry_run:        True の場合、API 呼び出しをスキップ（参照画像の収集のみ確認）
    sleep_between:  各キャラクター間の待機秒数 (API レート制限対策)

    Returns
    -------
    生成したデータセット辞書
    """
    print(f"\n[StyleDataset] {form} 形態の作風分析を開始します。")
    print(f"[StyleDataset] 最大 {max_chars} キャラクター / dry_run={dry_run}")

    # 既存データセットを読み込む（更新ベースとして使う）
    out_path = Path(output_path)
    existing_dataset: dict | None = None
    if out_path.exists():
        try:
            with out_path.open(encoding="utf-8") as f:
                existing_dataset = json.load(f)
            print(f"[StyleDataset] 既存データセットを読み込みました: {out_path}")
        except Exception:
            pass

    # 全キャラクターの取得
    characters = get_characters()
    work_chars = [
        c for c in characters
        if c.get("work_key") == work_key
    ]
    print(f"[StyleDataset] 対象: {len(work_chars)} キャラクター (work_key={work_key})")

    # 参照画像があるキャラクターのみ抽出
    target_chars: list[dict] = []
    for char in work_chars:
        refs = collect_reference_images(char, form=form)
        if refs["local_paths"]:
            target_chars.append({"record": char, "ref_paths": refs["local_paths"]})

    print(f"[StyleDataset] {form} 参照画像あり: {len(target_chars)} キャラクター")

    if dry_run:
        print("\n[DRY-RUN] 分析対象のキャラクターと参照画像:")
        for i, item in enumerate(target_chars[:max_chars], 1):
            num = item["record"]["data"]["Num"]
            name = item["record"]["data"].get("Name", "?")
            n_refs = len(item["ref_paths"])
            print(f"  {i:02d}. #{num:03d} {name}: {n_refs} 枚")
        return existing_dataset or {}

    # 各キャラクターを分析
    analyses: list[dict] = []
    for i, item in enumerate(target_chars[:max_chars], 1):
        record = item["record"]
        num = record["data"]["Num"]
        name = record["data"].get("Name", "?")
        ref_paths = item["ref_paths"]

        print(f"\n[StyleDataset] [{i}/{min(len(target_chars), max_chars)}] #{num:03d} {name}")
        analysis = _analyze_images_with_gemini(ref_paths, char_num=num)
        if analysis:
            analyses.append(analysis)
            print(f"  mood: {analysis.get('overall_mood', '?')[:60]}")
            print(f"  keywords: {', '.join((analysis.get('keywords_en') or [])[:4])}")

        if i < min(len(target_chars), max_chars):
            time.sleep(sleep_between)

    if not analyses:
        print("[StyleDataset] 分析結果が 0 件でした。終了します。")
        return existing_dataset or {}

    print(f"\n[StyleDataset] {len(analyses)} 件の分析結果を統合中...")
    dataset = _synthesize_style_data(analyses, form, existing_dataset)

    # 保存
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"[StyleDataset] 保存完了: {out_path}")
    print(f"[StyleDataset] preferred_art_style: {dataset.get('preferred_art_style', [])}")

    return dataset


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "ナンバーテールズ全キャラクターのコアフォルダイラストを Gemini Vision で分析し、\n"
            "共通作風データセットを `_ideas/form_common_datasets/Works_NumberTales.json` に保存します。\n"
            "このデータセットは画像生成プロンプトに自動注入され、原典再現性が向上します。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--form", choices=["corefolder", "humanoid"], default="corefolder",
        help="分析する形態 (デフォルト: corefolder)",
    )
    parser.add_argument("--work", default="#Works_NumberTales", help="作品キー")
    parser.add_argument(
        "--max-chars", type=int, default=30,
        help="分析する最大キャラクター数 (デフォルト: 30, API コスト制限用)",
    )
    parser.add_argument(
        "--output", default=_DEFAULT_OUTPUT,
        help=f"出力 JSON パス (デフォルト: {_DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="API を呼ばず、分析対象のキャラクター一覧だけ表示する",
    )
    parser.add_argument(
        "--sleep", type=float, default=1.5,
        help="各キャラクター間の待機秒数 (デフォルト: 1.5)",
    )
    args = parser.parse_args()

    dataset = build_style_dataset(
        form=args.form,
        work_key=args.work,
        max_chars=args.max_chars,
        output_path=args.output,
        dry_run=args.dry_run,
        sleep_between=args.sleep,
    )

    if dataset and not args.dry_run:
        print("\n[完了] 作風データセットを更新しました。")
        print(f"  出力先: {args.output}")
        form_data = (dataset.get("forms") or {}).get(args.form) or {}
        print(f"  definition_en: {form_data.get('definition_en', '(なし)')}")
    elif args.dry_run:
        print("\n[DRY-RUN 完了] 実際の分析は行いませんでした。")


if __name__ == "__main__":
    main()
