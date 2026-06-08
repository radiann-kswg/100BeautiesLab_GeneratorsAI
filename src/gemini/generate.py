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
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# プロジェクトルートを sys.path に追加（-m なしで直接実行した場合の対策）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import find_character, build_gemini_prompt  # noqa: E402


def _guess_mime_type(path_or_url: str) -> str:
    mime, _ = mimetypes.guess_type(path_or_url)
    return mime or "image/png"


def _build_reference_parts(
    types_module,
    ref_urls: list[str],
    ref_local_paths: list[str],
    limit: int = 4,
) -> list[Any]:
    parts: list[Any] = []

    for path in ref_local_paths:
        p = Path(path)
        if not p.exists() or not p.is_file():
            continue
        parts.append(
            types_module.Part.from_bytes(data=p.read_bytes(), mime_type=_guess_mime_type(str(p)))
        )
        if len(parts) >= limit:
            return parts

    for url in ref_urls:
        parts.append(
            types_module.Part.from_uri(file_uri=url, mime_type=_guess_mime_type(url))
        )
        if len(parts) >= limit:
            break

    return parts


def _extract_generated_image_bytes(response: object) -> list[bytes]:
    candidates = getattr(response, "candidates", None) or []
    out: list[bytes] = []

    for cand in candidates:
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            data = getattr(inline_data, "data", None)
            if isinstance(data, (bytes, bytearray)) and data:
                out.append(bytes(data))

    if out:
        return out

    generated_images = getattr(response, "generated_images", None) or []
    for item in generated_images:
        image = getattr(item, "image", None)
        image_bytes = getattr(image, "image_bytes", None)
        if isinstance(image_bytes, (bytes, bytearray)) and image_bytes:
            out.append(bytes(image_bytes))

    return out


def _normalize_generate_content_model_name(model_name: str) -> str:
    return model_name if model_name.startswith("models/") else f"models/{model_name}"


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
    reference_model = os.environ.get("GEMINI_REFERENCE_MODEL", "models/gemini-3.1-flash-image")
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
    ref_parts = _build_reference_parts(types, ref_urls, ref_locals, limit=4)
    use_reference_input = bool(ref_parts)
    multimodal_model = model
    if use_reference_input and model.startswith("imagen"):
        multimodal_model = reference_model
    if use_reference_input:
        multimodal_model = _normalize_generate_content_model_name(multimodal_model)
        print(
            f"[INFO] 参照入力モード: {multimodal_model} を使用 "
            f"(IMAGEN_MODEL={model} から自動切替)"
        )

    saved: list[Path] = []
    for i in range(count):
        image_data: bytes | None = None

        if use_reference_input:
            try:
                response = client.models.generate_content(
                    model=multimodal_model,
                    contents=[types.Part.from_text(text=prompt_text), *ref_parts],
                    config=types.GenerateContentConfig(
                        response_modalities=[types.Modality.IMAGE],
                        image_config=types.ImageConfig(aspect_ratio="1:1"),
                    ),
                )
                generated = _extract_generated_image_bytes(response)
                if generated:
                    image_data = generated[0]
                else:
                    print(
                        f"[WARN] 画像 {i + 1}: 参照入力モードの生成結果が空でした。"
                        "通常生成へフォールバックします。"
                    )
            except Exception as err:
                print(
                    f"[WARN] 画像 {i + 1}: 参照入力モードに失敗しました ({err})。"
                    "通常生成へフォールバックします。"
                )

        if image_data is None:
            response = client.models.generate_images(
                model=model,
                prompt=prompt_text,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="1:1",
                    safety_filter_level=types.SafetyFilterLevel.BLOCK_LOW_AND_ABOVE,
                ),
            )

            generated = _extract_generated_image_bytes(response)
            if generated:
                image_data = generated[0]
            else:
                print(f"[WARN] 画像 {i + 1} の生成結果が空でした。スキップします。")
                continue

        out_path = output_dir / f"num{num:03d}_{form}_{i + 1:02d}.png"
        if image_data is None:
            print(f"[WARN] 画像 {i + 1}: 画像データが取得できませんでした。スキップします。")
            continue
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
