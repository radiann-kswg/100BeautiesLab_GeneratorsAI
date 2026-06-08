"""
openai/generate.py — OpenAI DALL-E 3 / GPT-4o を使ったキャラクター画像生成スクリプト
Copyright © RadianN_kswg — CC BY-NC 4.0

使用方法:
    # DALL-E 3 で画像生成
    python -m src.openai.generate --num 57 --form corefolder

    # GPT-4o でプロンプト補助（テキスト出力）
    python -m src.openai.generate --num 57 --mode prompt-assist

保存先:
    実行ごとに ``{OUTPUT_BASE_DIR}/{YYYYMMDD_HHMMSS}_openai_{form}_num{NNN}/`` を作成し、
    過去の生成結果が上書きされないようにします。``--out`` でベースを上書き可能。

必要な環境変数 (.env):
    OPENAI_API_KEY   — OpenAI Platform の API キー
    DALLE_MODEL      — 使用モデル (デフォルト: dall-e-3)
    GPT_MODEL        — 使用モデル (デフォルト: gpt-4o)
    OUTPUT_BASE_DIR  — 出力ベースディレクトリ (デフォルト: output)
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import os
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import (  # noqa: E402
    build_dalle_prompt,
    build_run_output_dir,
    collect_reference_images,
    finalize_run_logs,
    find_character,
    initialize_run_logs,
)


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
    out_dir:  出力ベースディレクトリ (None の場合は環境変数
              ``OUTPUT_BASE_DIR`` → ``OUTPUT_DIR`` → ``output`` を使用)。
              実際の保存先はその配下に
              ``{YYYYMMDD_HHMMSS}_openai_{form}_num{NNN}/`` を切る。
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
    requested_quality = os.environ.get("OPENAI_IMAGE_QUALITY", "standard")
    output_dir = build_run_output_dir(
        provider="openai",
        num=num,
        form=form,
        base_dir=out_dir,
    )
    print(f"[INFO] 出力先: {output_dir}")

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

    log_paths = initialize_run_logs(
        output_dir,
        provider="openai",
        num=num,
        form=form,
        work_key=work_key,
        model=model,
        prompt_text=prompt_text,
        meta={
            "mode": "dalle",
            "size": size,
            "quality_requested": requested_quality,
            "reference_urls": references["urls"],
            "reference_local_paths": references["local_paths"],
            "character_name": record["data"].get("Name", str(num)),
        },
    )
    print(f"[INFO] ログ: {log_paths['meta']}")

    client = OpenAI(api_key=api_key)

    quality = requested_quality
    if model.startswith("gpt-image") and quality == "standard":
        quality = "medium"

    out_path = output_dir / f"num{num:03d}_{form}_dalle.png"

    try:
        response = client.images.generate(
            model=model,
            prompt=prompt_text,
            size=size,
            quality=quality,
            n=1,
        )
    except Exception as err:
        print(f"[ERROR] OpenAI 画像生成 API に失敗: {err}")
        finalize_run_logs(
            output_dir,
            status="failed",
            results=[{"file": str(out_path.name), "status": "failed"}],
            errors=[{"messages": [str(err)]}],
            extra={"quality": quality},
        )
        return None

    first = response.data[0]
    img_b64 = getattr(first, "b64_json", None)
    img_url = getattr(first, "url", None)

    if img_b64:
        out_path.write_bytes(base64.b64decode(img_b64))
    elif img_url:
        urllib.request.urlretrieve(img_url, out_path)
    else:
        print("[WARN] 画像データ (url/b64_json) が空でした。")
        finalize_run_logs(
            output_dir,
            status="failed",
            results=[{"file": str(out_path.name), "status": "failed"}],
            errors=[{"messages": ["画像データ (url/b64_json) が空"]}],
            extra={"quality": quality},
        )
        return None

    print(f"[OK] 保存: {out_path}")
    finalize_run_logs(
        output_dir,
        status="ok",
        results=[{"file": str(out_path.name), "status": "ok"}],
        errors=[],
        extra={"quality": quality},
    )
    return out_path


def assist_prompt_gpt(
    num: int,
    form: str = "corefolder",
    work_key: str = "#Works_NumberTales",
    user_scene: str = "",
    out_dir: str | None = None,
) -> str:
    """GPT-4o でプロンプトの改善提案を得る。

    Parameters
    ----------
    num:        キャラクター番号
    form:       形態
    work_key:   作品キー
    user_scene: 追加で描きたいシーンの説明 (任意)
    out_dir:    出力ベースディレクトリ (省略時は ``OUTPUT_BASE_DIR``)。
                配下に ``{ts}_openai_{form}_num{NNN}_prompt-assist/`` を作り、
                プロンプト・GPT応答・メタを保存する。

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

    output_dir = build_run_output_dir(
        provider="openai",
        num=num,
        form=form,
        base_dir=out_dir,
        suffix="prompt-assist",
    )
    print(f"[INFO] prompt-assist 出力先: {output_dir}")

    log_paths = initialize_run_logs(
        output_dir,
        provider="openai",
        num=num,
        form=form,
        work_key=work_key,
        model=gpt_model,
        prompt_text=base_prompt,
        meta={
            "mode": "prompt-assist",
            "user_scene": user_scene,
            "character_name": char_name,
            "reference_urls": references["urls"][:3],
            "reference_local_paths": references["local_paths"][:3],
        },
    )
    print(f"[INFO] ログ: {log_paths['meta']}")

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
    response_input_parts: list[dict[str, object]] = [{"type": "input_text", "text": user_message}]

    for url in references["urls"][:3]:
        user_content.append({"type": "image_url", "image_url": {"url": url}})
        response_input_parts.append({"type": "input_image", "image_url": url})

    for local_path in references["local_paths"][:3]:
        data_url = _local_image_to_data_url(local_path)
        if data_url:
            user_content.append({"type": "image_url", "image_url": {"url": data_url}})
            response_input_parts.append({"type": "input_image", "image_url": data_url})

    print(
        f"[INFO] prompt-assist 参照画像投入: URL {min(len(references['urls']), 3)}件 / "
        f"ローカル {sum(1 for p in references['local_paths'][:3] if Path(p).exists())}件"
    )

    client = OpenAI(api_key=api_key)
    result = ""

    def _local_fallback_prompt() -> str:
        ref_urls = "\n".join(f"- {u}" for u in references["urls"][:3]) or "- (なし)"
        scene_block = user_scene.strip() or "既存デザインに寄せた自然な立ち姿"
        return (
            "[fallback] OpenAI応答が取得できなかったため、ローカル補助案を返します。\n\n"
            "このキャラクターを描いてください。\n\n"
            "[参照画像URL]\n"
            f"{ref_urls}\n\n"
            f"[形態]\n{form}\n\n"
            "[追加シーン]\n"
            f"{scene_block}\n\n"
            "[重要ルール]\n"
            "- 既存画像の顔立ち・髪型・配色を優先\n"
            "- 耳・尻尾本数・髪色・瞳色は不変\n"
            "- corefolder 指定時は装備要素を維持し、humanoid寄せを避ける\n\n"
            "[ベースプロンプト]\n"
            f"{base_prompt}"
        )

    try:
        resp = client.responses.create(
            model=gpt_model,
            instructions=system_message,
            input=[{"role": "user", "content": response_input_parts}],
            max_output_tokens=1024,
        )
        result = (getattr(resp, "output_text", None) or "").strip()
    except Exception as err:
        print(f"[WARN] responses API 失敗: {err} / chat.completions へフォールバック")

    if not result or result.strip().lower().startswith("i'm sorry"):
        response = client.chat.completions.create(
            model=gpt_model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1024,
        )
        result = (response.choices[0].message.content or "").strip()

    if not result or result.strip().lower().startswith("i'm sorry"):
        result = _local_fallback_prompt()

    response_path = output_dir / "gpt_response.md"
    response_path.write_text(result, encoding="utf-8")
    print(f"[OK] GPT応答を保存: {response_path}")
    finalize_run_logs(
        output_dir,
        status="ok" if result else "failed",
        results=[{"file": response_path.name, "status": "ok" if result else "failed"}],
        errors=[],
    )

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
    parser.add_argument(
        "--out",
        default=None,
        help=(
            "出力ベースディレクトリ (省略時は OUTPUT_BASE_DIR / OUTPUT_DIR / 'output')。"
            "実際は配下に {YYYYMMDD_HHMMSS}_openai_{form}_num{NNN}/ を作って保存します。"
        ),
    )
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
            out_dir=args.out,
        )
        print("\n[GPT-4o プロンプト改善提案]\n")
        print(result)


if __name__ == "__main__":
    main()
