"""
gemini/generate.py — Google Imagen 3 を使ったキャラクター画像生成スクリプト
Copyright © RadianN_kswg — CC BY-NC 4.0

使用方法:
    python -m src.gemini.generate --num 57 --form corefolder --out output/

必要な環境変数 (.env):
    GEMINI_API_KEY  — Google AI Studio の API キー
    IMAGEN_MODEL    — 使用モデル (デフォルト: imagen-3.0-generate-001)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# プロジェクトルートを sys.path に追加（-m なしで直接実行した場合の対策）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import find_character, build_gemini_prompt  # noqa: E402


def generate_image(
    num: int,
    form: str = "corefolder",
    work_key: str = "#Works_NumberTales",
    out_dir: str | None = None,
    count: int = 1,
) -> list[Path]:
    """Imagen 3 でキャラクター画像を生成して保存する。

    Parameters
    ----------
    num:      キャラクター番号 (例: 57)
    form:     形態 ("corefolder" または "humanoid")
    work_key: 作品キー
    out_dir:  保存先ディレクトリ (None の場合は環境変数 OUTPUT_DIR を使用)
    count:    生成枚数 (1–4)

    Returns
    -------
    保存したファイルパスのリスト
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.exit(
            "[ERROR] google-genai がインストールされていません。\n"
            "  pip install google-genai  を実行してください。"
        )

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("[ERROR] GEMINI_API_KEY が設定されていません。.env を確認してください。")

    model = os.environ.get("IMAGEN_MODEL", "imagen-3.0-generate-001")
    output_dir = Path(out_dir or os.environ.get("OUTPUT_DIR", "output")) / "gemini"
    output_dir.mkdir(parents=True, exist_ok=True)

    # キャラクターデータ取得
    record = find_character(num, work_key)
    if record is None:
        sys.exit(f"[ERROR] キャラクター #{num} ({work_key}) が見つかりません。")

    data = build_gemini_prompt(record, form)
    prompt_text = data["prompt"]
    ref_url = data["reference_image_url"]
    ref_urls = data.get("reference_image_urls") or []
    ref_locals = data.get("reference_local_paths") or []

    print(f"[INFO] キャラクター: {record['data'].get('Name', num)} / 形態: {form}")
    print(f"[INFO] 参照画像: {ref_url or '(なし)'}")
    print(f"[INFO] 参照画像候補: URL {len(ref_urls)}件 / ローカル {len(ref_locals)}件")
    print(f"[INFO] モデル: {model} / 生成枚数: {count}")

    client = genai.Client(api_key=api_key)

    saved: list[Path] = []
    for i in range(count):
        response = client.models.generate_images(
            model=model,
            prompt=prompt_text,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
                safety_filter_level="block_low_and_above",
            ),
        )

        if not response.generated_images:
            print(f"[WARN] 画像 {i + 1} の生成結果が空でした。スキップします。")
            continue

        image_data = response.generated_images[0].image.image_bytes
        out_path = output_dir / f"num{num:03d}_{form}_{i + 1:02d}.png"
        out_path.write_bytes(image_data)
        print(f"[OK] 保存: {out_path}")
        saved.append(out_path)

    return saved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Imagen 3 でナンバーテールズキャラクターの画像を生成します。"
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
    parser.add_argument("--count", type=int, default=1, choices=range(1, 5), help="生成枚数 (1-4)")
    args = parser.parse_args()

    paths = generate_image(
        num=args.num,
        form=args.form,
        work_key=args.work,
        out_dir=args.out,
        count=args.count,
    )
    if paths:
        print(f"\n[完了] {len(paths)} 枚の画像を生成しました。")
    else:
        print("\n[完了] 画像は生成されませんでした。")


if __name__ == "__main__":
    main()
