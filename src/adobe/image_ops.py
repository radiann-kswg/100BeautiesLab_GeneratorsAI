"""
adobe/image_ops.py — Adobe Firefly 以外の画像処理 API (Photoshop / Lightroom) + PIL フォールバック
Copyright © RadianN_kswg — CC BY-NC 4.0

Stage 2 で「構図ガイド」を生成するために使用する。
Firefly による text-to-image ではなく、Adobe の Lightroom / Photoshop API で
創作 DB の参照画像を加工し、シーン演出・構図寄せを施した「構図ガイド画像」を作る。

処理フロー:
  1. DB 参照画像 (キャラクターのコアフォルダ or ヒューマノイド画像) を取得
  2. Adobe Lightroom API で自動トーン調整 → シーン雰囲気に合わせた露光・色温度変更
  3. Photoshop API でオブジェクト切り抜き (背景除去 → 新背景合成)
  4. 結果を stage2_rough/ に保存して Gemini への参照として渡す

Adobe API が設定されていない場合: PIL を使ったローカル処理にフォールバック。
  - 自動トーン: ヒストグラム正規化 + コントラスト強調
  - 背景調整: 背景色をシーン指定のカラーに変更
  - スタイルフィルタ: ソフトフォーカス / アンシャープマスク

必要な環境変数:
  FIREFLY_CLIENT_ID       — IMS 認証の Client ID (Lightroom/Photoshop API も共通)
  FIREFLY_CLIENT_SECRET   — Client Secret
  ADOBE_STORAGE_TYPE      — "dropbox" / "s3" / "local" (default: "local" = PIL fallback)
  ADOBE_LIGHTROOM_API_URL — Lightroom API エンドポイント (デフォルト: 公式 URL)
  ADOBE_PHOTOSHOP_API_URL — Photoshop API エンドポイント (デフォルト: 公式 URL)

参考:
  https://developer.adobe.com/photoshop/photoshop-api-docs/
  https://developer.adobe.com/photoshop/photoshop-api-docs/features/lightroom/
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from src.utils import collect_reference_images, find_character  # noqa: E402

_IMS_TOKEN_URL = "https://ims-na1.adobelogin.com/ims/token/v3"
_IMS_SCOPE = (
    "openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis"
)
_LR_AUTOTONE_URL = "https://image.adobe.io/lrService/autoTone"
_LR_EDIT_URL = "https://image.adobe.io/lrService/editPhoto"
_PS_CUTOUT_URL = "https://image.adobe.io/sensei/cutout"

# 背景カラーのシーンキーワードマッピング（PIL フォールバック用）
_SCENE_BACKGROUND_COLORS: dict[str, tuple[int, int, int]] = {
    "図書館": (230, 215, 190),
    "library": (230, 215, 190),
    "夕暮れ": (255, 180, 100),
    "sunset": (255, 180, 100),
    "森": (100, 160, 100),
    "forest": (100, 160, 100),
    "海": (100, 160, 220),
    "ocean": (100, 160, 220),
    "夜": (40, 40, 80),
    "night": (40, 40, 80),
    "白": (255, 255, 255),
    "white": (255, 255, 255),
    "黒": (30, 30, 30),
    "black": (30, 30, 30),
    "空": (180, 210, 255),
    "sky": (180, 210, 255),
}

_DEFAULT_BG_COLOR: tuple[int, int, int] = (200, 200, 210)


def _get_ims_token(client_id: str, client_secret: str) -> str:
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
    with urllib.request.urlopen(req) as resp:  # noqa: S310
        payload = json.loads(resp.read().decode("utf-8"))
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"IMS トークン取得に失敗: {payload}")
    return token


def _adobe_post_json(url: str, token: str, client_id: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
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
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Adobe API HTTP {e.code}: {body[:400]}") from e


def _poll_job(
    status_url: str,
    token: str,
    client_id: str,
    max_wait: int = 120,
    interval: int = 3,
) -> dict:
    """Adobe 非同期ジョブのステータスをポーリングして結果を返す。"""
    headers = {
        "x-api-key": client_id,
        "Authorization": f"Bearer {token}",
    }
    waited = 0
    while waited < max_wait:
        req = urllib.request.Request(status_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req) as resp:  # noqa: S310
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ジョブステータス取得失敗 HTTP {e.code}: {body[:200]}") from e

        status = (result.get("status") or result.get("_status") or "").lower()
        if status in ("succeeded", "done", "complete"):
            return result
        if status in ("failed", "error"):
            raise RuntimeError(f"Adobe ジョブ失敗: {json.dumps(result)[:400]}")

        time.sleep(interval)
        waited += interval

    raise TimeoutError(f"Adobe ジョブがタイムアウトしました ({max_wait}s)")


def _download_url_to_path(url: str, out_path: Path) -> Path:
    with urllib.request.urlopen(url) as resp:  # noqa: S310
        raw = resp.read()
    out_path.write_bytes(raw)
    return out_path


# ── PIL フォールバック ─────────────────────────────────────────────────────────

def _guess_bg_color(scene: str, background: str) -> tuple[int, int, int]:
    combined = (scene + " " + background).lower()
    for keyword, color in _SCENE_BACKGROUND_COLORS.items():
        if keyword in combined:
            return color
    return _DEFAULT_BG_COLOR


def _pil_auto_tone(img: Any) -> Any:
    """PIL を使ったローカル自動トーン（ヒストグラム正規化 + コントラスト強調）。"""
    from PIL import ImageEnhance, ImageOps  # type: ignore[import]

    img = img.convert("RGB")
    img = ImageOps.autocontrast(img, cutoff=2)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Color(img).enhance(1.1)
    return img


def _pil_apply_bg(img: Any, bg_color: tuple[int, int, int]) -> Any:
    """PIL を使った背景色変更（透過部分 or 四隅をぼかして背景を合成）。"""
    from PIL import Image, ImageFilter  # type: ignore[import]

    img = img.convert("RGBA")
    # ソフトビネット合成で構図ガイドらしい演出を付ける
    w, h = img.size
    bg = Image.new("RGBA", (w, h), bg_color + (255,))

    # エッジをソフトにして合成
    blurred = img.filter(ImageFilter.GaussianBlur(radius=2))
    composite = Image.alpha_composite(bg, blurred)
    return composite.convert("RGB")


def _pil_apply_style(img: Any, style_hint: str = "") -> Any:
    """シーン用のソフトスタイルフィルタ（軽いグロウ効果）。"""
    from PIL import ImageFilter, ImageEnhance  # type: ignore[import]

    # 僅かなソフトフォーカスで「ラフスケッチ的な」雰囲気にする
    softened = img.filter(ImageFilter.GaussianBlur(radius=1))
    from PIL import Image  # type: ignore[import]
    img = Image.blend(img, softened, alpha=0.3)
    # 僅かに彩度を下げて「構図ガイド」らしい落ち着いた見た目に
    img = ImageEnhance.Color(img).enhance(0.85)
    return img


def _create_composition_guide_pil(
    ref_paths: list[str],
    stage_dir: Path,
    scene: str,
    background: str,
    style: str,
    num: int,
    form: str,
) -> list[Path]:
    """PIL フォールバック: 参照画像を加工して構図ガイドを作成する。"""
    try:
        from PIL import Image  # type: ignore[import]
    except ImportError:
        print("[WARN] Pillow がインストールされていません。構図ガイド生成をスキップします。")
        print("       pip install Pillow  でインストールしてください。")
        return []

    bg_color = _guess_bg_color(scene, background)
    saved: list[Path] = []

    for i, ref_path in enumerate(ref_paths[:2]):  # 最大 2 枚
        p = Path(ref_path)
        if not p.exists():
            continue
        try:
            img = Image.open(p)
            img = _pil_auto_tone(img)
            img = _pil_apply_bg(img, bg_color)
            img = _pil_apply_style(img, style)
            out_path = stage_dir / f"num{num:03d}_{form}_composition_guide_{i + 1:02d}.png"
            img.save(out_path, format="PNG")
            print(f"[Stage2-Adobe] 構図ガイド (PIL): {out_path.name}")
            saved.append(out_path)
        except Exception as err:
            print(f"[WARN] PIL 構図ガイド生成 {p.name} 失敗: {err}")

    return saved


# ── Adobe Lightroom API ────────────────────────────────────────────────────────

def _lr_auto_tone(
    input_href: str,
    output_href: str,
    token: str,
    client_id: str,
    storage: str = "external",
) -> str:
    """Lightroom API の autoTone を呼んで output presigned URL を返す。"""
    payload = {
        "inputs": [{"storage": storage, "href": input_href}],
        "outputs": [{"storage": storage, "href": output_href, "type": "image/jpeg"}],
    }
    result = _adobe_post_json(_LR_AUTOTONE_URL, token, client_id, payload)
    status_url = (
        result.get("_links", {}).get("self", {}).get("href")
        or result.get("statusUrl")
    )
    if not status_url:
        raise RuntimeError(f"Lightroom autoTone: statusUrl が取得できません: {result}")
    job_result = _poll_job(status_url, token, client_id)
    outputs = job_result.get("outputs") or []
    if outputs and isinstance(outputs[0], dict):
        return outputs[0].get("href") or output_href
    return output_href


def _lr_edit_photo(
    input_href: str,
    output_href: str,
    token: str,
    client_id: str,
    brightness: int = 0,
    contrast: int = 15,
    color_temperature: int = 0,
    storage: str = "external",
) -> str:
    """Lightroom API の editPhoto で露光・色温度を調整する。"""
    payload = {
        "inputs": [{"storage": storage, "href": input_href}],
        "outputs": [{"storage": storage, "href": output_href, "type": "image/jpeg"}],
        "options": {
            "Brightness": brightness,
            "Contrast": contrast,
            "Temperature": color_temperature,
        },
    }
    result = _adobe_post_json(_LR_EDIT_URL, token, client_id, payload)
    status_url = (
        result.get("_links", {}).get("self", {}).get("href")
        or result.get("statusUrl")
    )
    if not status_url:
        raise RuntimeError(f"Lightroom editPhoto: statusUrl が取得できません: {result}")
    job_result = _poll_job(status_url, token, client_id)
    outputs = job_result.get("outputs") or []
    if outputs and isinstance(outputs[0], dict):
        return outputs[0].get("href") or output_href
    return output_href


def _create_composition_guide_adobe(
    ref_paths: list[str],
    stage_dir: Path,
    scene: str,
    background: str,
    style: str,
    num: int,
    form: str,
    token: str,
    client_id: str,
) -> list[Path]:
    """Adobe Lightroom API を使った構図ガイド生成。

    外部ストレージ（Dropbox / S3 等）が設定されていない場合は空リストを返す。
    ADOBE_INPUT_STORAGE_URL / ADOBE_OUTPUT_STORAGE_URL 環境変数で
    presigned URL を直接指定することも可能（テスト用途）。
    """
    storage_type = os.environ.get("ADOBE_STORAGE_TYPE", "local").lower()
    if storage_type == "local":
        print("[INFO] ADOBE_STORAGE_TYPE=local のため Adobe Lightroom API をスキップ。PIL fallback を使用します。")
        return []

    saved: list[Path] = []
    for i, ref_path in enumerate(ref_paths[:2]):
        p = Path(ref_path)
        if not p.exists():
            continue
        # 外部ストレージ presigned URL (環境変数で設定)
        input_url = os.environ.get(f"ADOBE_INPUT_URL_{i + 1}")
        output_url = os.environ.get(f"ADOBE_OUTPUT_URL_{i + 1}")
        if not input_url or not output_url:
            print(f"[WARN] ADOBE_INPUT_URL_{i + 1} / ADOBE_OUTPUT_URL_{i + 1} 未設定。スキップ。")
            continue
        try:
            result_url = _lr_auto_tone(input_url, output_url, token, client_id, storage_type)
            out_path = stage_dir / f"num{num:03d}_{form}_composition_guide_adobe_{i + 1:02d}.jpg"
            _download_url_to_path(result_url, out_path)
            print(f"[Stage2-Adobe] 構図ガイド (Lightroom API): {out_path.name}")
            saved.append(out_path)
        except Exception as err:
            print(f"[WARN] Adobe Lightroom 構図ガイド生成失敗: {err}")

    return saved


# ── メインエントリポイント ────────────────────────────────────────────────────

def create_composition_guide(
    record: dict,
    form: str,
    stage_dir: Path,
    scene: str = "",
    background: str = "",
    style: str = "",
    work_key: str = "#Works_NumberTales",
) -> list[Path]:
    """DB 参照画像から構図ガイドを生成して stage_dir に保存する。

    Adobe Lightroom / Photoshop API が利用可能な場合はそちらを使い、
    利用不可の場合は PIL でローカル処理する。

    Parameters
    ----------
    record:     find_character() が返すキャラクターレコード
    form:       "corefolder" または "humanoid"
    stage_dir:  保存先ディレクトリ (通常は stage2_rough/)
    scene:      シーン説明 (背景色の推定に使用)
    background: 背景ヒント
    style:      作風ヒント
    work_key:   作品キー

    Returns
    -------
    保存した構図ガイド画像のパスリスト
    """
    stage_dir.mkdir(parents=True, exist_ok=True)
    num = record["data"]["Num"]

    refs = collect_reference_images(record, form=form)
    ref_paths = refs["local_paths"]
    if not ref_paths:
        print(f"[WARN] Stage2-Adobe: #{num:03d} の参照画像が見つかりません。構図ガイドをスキップします。")
        return []

    print(f"[Stage2-Adobe] 構図ガイド生成開始: #{num:03d} {form} / 参照 {len(ref_paths)} 件")

    client_id = os.environ.get("FIREFLY_CLIENT_ID")
    client_secret = os.environ.get("FIREFLY_CLIENT_SECRET")
    storage_type = os.environ.get("ADOBE_STORAGE_TYPE", "local").lower()

    # Adobe API モード (外部ストレージ設定済み + 認証情報あり)
    if storage_type != "local" and client_id and client_secret:
        try:
            token = _get_ims_token(client_id, client_secret)
            result = _create_composition_guide_adobe(
                ref_paths, stage_dir, scene, background, style, num, form,
                token, client_id,
            )
            if result:
                return result
        except Exception as err:
            print(f"[WARN] Adobe Lightroom API 失敗: {err}. PIL fallback へ切り替えます。")

    # PIL フォールバック
    return _create_composition_guide_pil(
        ref_paths, stage_dir, scene, background, style, num, form
    )


def main() -> None:
    import argparse
    from dotenv import load_dotenv
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="DB 参照画像から構図ガイドを生成する (Adobe Lightroom API or PIL)"
    )
    parser.add_argument("--num", type=int, required=True, help="キャラクター番号")
    parser.add_argument(
        "--form", choices=["corefolder", "humanoid"], default="corefolder"
    )
    parser.add_argument("--work", default="#Works_NumberTales")
    parser.add_argument("--out", default="output/composition_test")
    parser.add_argument("--scene", default="")
    parser.add_argument("--background", default="")
    parser.add_argument("--style", default="")
    args = parser.parse_args()

    record = find_character(args.num, args.work)
    if record is None:
        sys.exit(f"[ERROR] キャラクター #{args.num} が見つかりません。")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = create_composition_guide(
        record, args.form, out_dir,
        scene=args.scene, background=args.background, style=args.style,
        work_key=args.work,
    )
    if paths:
        print(f"\n[完了] {len(paths)} 件の構図ガイドを生成しました。")
        for p in paths:
            print(f"  {p}")
    else:
        print("\n[完了] 構図ガイドは生成されませんでした。")


if __name__ == "__main__":
    main()
