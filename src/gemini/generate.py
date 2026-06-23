"""
gemini/generate.py — Google Imagen 3 を使ったキャラクター画像生成スクリプト
Copyright © RadianN_kswg — CC BY-NC 4.0

使用方法:
    python -m src.gemini.generate --num 57 --form corefolder

保存先:
    実行ごとに ``{OUTPUT_BASE_DIR}/{YYYYMMDD_HHMMSS}_gemini_{form}_num{NNN}/`` を作成し、
    過去の生成結果が上書きされないようにします。``--out`` でベースを上書き可能。

必要な環境変数 (.env):
    GEMINI_API_KEY       — Google AI Studio の API キー
    IMAGEN_MODEL         — 使用モデル (デフォルト: imagen-4.0-generate-001)
    GEMINI_IMAGE_SLEEP   — 複数枚生成時の待機秒 (デフォルト: 6)
    OUTPUT_BASE_DIR      — 出力ベースディレクトリ (デフォルト: output)
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

from dotenv import load_dotenv

load_dotenv()

# プロジェクトルートを sys.path に追加（-m なしで直接実行した場合の対策）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import (  # noqa: E402
    build_gemini_prompt,
    build_run_output_dir,
    collect_record_capabilities,
    finalize_run_logs,
    find_character,
    initialize_run_logs,
    next_iteration_label,
    parse_revisions,
    resolve_iterate_source,
    save_image_bytes,
    write_run_meta,
)


# Imagen フォールバックモデルチェーン (先頭から順に試す)
# 注: Gemini API では imagen-3.0-* は廃止済み。現行は imagen-4.0-* のみ利用可。
_IMAGEN_FALLBACK_MODELS = [
    "imagen-4.0-generate-001",
    "imagen-4.0-fast-generate-001",
]


def _is_rate_limit(err: Exception) -> bool:
    s = str(err)
    return "429" in s or "RESOURCE_EXHAUSTED" in s


def _is_not_found(err: Exception) -> bool:
    s = str(err)
    return "404" in s or "NOT_FOUND" in s


def _generate_content_with_retry(client, types, model, prompt_text, ref_parts,
                                  max_retries: int = 4, base_delay: float = 30.0):
    """429 リトライ付き generate_content (参照入力モード)。
    Returns (response, error) のタプル。"""
    delay = base_delay
    for attempt in range(max_retries + 1):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=[types.Part.from_text(text=prompt_text), *ref_parts],
                config=types.GenerateContentConfig(
                    response_modalities=[types.Modality.IMAGE],
                    image_config=types.ImageConfig(aspect_ratio="1:1"),
                ),
            )
            return resp, None
        except Exception as err:
            if _is_rate_limit(err) and attempt < max_retries:
                print(f"[WARN] 参照入力モード 429 超過。{delay:.0f}秒後にリトライ ({attempt + 1}/{max_retries})...")
                time.sleep(delay)
                delay *= 2
            else:
                return None, err
    return None, Exception("最大リトライ回数に達しました (参照入力)")


def _generate_images_with_retry(client, types, model, prompt_text,
                                 max_retries: int = 4, base_delay: float = 30.0):
    """404 フォールバック + 429 リトライ付き generate_images (通常生成モード)。
    Returns (response, used_model, error) のタプル。"""
    models_to_try = [model] + [m for m in _IMAGEN_FALLBACK_MODELS if m != model]
    last_err: Exception | None = None

    for m in models_to_try:
        delay = base_delay
        for attempt in range(max_retries + 1):
            try:
                resp = client.models.generate_images(
                    model=m,
                    prompt=prompt_text,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="1:1",
                        safety_filter_level=types.SafetyFilterLevel.BLOCK_LOW_AND_ABOVE,
                    ),
                )
                if m != model:
                    print(f"[INFO] フォールバックモデルで成功: {m}")
                return resp, m, None
            except Exception as err:
                last_err = err
                if _is_not_found(err):
                    print(f"[WARN] モデル {m} が見つかりません。次のモデルを試みます...")
                    break  # 次のモデルへ
                if _is_rate_limit(err) and attempt < max_retries:
                    print(f"[WARN] Imagen ({m}) 429 超過。{delay:.0f}秒後にリトライ ({attempt + 1}/{max_retries})...")
                    time.sleep(delay)
                    delay *= 2
                else:
                    break  # リトライ上限 or その他エラー

    return None, None, last_err


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
        # Gemini API (非 Vertex) では Part.from_uri(file_uri=任意の公開URL) は
        # サーバー側フェッチに失敗し 400 INVALID_ARGUMENT になる。
        # ここで実バイトを取得して from_bytes で渡す。取得失敗した URL はスキップ。
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.content
            if not data:
                raise ValueError("空レスポンス")
            mime = resp.headers.get("Content-Type") or _guess_mime_type(url)
            if not str(mime).startswith("image/"):
                mime = _guess_mime_type(url)
            parts.append(types_module.Part.from_bytes(data=data, mime_type=mime))
        except Exception as err:  # noqa: BLE001
            print(f"[WARN] 参照URL取得失敗のためスキップ: {url} ({err})")
            continue
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
    scene: str = "",
    style: str = "",
    composition: str = "",
    background: str = "",
    iterate_from: str | None = None,
    revisions: list[str] | None = None,
    prompt_override: str | None = None,
    extra_ref_locals: list[str] | None = None,
    skip_db_refs: bool = False,
    skip_ref_urls: bool = False,
) -> list[Path]:
    """Imagen 3 でキャラクター画像を生成して保存する。

    Parameters
    ----------
    num:      キャラクター番号 (例: 57)
    form:     形態 ("corefolder" または "humanoid")
    work_key: 作品キー
    out_dir:  出力ベースディレクトリ (None の場合は環境変数
              ``OUTPUT_BASE_DIR`` → ``OUTPUT_DIR`` → ``output`` を使用し、
              ``{YYYYMMDD}/{YYYYMMDD_HHMMSS}_gemini_{form}_num{NNN}/`` を切る)。
              out_dir を明示した場合 (パイプラインの各ステージ配下) は日付フォルダを
              作らず ``{out_dir}/{YYYYMMDD_HHMMSS}_gemini_{form}_num{NNN}/`` をフラットに切る。
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

    model = os.environ.get("IMAGEN_MODEL", "imagen-4.0-generate-001")
    _inter_image_sleep = float(os.environ.get("GEMINI_IMAGE_SLEEP", "6"))
    _api_timeout = int(os.environ.get("GEMINI_API_TIMEOUT", "120"))
    reference_model = os.environ.get("GEMINI_REFERENCE_MODEL", "models/gemini-3.1-flash-image")

    # iterate-from が指定されている場合、起点画像と次の iter ラベルを解決する。
    iterate_source_path: Path | None = None
    iterate_source_dir: Path | None = None
    iter_label: str | None = None
    revision_items: list[str] = []
    if iterate_from:
        try:
            iterate_source_path, iterate_source_dir = resolve_iterate_source(iterate_from)
        except (FileNotFoundError, ValueError) as err:
            sys.exit(f"[ERROR] --iterate-from の解決に失敗: {err}")
        iter_label = next_iteration_label(iterate_source_path)
        if isinstance(revisions, str):
            revision_items = parse_revisions(revisions)
        else:
            revision_items = list(revisions or [])
        print(
            f"[INFO] iterate-from: {iterate_source_path}"
            f" -> 次ラベル: {iter_label} / 修正指示 {len(revision_items)} 件"
        )

    # out_dir 明示時 (パイプラインの各ステージ配下) は日付フォルダを作らずフラットに置く。
    output_dir = build_run_output_dir(
        provider="gemini",
        num=num,
        form=form,
        base_dir=out_dir,
        suffix=iter_label,
        date_group=out_dir is None,
    )
    print(f"[INFO] 出力先: {output_dir}")

    # キャラクターデータ取得
    record = find_character(num, work_key)
    if record is None:
        sys.exit(f"[ERROR] キャラクター #{num} ({work_key}) が見つかりません。")

    data = build_gemini_prompt(
        record,
        form,
        scene=scene,
        style=style,
        composition=composition,
        background=background,
        revisions=revision_items or None,
    )
    prompt_text = prompt_override if prompt_override else data["prompt"]
    # 参照画像内のテキストが生成画像に転写されるのを防ぐ安全装置 (prompt_override でも維持)
    _no_text_suffix = (
        "\n[絶対禁止] 画像内に文字・テキスト・ラベル・サインを一切描かないこと。"
        " Do NOT render any text, words, labels, or signs in the image."
    )
    if _no_text_suffix not in prompt_text:
        prompt_text = prompt_text + _no_text_suffix
    ref_url = data["reference_image_url"]
    ref_urls = data.get("reference_image_urls") or []
    ref_locals = data.get("reference_local_paths") or []

    # i2i 最小修正時は DB 参照画像を除外する。DB 画像があると Gemini が
    # 「DB に合わせてほしい」と解釈して余計な要素を追加することがあるため。
    if skip_db_refs:
        ref_locals = []
        ref_urls = []
    elif skip_ref_urls:
        # DB サーバーの URL が Gemini のデータセンターからフェッチできず
        # 400 INVALID_ARGUMENT になるケースがあるため URL のみ除外する。
        # ローカルキャッシュ済みの参照画像は引き続き使用する。
        ref_urls = []

    # iterate-from の起点画像を参照ローカルの先頭へ差し込む (最高優先で添付)。
    if iterate_source_path is not None:
        iterate_path_str = str(iterate_source_path)
        if iterate_path_str in ref_locals:
            ref_locals.remove(iterate_path_str)
        ref_locals.insert(0, iterate_path_str)

    # extra_ref_locals (Stage 5 合成ラフ等) を iterate_from の直後に差し込む。
    # limit を 1 増やして合成参照が確実に含まれるようにする。
    ref_limit = 4
    if extra_ref_locals:
        for ep in reversed(extra_ref_locals):
            ep_str = str(ep)
            if ep_str not in ref_locals:
                ref_locals.insert(0 if iterate_source_path is None else 1, ep_str)
        ref_limit = 5

    print(f"[INFO] キャラクター: {record['data'].get('Name', num)} / 形態: {form}")
    print(f"[INFO] 参照画像: {ref_url or '(なし)'}")
    print(f"[INFO] 参照画像候補: URL {len(ref_urls)}件 / ローカル {len(ref_locals)}件")
    print(f"[INFO] モデル: {model} / 生成枚数: {count}")

    log_paths = initialize_run_logs(
        output_dir,
        provider="gemini",
        num=num,
        form=form,
        work_key=work_key,
        model=model,
        prompt_text=prompt_text,
        meta={
            "character_name": record["data"].get("Name", str(num)),
            "count": int(count),
            "reference_model": reference_model,
            "reference_image_url": ref_url,
            "reference_image_urls": ref_urls,
            "reference_local_paths": ref_locals,
            "scene": scene or "",
            "style": style or "",
            "composition": composition or "",
            "background": background or "",
            "iteration": (
                {
                    "label": iter_label,
                    "source_image": str(iterate_source_path),
                    "source_dir": str(iterate_source_dir) if iterate_source_dir else None,
                    "revisions": revision_items,
                }
                if iterate_source_path is not None
                else None
            ),
            "record_capabilities": collect_record_capabilities(record, form=form),
        },
    )
    print(f"[INFO] ログ: {log_paths['meta']}")

    client = genai.Client(api_key=api_key, http_options={"timeout": _api_timeout})
    ref_parts = _build_reference_parts(types, ref_urls, ref_locals, limit=ref_limit)
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

    write_run_meta(
        output_dir,
        {
            "multimodal_model": multimodal_model,
            "use_reference_input": use_reference_input,
        },
    )

    saved: list[Path] = []
    results: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    for i in range(count):
        # レートリミット対策: 2枚目以降は待機
        if i > 0:
            print(f"[INFO] レートリミット対策: {_inter_image_sleep:.0f}秒待機 (画像 {i + 1}/{count})...")
            time.sleep(_inter_image_sleep)

        image_data: bytes | None = None
        attempt_errors: list[str] = []

        if use_reference_input:
            response, err = _generate_content_with_retry(
                client, types, multimodal_model, prompt_text, ref_parts
            )
            if err is None:
                generated = _extract_generated_image_bytes(response)
                if generated:
                    image_data = generated[0]
                else:
                    msg = f"画像 {i + 1}: 参照入力モードの生成結果が空でした。通常生成へフォールバックします。"
                    print(f"[WARN] {msg}")
                    attempt_errors.append(msg)
            else:
                msg = f"画像 {i + 1}: 参照入力モードに失敗 ({err})。通常生成へフォールバックします。"
                print(f"[WARN] {msg}")
                attempt_errors.append(msg)

        if image_data is None:
            response, used_model, err = _generate_images_with_retry(
                client, types, model, prompt_text
            )
            if err is None and response is not None:
                generated = _extract_generated_image_bytes(response)
                if generated:
                    image_data = generated[0]
                else:
                    msg = f"画像 {i + 1} の生成結果が空でした。スキップします。"
                    print(f"[WARN] {msg}")
                    attempt_errors.append(msg)
            else:
                msg = f"画像 {i + 1}: 通常生成も失敗しました ({err})"
                print(f"[ERROR] {msg}")
                attempt_errors.append(msg)

        out_path = output_dir / f"num{num:03d}_{form}_{i + 1:02d}.png"
        if image_data is None:
            print(f"[WARN] 画像 {i + 1}: 画像データが取得できませんでした。スキップします。")
            results.append({"index": i + 1, "file": str(out_path.name), "status": "failed"})
            errors.append({"index": i + 1, "messages": attempt_errors})
            continue
        # 実体 MIME を判定し、拡張子を実体に合わせて保存 (Gemini は JPEG を返すことがあるため)
        out_path = save_image_bytes(image_data, out_path)
        print(f"[OK] 保存: {out_path}")
        saved.append(out_path)
        results.append({"index": i + 1, "file": str(out_path.name), "status": "ok"})
        if attempt_errors:
            errors.append({"index": i + 1, "messages": attempt_errors})

    final_status = "ok" if saved and not errors else (
        "partial" if saved else "failed"
    )
    finalize_run_logs(
        output_dir,
        status=final_status,
        results=results,
        errors=errors,
        extra={"saved_count": len(saved)},
    )

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
    parser.add_argument(
        "--out",
        default=None,
        help=(
            "出力ベースディレクトリ (省略時は OUTPUT_BASE_DIR / OUTPUT_DIR / 'output')。"
            "実際は配下に {YYYYMMDD_HHMMSS}_gemini_{form}_num{NNN}/ を作って保存します。"
        ),
    )
    parser.add_argument("--count", type=int, default=1, choices=range(1, 5), help="生成枚数 (1-4)")
    parser.add_argument(
        "--scene",
        default="",
        help="生成時に追加で指定するシーン/ポーズ説明 (例: 「図書館で本を読んでいるシーン」)",
    )
    parser.add_argument(
        "--style",
        default="",
        help="作風ヒント (例: 'watercolor' / 'pixel art' / 'official artwork')",
    )
    parser.add_argument(
        "--composition",
        default="",
        help="構図ヒント (例: 'low angle, full body' / 'bust shot' / 'dynamic action')",
    )
    parser.add_argument(
        "--background",
        default="",
        help="背景ヒント (例: 'sunset library' / 'white background')",
    )
    parser.add_argument(
        "--iterate-from",
        dest="iterate_from",
        default=None,
        help=(
            "i2i 起点となる前回生成画像 (ファイル) または run ディレクトリ。"
            " 指定すると先頭参照に差し込み、出力先サブフォルダ名末尾に iterN ラベルを付与する。"
        ),
    )
    parser.add_argument(
        "--revisions",
        default=None,
        help=(
            "iterate-from と併用する修正指示。';' または改行で複数項目に分割される。"
            " 例: '尻尾は元のまま; 表情だけ笑顔にして'"
        ),
    )
    args = parser.parse_args()

    paths = generate_image(
        num=args.num,
        form=args.form,
        work_key=args.work,
        out_dir=args.out,
        count=args.count,
        scene=args.scene,
        style=args.style,
        composition=args.composition,
        background=args.background,
        iterate_from=args.iterate_from,
        revisions=parse_revisions(args.revisions),
    )
    if paths:
        print(f"\n[完了] {len(paths)} 枚の画像を生成しました。")
    else:
        print("\n[完了] 画像は生成されませんでした。")


if __name__ == "__main__":
    main()
