"""
openai/generate.py — OpenAI DALL-E 3 / GPT-4o を使ったキャラクター画像生成スクリプト
Copyright © RadianN_kswg — CC BY-NC 4.0

使用方法:
    # DALL-E 3 で画像生成
    python -m src.openai.generate --num 57 --form corefolder

    # GPT-4o でプロンプト補助（テキスト出力）
    python -m src.openai.generate --num 57 --mode prompt-assist

必要な環境変数 (.env):
    OPENAI_API_KEY  — OpenAI Platform の API キー
    DALLE_MODEL     — 使用モデル (デフォルト: dall-e-3)
    GPT_MODEL       — 使用モデル (デフォルト: gpt-4o)
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import find_character, build_dalle_prompt, collect_reference_images  # noqa: E402


def _local_image_to_data_url(path: str) -> str | None:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    mime, _ = mimetypes.guess_type(str(p))
    if not mime:
        mime = "image/png"
    raw = p.read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def generate_image_dalle(
    num: int,
    form: str = "corefolder",
    work_key: str = "#Works_NumberTales",
    out_dir: str | None = None,
    size: str = "1024x1024",
) -> Path | None:
    """DALL-E 3 でキャラクター画像を生成して保存する。

    Parameters
    ----------
    num:      キャラクター番号
    form:     形態 ("corefolder" または "humanoid")
    work_key: 作品キー
    out_dir:  保存先ディレクトリ
    size:     画像サイズ ("1024x1024" / "1792x1024" / "1024x1792")

    Returns
    -------
    保存したファイルパス (失敗時は None)
    """
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit(
            "[ERROR] openai がインストールされていません。\n"
            "  pip install openai  を実行してください。"
        )

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("[ERROR] OPENAI_API_KEY が設定されていません。.env を確認してください。")

    model = os.environ.get("DALLE_MODEL", "dall-e-3")
    output_dir = Path(out_dir or os.environ.get("OUTPUT_DIR", "output")) / "openai"
    output_dir.mkdir(parents=True, exist_ok=True)

    record = find_character(num, work_key)
    if record is None:
        sys.exit(f"[ERROR] キャラクター #{num} ({work_key}) が見つかりません。")

    prompt_text = build_dalle_prompt(record, form)
    references = collect_reference_images(record, form=form)

    print(f"[INFO] キャラクター: {record['data'].get('Name', num)} / 形態: {form}")
    print(f"[INFO] モデル: {model} / サイズ: {size}")
    print(
        f"[INFO] 参照画像候補: URL {len(references['urls'])}件 / "
        f"ローカル {len(references['local_paths'])}件"
    )

    client = OpenAI(api_key=api_key)

    response = client.images.generate(
        model=model,
        prompt=prompt_text,
        size=size,
        quality="standard",
        n=1,
    )

    img_url = response.data[0].url
    if not img_url:
        print("[WARN] 画像URLが空でした。")
        return None

    import urllib.request
    out_path = output_dir / f"num{num:03d}_{form}_dalle.png"
    urllib.request.urlretrieve(img_url, out_path)
    print(f"[OK] 保存: {out_path}")
    return out_path


def assist_prompt_gpt(
    num: int,
    form: str = "corefolder",
    work_key: str = "#Works_NumberTales",
    user_scene: str = "",
) -> str:
    """GPT-4o でプロンプトの改善提案を得る。

    Parameters
    ----------
    num:        キャラクター番号
    form:       形態
    work_key:   作品キー
    user_scene: 追加で描きたいシーンの説明 (任意)

    Returns
    -------
    GPT-4o からの改善提案テキスト
    """
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("[ERROR] openai がインストールされていません。")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("[ERROR] OPENAI_API_KEY が設定されていません。")

    gpt_model = os.environ.get("GPT_MODEL", "gpt-4o")

    record = find_character(num, work_key)
    if record is None:
        sys.exit(f"[ERROR] キャラクター #{num} ({work_key}) が見つかりません。")

    base_prompt = build_dalle_prompt(record, form)
    char_name = record["data"].get("Name", f"#{num}")
    references = collect_reference_images(record, form=form)

    system_message = (
        "あなたは画像生成プロンプトの専門家です。"
        "ナンバーテールズシリーズのキャラクターデータを元に、"
        "DALL-E 3 向けに最適化された自然文プロンプトを提案してください。"
        "外見不変要素（耳・尻尾の本数・髪色・瞳色）は必ず維持してください。"
        "可能な限り添付された参照画像と作風を合わせてください。"
    )

    user_message = (
        f"キャラクター「{char_name}」の {form} 形態のプロンプトを改善してください。\n\n"
        "添付した創作DBの既存画像を優先参照し、画風と特徴の一貫性を高めてください。\n\n"
        f"[ベースプロンプト]\n{base_prompt}\n"
    )
    if user_scene:
        user_message += f"\n[描きたいシーン・追加要素]\n{user_scene}"

    user_content: list[dict[str, object]] = [{"type": "text", "text": user_message}]

    for url in references["urls"][:3]:
        user_content.append({"type": "image_url", "image_url": {"url": url}})

    for local_path in references["local_paths"][:3]:
        data_url = _local_image_to_data_url(local_path)
        if data_url:
            user_content.append({"type": "image_url", "image_url": {"url": data_url}})

    print(
        f"[INFO] prompt-assist 参照画像投入: URL {min(len(references['urls']), 3)}件 / "
        f"ローカル {sum(1 for p in references['local_paths'][:3] if Path(p).exists())}件"
    )

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=gpt_model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_content},
        ],
        max_tokens=1024,
    )
    result = response.choices[0].message.content or ""
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OpenAI (DALL-E 3 / GPT-4o) でナンバーテールズキャラクター画像を生成・プロンプト補助します。"
    )
    parser.add_argument("--num", type=int, required=True, help="キャラクター番号 (例: 57)")
    parser.add_argument(
        "--form",
        choices=["corefolder", "humanoid"],
        default="corefolder",
        help="生成する形態 (デフォルト: corefolder)",
    )
    parser.add_argument("--work", default="#Works_NumberTales", help="作品キー")
    parser.add_argument("--out", default=None, help="出力ディレクトリ")
    parser.add_argument(
        "--mode",
        choices=["dalle", "prompt-assist"],
        default="dalle",
        help="実行モード: dalle=画像生成, prompt-assist=プロンプト改善提案",
    )
    parser.add_argument(
        "--size",
        choices=["1024x1024", "1792x1024", "1024x1792"],
        default="1024x1024",
        help="DALL-E 3 画像サイズ",
    )
    parser.add_argument("--scene", default="", help="prompt-assist モード用の追加シーン説明")
    args = parser.parse_args()

    if args.mode == "dalle":
        path = generate_image_dalle(
            num=args.num,
            form=args.form,
            work_key=args.work,
            out_dir=args.out,
            size=args.size,
        )
        if path:
            print(f"\n[完了] 画像を生成しました: {path}")
    else:
        result = assist_prompt_gpt(
            num=args.num,
            form=args.form,
            work_key=args.work,
            user_scene=args.scene,
        )
        print("\n[GPT-4o プロンプト改善提案]\n")
        print(result)


if __name__ == "__main__":
    main()
