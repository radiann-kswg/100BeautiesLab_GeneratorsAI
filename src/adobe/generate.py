"""
adobe/generate.py — Adobe Firefly Services (text-to-image) を使った画像生成スクリプト
Copyright © RadianN_kswg — CC BY-NC 4.0

Firefly Services の Generate Images API (v3) を OAuth Server-to-Server
(client_credentials) 認証で呼び出し、ナンバーテールズキャラクターの画像を
生成して保存します。既存の gemini / openai プロバイダと同じ出力レイアウト・
ログ規約に従います。

使用方法:
    python -m src.adobe.generate --num 57 --form corefolder --count 1

保存先:
    {OUTPUT_BASE_DIR}/{YYYYMMDD}/{ts}_adobe_{form}_num{NNN}/
    (out_dir 明示時 = パイプライン各ステージ配下では日付フォルダを作らずフラットに配置)

必要な環境変数 (.env):
    FIREFLY_CLIENT_ID      — Adobe Developer Console の Client ID (x-api-key)
    FIREFLY_CLIENT_SECRET  — Client Secret
    FIREFLY_SIZE           — 生成サイズ (デフォルト: 1024x1024)
    FIREFLY_MODEL          — 任意: モデルバージョン (省略時は API デフォルト)
    OUTPUT_BASE_DIR        — 出力ベースディレクトリ (デフォルト: output)

参考:
    https://developer.adobe.com/firefly-services/docs/firefly-api/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import (  # noqa: E402
    apply_generation_gate,
    build_dalle_prompt,
    build_run_output_dir,
    collect_record_capabilities,
    collect_reference_images,
    finalize_run_logs,
    find_character,
    initialize_run_logs,
    next_iteration_label,
    parse_revisions,
    resolve_iterate_source,
    save_image_bytes,
)

_IMS_TOKEN_URL = "https://ims-na1.adobelogin.com/ims/token/v3"
_FIREFLY_GENERATE_URL = "https://firefly-api.adobe.io/v3/images/generate"
_IMS_SCOPE = (
    "openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis"
)


def _parse_size(size: str) -> dict[str, int]:
    """`"1024x1024"` を {"width":1024,"height":1024} に変換。"""
    try:
        w, h = size.lower().split("x", 1)
        return {"width": int(w), "height": int(h)}
    except Exception:
        return {"width": 1024, "height": 1024}


def _get_ims_token(client_id: str, client_secret: str) -> str:
    """client_credentials で IMS アクセストークンを取得する (有効期限 24h)。"""
    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": _IMS_SCOPE,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        _IMS_TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:  # noqa: S310 (信頼済 Adobe IMS)
        payload = json.loads(resp.read().decode("utf-8"))
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"IMS トークン取得に失敗: {payload}")
    return token


def _call_firefly_generate(
    token: str,
    client_id: str,
    prompt: str,
    size: dict[str, int],
    num_variations: int,
    model: str | None,
) -> list[str]:
    """Firefly Generate Images API を叩き、生成画像 URL のリストを返す。"""
    payload: dict[str, object] = {
        "prompt": prompt,
        "numVariations": max(1, min(int(num_variations), 4)),
        "size": size,
    }
    if model:
        payload["modelVersion"] = model

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _FIREFLY_GENERATE_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": client_id,
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310 (信頼済 Adobe Firefly)
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Firefly API HTTP {e.code}: {body[:400]}\n"
            "ヒント: Adobe Developer Console でプロジェクトに "
            "「Firefly - Creative Cloud Automation API」サービスが追加されているか確認してください。"
        ) from e

    urls: list[str] = []
    for out in result.get("outputs", []) or []:
        image = out.get("image") or {}
        url = image.get("url") or image.get("presignedUrl")
        if url:
            urls.append(url)
    return urls


def generate_image_firefly(
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
    dry_run: bool = False,
    prompt_override: str | None = None,
) -> list[Path]:
    """Adobe Firefly でキャラクター画像を生成して保存する。

    Returns
    -------
    保存したファイルパスのリスト。
    """
    client_id = os.environ.get("FIREFLY_CLIENT_ID")
    client_secret = os.environ.get("FIREFLY_CLIENT_SECRET")
    if not dry_run and (not client_id or not client_secret):
        sys.exit(
            "[ERROR] FIREFLY_CLIENT_ID / FIREFLY_CLIENT_SECRET が設定されていません。"
            ".env を確認してください。"
        )

    size_str = os.environ.get("FIREFLY_SIZE", "1024x1024")
    size = _parse_size(size_str)
    model = os.environ.get("FIREFLY_MODEL") or None

    # iterate-from の解決 (出力フォルダ名 suffix 用)。Firefly v3 generate は
    # 参照画像入力に別途アップロードが必要なため、ここではラベル付けのみ。
    iterate_source_path: Path | None = None
    iter_label: str | None = None
    revision_items: list[str] = []
    if iterate_from:
        try:
            iterate_source_path, _ = resolve_iterate_source(iterate_from)
        except (FileNotFoundError, ValueError) as err:
            sys.exit(f"[ERROR] --iterate-from の解決に失敗: {err}")
        iter_label = next_iteration_label(iterate_source_path)
        revision_items = (
            parse_revisions(revisions) if isinstance(revisions, str) else list(revisions or [])
        )

    # out_dir 明示時 (パイプラインの各ステージ配下) は日付フォルダを作らずフラットに置く。
    output_dir = build_run_output_dir(
        provider="adobe", num=num, form=form, base_dir=out_dir, suffix=iter_label,
        date_group=out_dir is None,
    )
    print(f"[INFO] 出力先: {output_dir}")

    record = find_character(num, work_key)
    if record is None:
        sys.exit(f"[ERROR] キャラクター #{num} ({work_key}) が見つかりません。")

    # AI 学習/生成オプトアウト・ゲート（権利軸=中止、充填軸=警告のうえ続行）
    proceed, ai_gate = apply_generation_gate(record, usage="image", num=num, printer=print)
    if not proceed:
        return []

    prompt_text = prompt_override or build_dalle_prompt(
        record,
        form,
        scene=scene,
        style=style,
        composition=composition,
        background=background,
        revisions=revision_items or None,
    )
    references = collect_reference_images(record, form=form)

    print(f"[INFO] キャラクター: {record['data'].get('Name_JP') or record['data'].get('Name') or num} / 形態: {form}")
    print(f"[INFO] モデル: Firefly ({model or 'default'}) / サイズ: {size_str} / 枚数: {count}")

    log_paths = initialize_run_logs(
        output_dir,
        provider="adobe",
        num=num,
        form=form,
        work_key=work_key,
        model=model or "firefly-default",
        prompt_text=prompt_text,
        meta={
            "mode": "firefly-generate",
            "size": size_str,
            "count": int(count),
            "reference_urls": references["urls"],
            "reference_local_paths": references["local_paths"],
            "character_name": record["data"].get("Name_JP") or record["data"].get("Name") or str(num),
            "scene": scene or "",
            "style": style or "",
            "composition": composition or "",
            "background": background or "",
            "iteration": (
                {"label": iter_label, "source_image": str(iterate_source_path),
                 "revisions": revision_items}
                if iterate_source_path is not None else None
            ),
            "record_capabilities": collect_record_capabilities(record, form=form),
            "ai_training_gate": ai_gate,
        },
    )
    print(f"[INFO] ログ: {log_paths['meta']}")

    if dry_run:
        print("[DRY-RUN] Firefly API は呼び出しません。プロンプトとログのみ生成しました。")
        finalize_run_logs(
            output_dir, status="skipped",
            results=[{"status": "dry-run"}], errors=[], extra={"dry_run": True},
        )
        return []

    try:
        token = _get_ims_token(client_id, client_secret)
        urls = _call_firefly_generate(
            token, client_id, prompt_text, size, int(count), model
        )
    except Exception as err:
        print(f"[ERROR] Firefly 生成に失敗: {err}")
        finalize_run_logs(
            output_dir, status="failed",
            results=[{"status": "failed"}], errors=[{"messages": [str(err)]}],
        )
        return []

    if not urls:
        print("[WARN] Firefly の生成結果が空でした。")
        finalize_run_logs(
            output_dir, status="failed",
            results=[{"status": "failed"}], errors=[{"messages": ["empty outputs"]}],
        )
        return []

    saved: list[Path] = []
    results: list[dict[str, object]] = []
    for i, url in enumerate(urls):
        out_path = output_dir / f"num{num:03d}_{form}_firefly_{i + 1:02d}.png"
        try:
            with urllib.request.urlopen(url) as resp:  # noqa: S310 (Firefly presigned URL)
                raw = resp.read()
            out_path = save_image_bytes(raw, out_path)
            print(f"[OK] 保存: {out_path}")
            saved.append(out_path)
            results.append({"index": i + 1, "file": out_path.name, "status": "ok"})
        except Exception as err:
            print(f"[WARN] 画像 {i + 1} のDLに失敗: {err}")
            results.append({"index": i + 1, "status": "failed"})

    finalize_run_logs(
        output_dir,
        status="ok" if saved else "failed",
        results=results,
        errors=[],
        extra={"saved_count": len(saved)},
    )
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adobe Firefly Services でナンバーテールズキャラクター画像を生成します。"
    )
    parser.add_argument("--num", type=int, required=True, help="キャラクター番号 (例: 57)")
    parser.add_argument(
        "--form", choices=["corefolder", "humanoid"], default="corefolder",
        help="生成する形態 (デフォルト: corefolder)",
    )
    parser.add_argument("--work", default="#Works_NumberTales", help="作品キー")
    parser.add_argument("--out", default=None, help="出力ベースディレクトリ")
    parser.add_argument("--count", type=int, default=1, choices=range(1, 5), help="生成枚数 (1-4)")
    parser.add_argument("--scene", default="", help="シーン/ポーズ説明")
    parser.add_argument("--style", default="", help="作風ヒント")
    parser.add_argument("--composition", default="", help="構図ヒント")
    parser.add_argument("--background", default="", help="背景ヒント")
    parser.add_argument(
        "--iterate-from", dest="iterate_from", default=None,
        help="出力サブフォルダ名末尾に iterN ラベルを付与する起点画像/runディレクトリ",
    )
    parser.add_argument("--revisions", default=None, help="iterate-from 併用時の修正指示 (';' 区切り)")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Firefly API を呼ばずプロンプト/ログのみ生成 (課金ゼロ)",
    )
    args = parser.parse_args()

    paths = generate_image_firefly(
        num=args.num, form=args.form, work_key=args.work, out_dir=args.out,
        count=args.count, scene=args.scene, style=args.style,
        composition=args.composition, background=args.background,
        iterate_from=args.iterate_from, revisions=parse_revisions(args.revisions),
        dry_run=args.dry_run,
    )
    if paths:
        print(f"\n[完了] {len(paths)} 枚の画像を生成しました。")
    else:
        print("\n[完了] 画像は生成されませんでした。")


if __name__ == "__main__":
    main()
