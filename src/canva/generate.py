"""
canva/generate.py — Canva Connect API による「デザイン化 & 書き出し」プロバイダ
Copyright © RadianN_kswg — CC BY-NC 4.0

【重要】Canva Connect API には「テキスト→画像」の生成機能はありません
(Magic Media の text-to-image は Canva アプリ / MCP ワークフロー側でのみ利用可)。
そのため本プロバイダは「すでに生成済みの画像 (Gemini/OpenAI/Firefly の出力など)」
を入力に取り、Canva にアップロード → デザイン作成 → PNG/JPG/PDF で書き出す
"後段(フィニッシング)" ツールとして動作します。

  generated image ──▶ Canva アップロード ──▶ デザイン作成 ──▶ 書き出し ──▶ 保存

使用方法:
    python -m src.canva.generate --num 57 --form corefolder \
        --from-image output/.../num057_corefolder_01.png

保存先:
    {OUTPUT_BASE_DIR}/{YYYYMMDD}/{ts}_canva_{form}_num{NNN}/
    (out_dir 明示時 = パイプライン各ステージ配下では日付フォルダを作らずフラットに配置)

必要な環境変数 (.env):
    CANVA_ACCESS_TOKEN   — Canva Connect の user OAuth アクセストークン
    CANVA_EXPORT_FORMAT  — 書き出し形式 (png/jpg/pdf, デフォルト png)
    OUTPUT_BASE_DIR      — 出力ベースディレクトリ (デフォルト: output)

参考:
    https://www.canva.dev/docs/connect/
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import (  # noqa: E402
    build_run_output_dir,
    finalize_run_logs,
    find_character,
    format_num,
    initialize_run_logs,
    save_image_bytes,
)

_API_BASE = "https://api.canva.com/rest/v1"


def _request(method: str, url: str, token: str, *, body: bytes | None = None,
             headers: dict[str, str] | None = None) -> dict:
    hdrs = {"Authorization": f"Bearer {token}"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    with urllib.request.urlopen(req) as resp:  # noqa: S310 (信頼済 Canva API)
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def _poll_job(url: str, token: str, *, timeout: float = 120.0,
              interval: float = 2.0) -> dict:
    """`{...,"job":{"status":"in_progress|success|failed",...}}` 形式をポーリング。"""
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        last = _request("GET", url, token)
        job = last.get("job") or last
        status = job.get("status")
        if status in ("success", "completed"):
            return last
        if status in ("failed", "error"):
            raise RuntimeError(f"Canva ジョブ失敗: {job}")
        time.sleep(interval)
    raise TimeoutError(f"Canva ジョブがタイムアウトしました: {last}")


def _upload_asset(token: str, image_path: Path) -> str:
    """画像をアップロードして asset_id を返す。"""
    name_b64 = base64.b64encode(image_path.name.encode("utf-8")).decode("ascii")
    meta = json.dumps({"name_base64": name_b64})
    res = _request(
        "POST", f"{_API_BASE}/asset-uploads", token,
        body=image_path.read_bytes(),
        headers={
            "Content-Type": "application/octet-stream",
            "Asset-Upload-Metadata": meta,
        },
    )
    job = res.get("job") or {}
    job_id = job.get("id")
    if not job_id:
        # 同期的に asset が返る場合もある
        asset = (res.get("job") or {}).get("asset") or res.get("asset") or {}
        if asset.get("id"):
            return asset["id"]
        raise RuntimeError(f"asset-upload ジョブIDが取得できません: {res}")
    done = _poll_job(f"{_API_BASE}/asset-uploads/{job_id}", token)
    asset = (done.get("job") or {}).get("asset") or {}
    asset_id = asset.get("id")
    if not asset_id:
        raise RuntimeError(f"asset_id が取得できません: {done}")
    return asset_id


def _create_design(token: str, asset_id: str, title: str) -> str:
    """asset から design を作成して design_id を返す。"""
    body = json.dumps({
        "design_type": {"type": "preset", "name": "presentation"},
        "asset_id": asset_id,
        "title": title,
    }).encode("utf-8")
    res = _request(
        "POST", f"{_API_BASE}/designs", token,
        body=body, headers={"Content-Type": "application/json"},
    )
    design = res.get("design") or res
    design_id = design.get("id")
    if not design_id:
        raise RuntimeError(f"design_id が取得できません: {res}")
    return design_id


def _export_design(token: str, design_id: str, fmt: str) -> list[str]:
    """design を書き出して URL のリストを返す。"""
    body = json.dumps({
        "design_id": design_id,
        "format": {"type": fmt},
    }).encode("utf-8")
    res = _request(
        "POST", f"{_API_BASE}/exports", token,
        body=body, headers={"Content-Type": "application/json"},
    )
    job = res.get("job") or {}
    job_id = job.get("id")
    if not job_id:
        raise RuntimeError(f"export ジョブIDが取得できません: {res}")
    done = _poll_job(f"{_API_BASE}/exports/{job_id}", token)
    urls = (done.get("job") or {}).get("urls") or []
    return [u for u in urls if u]


def export_via_canva(
    num: int,
    form: str = "corefolder",
    work_key: str = "#Works_NumberTales",
    out_dir: str | None = None,
    from_image: str | None = None,
    title: str | None = None,
    dry_run: bool = False,
) -> list[Path]:
    """生成済み画像を Canva デザイン化して書き出す。

    Returns
    -------
    保存したファイルパスのリスト。
    """
    token = os.environ.get("CANVA_ACCESS_TOKEN")
    fmt = (os.environ.get("CANVA_EXPORT_FORMAT", "png") or "png").lower()

    if not from_image:
        sys.exit(
            "[ERROR] canva プロバイダは入力画像が必須です。--from-image に "
            "生成済み画像 (Gemini/OpenAI/Firefly の出力など) を指定してください。"
        )
    src_path = Path(from_image)
    if not src_path.exists() or not src_path.is_file():
        sys.exit(f"[ERROR] --from-image が見つかりません: {src_path}")

    if not dry_run and not token:
        sys.exit("[ERROR] CANVA_ACCESS_TOKEN が設定されていません。.env を確認してください。")

    # out_dir 明示時 (パイプラインの各ステージ配下) は日付フォルダを作らずフラットに置く。
    output_dir = build_run_output_dir(
        provider="canva", num=num, form=form, base_dir=out_dir,
        date_group=out_dir is None,
    )
    print(f"[INFO] 出力先: {output_dir}")

    record = find_character(num, work_key)
    char_name = (record["data"].get("Name_JP") or record["data"].get("Name") or str(num)) if record else str(num)
    design_title = title or f"NumberTales #{format_num(num)} {form}"

    log_paths = initialize_run_logs(
        output_dir,
        provider="canva",
        num=num,
        form=form,
        work_key=work_key,
        model="canva-connect",
        prompt_text=f"[canva finishing] source={src_path.name} title={design_title}",
        meta={
            "mode": "design-export",
            "source_image": str(src_path),
            "export_format": fmt,
            "design_title": design_title,
            "character_name": char_name,
        },
    )
    print(f"[INFO] ログ: {log_paths['meta']}")
    print(f"[INFO] 入力画像: {src_path} / 書き出し形式: {fmt}")

    if dry_run:
        print("[DRY-RUN] Canva API は呼び出しません。アップロード→デザイン化→書き出しの予定のみ。")
        finalize_run_logs(
            output_dir, status="skipped",
            results=[{"status": "dry-run"}], errors=[], extra={"dry_run": True},
        )
        return []

    try:
        print("[INFO] (1/3) Canva へアップロード中...")
        asset_id = _upload_asset(token, src_path)
        print(f"[INFO] (2/3) デザイン作成中... (asset_id={asset_id})")
        design_id = _create_design(token, asset_id, design_title)
        print(f"[INFO] (3/3) 書き出し中... (design_id={design_id})")
        urls = _export_design(token, design_id, fmt)
    except Exception as err:
        print(f"[ERROR] Canva 処理に失敗: {err}")
        finalize_run_logs(
            output_dir, status="failed",
            results=[{"status": "failed"}], errors=[{"messages": [str(err)]}],
        )
        return []

    if not urls:
        print("[WARN] 書き出しURLが空でした。")
        finalize_run_logs(
            output_dir, status="failed",
            results=[{"status": "failed"}], errors=[{"messages": ["empty export urls"]}],
        )
        return []

    saved: list[Path] = []
    results: list[dict[str, object]] = []
    ext = {"jpg": ".jpg", "jpeg": ".jpg", "pdf": ".pdf"}.get(fmt, ".png")
    for i, url in enumerate(urls):
        out_path = output_dir / f"num{format_num(num)}_{form}_canva_{i + 1:02d}{ext}"
        try:
            with urllib.request.urlopen(url) as resp:  # noqa: S310 (Canva export URL)
                raw = resp.read()
            if ext in (".png", ".jpg"):
                out_path = save_image_bytes(raw, out_path)
            else:
                out_path.write_bytes(raw)
            print(f"[OK] 保存: {out_path}")
            saved.append(out_path)
            results.append({"index": i + 1, "file": out_path.name, "status": "ok"})
        except Exception as err:
            print(f"[WARN] 書き出し {i + 1} のDLに失敗: {err}")
            results.append({"index": i + 1, "status": "failed"})

    finalize_run_logs(
        output_dir,
        status="ok" if saved else "failed",
        results=results, errors=[], extra={"saved_count": len(saved), "design_id": design_id},
    )
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Canva Connect API で生成済み画像をデザイン化・書き出しします。"
            " (Canva Connect にテキスト→画像生成は無いため後段ツールです)"
        )
    )
    parser.add_argument("--num", type=int, required=True, help="キャラクター番号 (例: 57)")
    parser.add_argument(
        "--form", choices=["corefolder", "humanoid"], default="corefolder",
        help="形態 (出力フォルダ名/タイトル用)",
    )
    parser.add_argument("--work", default="#Works_NumberTales", help="作品キー")
    parser.add_argument("--out", default=None, help="出力ベースディレクトリ")
    parser.add_argument(
        "--from-image", dest="from_image", default=None, required=False,
        help="Canva に取り込む生成済み画像のパス (必須)",
    )
    parser.add_argument("--title", default=None, help="Canva デザインのタイトル")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Canva API を呼ばず予定/ログのみ生成",
    )
    args = parser.parse_args()

    paths = export_via_canva(
        num=args.num, form=args.form, work_key=args.work, out_dir=args.out,
        from_image=args.from_image, title=args.title, dry_run=args.dry_run,
    )
    if paths:
        print(f"\n[完了] {len(paths)} 件を書き出しました。")
    else:
        print("\n[完了] 書き出しはありませんでした。")


if __name__ == "__main__":
    main()
