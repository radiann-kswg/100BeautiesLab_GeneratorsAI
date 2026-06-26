"""生成画像の出力アダプタ（local / drive / gcs 切替）。

環境変数 ``OUTPUT_SINK`` で送り先を選ぶ:

- ``local`` (既定): ローカルパスをそのまま返す（リモート実行時は手元に届かない点に注意）
- ``drive``       : Google Drive のフォルダにアップロードし webViewLink を返す
- ``gcs``         : Google Cloud Storage バケットにアップロードし署名 URL を返す

Stage 別シンクの挙動:
  - Stage3/4 (中間画像): ``publish_intermediate()`` → GCS のみ（Drive には上げない）
  - Stage5 (完成画像):   ``publish()`` → 設定シンクへ通常アップロード

いずれのシンクも「使う時だけ」依存ライブラリを遅延 import する。
依存やクレデンシャルが欠けている場合は例外で落とさず、local にフォールバックして
``note`` に理由を記録する（サーバ全体が止まらないようにするため）。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# ── 環境変数キー ───────────────────────────────────────────────
ENV_SINK = "OUTPUT_SINK"               # local | drive | gcs
ENV_DRIVE_FOLDER = "DRIVE_FOLDER_ID"   # アップロード先 Drive フォルダ ID
# Drive ユーザー OAuth（SA はストレージ容量 0 のため必須）
ENV_DRIVE_CLIENT_ID     = "DRIVE_CLIENT_ID"
ENV_DRIVE_CLIENT_SECRET = "DRIVE_CLIENT_SECRET"
ENV_DRIVE_REFRESH_TOKEN = "DRIVE_REFRESH_TOKEN"
ENV_GCS_BUCKET = "GCS_BUCKET"          # アップロード先 GCS バケット名
ENV_GCS_PREFIX = "GCS_PREFIX"          # GCS オブジェクトキーの接頭辞（任意）
ENV_SIGNED_TTL = "GCS_SIGNED_URL_TTL_SEC"  # 署名 URL の有効秒数（既定 7 日）

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def current_sink() -> str:
    """現在の出力シンク名を返す（小文字・未設定なら 'local'）。"""
    return (os.getenv(ENV_SINK) or "local").strip().lower()


def publish(paths: list[str], run_label: str = "") -> list[dict[str, Any]]:
    """完成画像（Stage5）を選択中のシンクへ公開し、参照情報のリストを返す。

    Parameters
    ----------
    paths:      公開対象のローカル画像ファイルパス
    run_label:  リモート格納時の整理用ラベル（run-dir 名など）

    Returns
    -------
    list[dict] — 各要素は以下のスキーマ::

        {
            "name":       str,        # ファイル名
            "local_path": str,        # 生成時のローカルパス
            "url":        str | None, # 取得用 URL（local シンクでは None）
            "sink":       str,        # 実際に使われたシンク (local|drive|gcs)
            "note":       str,        # フォールバック理由など（無ければ空）
        }
    """
    sink = current_sink()
    files = [p for p in paths if p and Path(p).exists()]

    if not files:
        return []

    if sink == "drive":
        return _publish_drive(files, run_label)
    if sink == "gcs":
        return _publish_gcs(files, run_label)
    return _publish_local(files)


def publish_intermediate(paths: list[str], run_label: str = "") -> list[dict[str, Any]]:
    """Stage3/4 の中間画像を GCS のみに公開する（Drive へはアップしない）。

    ``OUTPUT_SINK=drive`` の場合でも中間画像は GCS にのみ保存し、
    Claude チャット上で URL として表示できるようにする。
    ``OUTPUT_SINK=local`` の場合は local フォールバックになる。

    Parameters
    ----------
    paths:      公開対象のローカル画像ファイルパス
    run_label:  リモート格納時の整理用ラベル

    Returns
    -------
    list[dict] — ``publish()`` と同じスキーマ
    """
    sink = current_sink()
    files = [p for p in paths if p and Path(p).exists()]

    if not files:
        return []

    if sink in ("gcs", "drive"):
        return _publish_gcs(files, run_label)
    return _publish_local(files)


# ── local ───────────────────────────────────────────────────────
def _publish_local(files: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "name": Path(p).name,
            "local_path": str(p),
            "url": None,
            "sink": "local",
            "note": "",
        }
        for p in files
    ]


def _fallback(files: list[str], reason: str) -> list[dict[str, Any]]:
    out = _publish_local(files)
    for item in out:
        item["note"] = f"{reason} のため local にフォールバックしました。"
    return out


# ── Google Drive ────────────────────────────────────────────────
def _build_drive_creds():
    """Drive 用認証情報を取得する。

    DRIVE_REFRESH_TOKEN が設定されていればユーザー OAuth 認証（推奨）。
    未設定の場合は ADC（SA 認証）にフォールバックするが、個人 SA は
    Drive ストレージ容量がないため storageQuotaExceeded になることがある。
    """
    refresh_token = os.getenv(ENV_DRIVE_REFRESH_TOKEN, "").strip()
    if refresh_token:
        from google.oauth2.credentials import Credentials  # type: ignore
        from google.auth.transport.requests import Request  # type: ignore
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv(ENV_DRIVE_CLIENT_ID, ""),
            client_secret=os.getenv(ENV_DRIVE_CLIENT_SECRET, ""),
            scopes=["https://www.googleapis.com/auth/drive.file"],
        )
        creds.refresh(Request())
        return creds
    import google.auth  # type: ignore
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    return creds


def _publish_drive(files: list[str], run_label: str) -> list[dict[str, Any]]:
    folder_id = os.getenv(ENV_DRIVE_FOLDER, "").strip()
    if not folder_id:
        return _fallback(files, f"{ENV_DRIVE_FOLDER} 未設定")

    try:
        from googleapiclient.discovery import build  # type: ignore
        from googleapiclient.http import MediaFileUpload  # type: ignore
    except ImportError:
        return _fallback(files, "google-api-python-client 未インストール")

    try:
        creds = _build_drive_creds()
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:  # noqa: BLE001 - 認証は多様な例外を投げる
        return _fallback(files, f"Drive 認証失敗 ({type(e).__name__})")

    results: list[dict[str, Any]] = []
    for p in files:
        path = Path(p)
        try:
            metadata = {"name": _remote_name(path, run_label), "parents": [folder_id]}
            media = MediaFileUpload(str(path), resumable=False)
            created = (
                service.files()
                .create(body=metadata, media_body=media, fields="id, webViewLink")
                .execute()
            )
            results.append(
                {
                    "name": path.name,
                    "local_path": str(path),
                    "url": created.get("webViewLink"),
                    "sink": "drive",
                    "note": "",
                }
            )
        except Exception as e:  # noqa: BLE001
            item = _publish_local([str(path)])[0]
            item["note"] = f"Drive アップロード失敗 ({type(e).__name__})。"
            results.append(item)
    return results


# ── Google Cloud Storage ────────────────────────────────────────
def _signed_url(blob: Any, bucket_name: str, object_key: str, ttl: int) -> str:
    """blob の v4 署名 URL を返す（ADC/IAM 署名フォールバック付き）。失敗時は gs://。"""
    from datetime import timedelta
    try:
        return blob.generate_signed_url(
            version="v4", expiration=timedelta(seconds=ttl), method="GET"
        )
    except Exception:  # noqa: BLE001
        # Cloud Run / GCE の ADC は鍵ファイル無しでも IAM Credentials 経由で署名できる
        try:
            import google.auth  # type: ignore
            from google.auth.transport import requests as _greq  # type: ignore

            _creds, _ = google.auth.default()
            _creds.refresh(_greq.Request())
            _sa_email = getattr(_creds, "service_account_email", None)
            _token = getattr(_creds, "token", None)
            if _sa_email and _token:
                return blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(seconds=ttl),
                    method="GET",
                    service_account_email=_sa_email,
                    access_token=_token,
                )
        except Exception:  # noqa: BLE001
            pass
        return f"gs://{bucket_name}/{object_key}"


def _publish_gcs(files: list[str], run_label: str) -> list[dict[str, Any]]:
    bucket_name = os.getenv(ENV_GCS_BUCKET, "").strip()
    if not bucket_name:
        return _fallback(files, f"{ENV_GCS_BUCKET} 未設定")

    try:
        from google.cloud import storage  # type: ignore
    except ImportError:
        return _fallback(files, "google-cloud-storage 未インストール")

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
    except Exception as e:  # noqa: BLE001
        return _fallback(files, f"GCS クライアント初期化失敗 ({type(e).__name__})")

    prefix = os.getenv(ENV_GCS_PREFIX, "numbertales").strip("/")
    try:
        ttl = int(os.getenv(ENV_SIGNED_TTL, str(7 * 24 * 3600)))
    except ValueError:
        ttl = 7 * 24 * 3600

    results: list[dict[str, Any]] = []
    for p in files:
        path = Path(p)
        object_key = f"{prefix}/{_remote_name(path, run_label)}"
        try:
            blob = bucket.blob(object_key)
            blob.upload_from_filename(str(path))
            results.append(
                {
                    "name": path.name,
                    "local_path": str(path),
                    "url": _signed_url(blob, bucket_name, object_key, ttl),
                    "sink": "gcs",
                    "note": "",
                }
            )
        except Exception as e:  # noqa: BLE001
            item = _publish_local([str(path)])[0]
            item["note"] = f"GCS アップロード失敗 ({type(e).__name__})。"
            results.append(item)
    return results


# ── GCS 署名 URL ヘルパ & 一覧（読み取り専用） ───────────────────
def list_gcs_logs(limit: int = 300, since_days: int = 49) -> dict[str, Any]:
    """GCS 上の生成ログ画像を新しい順に一覧する（読み取り専用）。

    過去 ``since_days`` 日以内に作成された画像オブジェクトを ``GCS_PREFIX`` 配下から拾い、
    署名 URL 付きで返す。ジョブのメモリ履歴に依存しないため、サーバ再起動後や
    過去分のログも参照できる（既定 49 日 = 7 週間）。

    Returns
    -------
    dict::
        {
          "bucket": str, "prefix": str, "since_days": int,
          "count": int,
          "objects": [ {"name","object_key","url","size","created","sink":"gcs"} ],
          "note": str,
        }
    """
    bucket_name = os.getenv(ENV_GCS_BUCKET, "").strip()
    prefix = os.getenv(ENV_GCS_PREFIX, "numbertales").strip("/")
    base: dict[str, Any] = {
        "bucket": bucket_name, "prefix": prefix, "since_days": since_days,
        "count": 0, "objects": [], "note": "",
    }
    if not bucket_name:
        base["note"] = f"{ENV_GCS_BUCKET} 未設定"
        return base
    try:
        from google.cloud import storage  # type: ignore
    except ImportError:
        base["note"] = "google-cloud-storage 未インストール"
        return base
    try:
        client = storage.Client()
    except Exception as e:  # noqa: BLE001
        base["note"] = f"GCS クライアント初期化失敗 ({type(e).__name__})"
        return base

    try:
        ttl = int(os.getenv(ENV_SIGNED_TTL, str(7 * 24 * 3600)))
    except ValueError:
        ttl = 7 * 24 * 3600

    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, since_days))
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)

    # メタデータだけ集めて期間フィルタ → 新しい順に並べ → limit 件に絞ってから署名する
    # （署名は IAM 呼び出しを伴うので件数を絞ってから行う）
    candidates: list[Any] = []
    try:
        for blob in client.list_blobs(bucket_name, prefix=f"{prefix}/"):
            if Path(blob.name).suffix.lower() not in _IMAGE_EXTS:
                continue
            created = getattr(blob, "time_created", None)
            if created is not None and created < cutoff:
                continue
            candidates.append(blob)
    except Exception as e:  # noqa: BLE001
        base["note"] = f"一覧取得中にエラー ({type(e).__name__})"
        return base

    candidates.sort(key=lambda b: getattr(b, "time_created", None) or epoch, reverse=True)
    if limit and len(candidates) > limit:
        candidates = candidates[:limit]

    objects: list[dict[str, Any]] = []
    for blob in candidates:
        created = getattr(blob, "time_created", None)
        objects.append({
            "name": Path(blob.name).name,
            "object_key": blob.name,
            "url": _signed_url(blob, bucket_name, blob.name, ttl),
            "size": int(getattr(blob, "size", 0) or 0),
            "created": created.isoformat() if created else "",
            "sink": "gcs",
        })

    base["objects"] = objects
    base["count"] = len(objects)
    return base


def fetch_gcs_image_b64(object_key: str) -> dict[str, Any]:
    """GCS オブジェクトの画像バイトを base64 で返す（読み取り専用）。

    ``numbertales_list_gcs_logs`` が返す ``object_key`` を渡すと、画像本体を
    base64 で取得できる。署名 URL に直接アクセスできない環境（アーティファクト等）
    でのインライン表示用。object_key はファイル名のみ（プレフィックスなし）でも受け付ける。

    Returns
    -------
    dict::
        {
          "object_key": str, "name": str, "mime_type": str,
          "content": str,   # base64（失敗時は空文字）
          "size": int,
          "note": str,
        }
    """
    import base64
    import mimetypes

    bucket_name = os.getenv(ENV_GCS_BUCKET, "").strip()
    prefix = os.getenv(ENV_GCS_PREFIX, "numbertales").strip("/")
    out: dict[str, Any] = {
        "object_key": object_key, "name": Path(object_key).name,
        "mime_type": "", "content": "", "size": 0, "note": "",
    }
    if not bucket_name:
        out["note"] = f"{ENV_GCS_BUCKET} 未設定"
        return out
    try:
        from google.cloud import storage  # type: ignore
    except ImportError:
        out["note"] = "google-cloud-storage 未インストール"
        return out

    # フルキー(numbertales/...)でもファイル名のみでも受け付ける
    key = (object_key or "").strip().lstrip("/")
    if not key:
        out["note"] = "object_key が空です"
        return out
    if prefix and not key.startswith(prefix + "/") and "/" not in key:
        key = f"{prefix}/{key}"

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(key)
        data = blob.download_as_bytes()
    except Exception as e:  # noqa: BLE001
        out["note"] = f"GCS 取得失敗 ({type(e).__name__})"
        return out

    mime = getattr(blob, "content_type", None) or mimetypes.guess_type(key)[0] or "image/jpeg"
    out["name"] = Path(key).name
    out["object_key"] = key
    out["mime_type"] = mime
    out["size"] = len(data)
    out["content"] = base64.b64encode(data).decode("ascii")
    return out


# ── 共通ヘルパ ──────────────────────────────────────────────────
def _remote_name(path: Path, run_label: str) -> str:
    """リモート格納名を組み立てる（run ラベルでの衝突回避用プレフィックス付き）。

    同一 run 内で複数ファイルの basename が衝突する場合（stage5 synth の 3 枚など）、
    親ディレクトリ名（タイムスタンプ入り）を挿入して GCS 上書きを防ぐ。
    """
    label = (run_label or "").strip().replace("/", "_").replace("\\", "_")
    parent = path.parent.name
    # 親が "." や run_label と同一のときはそのまま
    if parent and parent != "." and parent != label:
        unique_name = f"{parent}_{path.name}"
    else:
        unique_name = path.name
    return f"{label}__{unique_name}" if label else unique_name
