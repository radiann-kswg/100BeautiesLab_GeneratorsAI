"""生成画像の出力アダプタ（local / drive / gcs 切替）。

環境変数 ``OUTPUT_SINK`` で送り先を選ぶ:

- ``local`` (既定): ローカルパスをそのまま返す（リモート実行時は手元に届かない点に注意）
- ``drive``       : Google Drive のフォルダにアップロードし webViewLink を返す
- ``gcs``         : Google Cloud Storage バケットにアップロードし署名 URL を返す

Stage 別シンクの挙動:
  - Stage3/4 (中間画像): ``publish_intermediate()`` → GCS のみ（Drive には上げない）
  - Stage5 (完成画像):   ``publish()`` → 設定シンクへ通常アップロード

GCS の接頭辞の下は、用途で分ける:
  - ``<接頭辞>/…``                       Stage3/4 の中間画像（従来どおり）
  - ``<接頭辞>/uploads/<日付>/…``        依頼者の入力画像。``create_upload_slot()`` の署名付き URL で受け取り、
                                         ``read_object()`` で読む（バケットのライフサイクルで 7 日後に消す）
  - ``<接頭辞>/runs/<実行フォルダー名>/…`` 改稿の起点を残すための ``pipeline_summary.json``・完成画像・Stage 1 の土台。
                                         ``store_run()`` で置き、``restore_run()`` で出力フォルダーへ戻す

いずれのシンクも「使う時だけ」依存ライブラリを遅延 import する。
依存やクレデンシャルが欠けている場合は例外で落とさず、local にフォールバックして
``note`` に理由を記録する（サーバ全体が止まらないようにするため）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
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


def _err_detail(e: Exception, limit: int = 200) -> str:
    """例外を「型名: メッセージ」形式で返す（note 用・長すぎる場合は切り詰め）。"""
    msg = str(e).replace("\n", " ").strip()
    detail = f"{type(e).__name__}: {msg}" if msg else type(e).__name__
    return detail[:limit] + ("…" if len(detail) > limit else "")


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
        return _fallback(files, f"Drive 認証失敗 ({_err_detail(e)})")

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
            item["note"] = f"Drive アップロード失敗 ({_err_detail(e)})。"
            results.append(item)
    return results


# ── Google Cloud Storage ────────────────────────────────────────
def _sign(blob: Any, ttl: int, **options: Any) -> str:
    """blob の v4 署名 URL を返す（ADC/IAM 署名フォールバック付き）。署名できなければ例外。"""
    from datetime import timedelta
    options = {"version": "v4", "expiration": timedelta(seconds=ttl), "method": "GET", **options}
    try:
        return blob.generate_signed_url(**options)
    except Exception:  # noqa: BLE001
        # Cloud Run / GCE の ADC は鍵ファイル無しでも IAM Credentials 経由で署名できる
        import google.auth  # type: ignore
        from google.auth.transport import requests as _greq  # type: ignore

        _creds, _ = google.auth.default()
        _creds.refresh(_greq.Request())
        _sa_email = getattr(_creds, "service_account_email", None)
        _token = getattr(_creds, "token", None)
        if not (_sa_email and _token):
            raise
        return blob.generate_signed_url(**options, service_account_email=_sa_email, access_token=_token)


def _signed_url(blob: Any, bucket_name: str, object_key: str, ttl: int) -> str:
    """blob の読み取り用の署名 URL を返す。失敗時は gs://。"""
    try:
        return _sign(blob, ttl)
    except Exception:  # noqa: BLE001
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
        return _fallback(files, f"GCS クライアント初期化失敗 ({_err_detail(e)})")

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
            item["note"] = f"GCS アップロード失敗 ({_err_detail(e)})。"
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


# ── 入力画像の受け取りと、自分の接頭辞の下の読み取り ─────────────
# 依頼者の入力画像は <接頭辞>/uploads/<日付>/ に、署名付き PUT URL で受け取る（バケットのライフサイクルで 7 日後に消す）。
UPLOAD_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
UPLOAD_MAX_BYTES = 10 * 1024 * 1024
UPLOAD_TTL_SEC = 15 * 60


def _gcs_prefix() -> str:
    return os.getenv(ENV_GCS_PREFIX, "numbertales").strip("/") or "numbertales"


def _bucket() -> Any:
    """設定されたバケットを返す。使えない理由は ValueError で返す。"""
    bucket_name = os.getenv(ENV_GCS_BUCKET, "").strip()
    if not bucket_name:
        raise ValueError(f"{ENV_GCS_BUCKET} 未設定")
    try:
        from google.cloud import storage  # type: ignore
    except ImportError as e:
        raise ValueError("google-cloud-storage 未インストール") from e
    try:
        return storage.Client().bucket(bucket_name)
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"GCS クライアント初期化失敗 ({_err_detail(e)})") from e


def read_object(object_key: str, max_bytes: int = UPLOAD_MAX_BYTES) -> bytes:
    """自分の接頭辞の下のオブジェクト 1 件を読む（同じバケットの、ほかの用途の物は読まない）。

    読めない理由は ValueError で返す。
    """
    prefix = _gcs_prefix()
    key = (object_key or "").strip().lstrip("/")
    if not key.startswith(f"{prefix}/") or ".." in key.split("/"):
        raise ValueError(f"扱えるのは {prefix}/ の下だけです: {object_key}")
    try:
        blob = _bucket().get_blob(key)
    except ValueError:
        raise
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"GCS からの取得に失敗 ({_err_detail(e)})") from e
    if blob is None:
        raise ValueError(f"GCS に見つかりません（アップロードが済んでいないか、保存期間を過ぎています）: {key}")
    if int(getattr(blob, "size", 0) or 0) > max_bytes:
        raise ValueError(f"大きすぎます（上限 {max_bytes // (1024 * 1024)}MB）: {key}")
    try:
        return blob.download_as_bytes()
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"GCS からの取得に失敗 ({_err_detail(e)})") from e


def create_upload_slot(content_type: str) -> dict[str, Any]:
    """入力画像 1 枚ぶんの置き場（署名付き PUT URL と object_key）を作る。

    URL は ``UPLOAD_TTL_SEC`` 秒だけ有効で、宣言した形式と ``UPLOAD_MAX_BYTES`` までの大きさしか
    受け付けない。中身の形式と大きさは、使う時にも確かめる。

    Returns
    -------
    dict::
        {
          "object_key": str, "upload_url": str, "method": "PUT",
          "headers": {...},          # アップロード時に必ず付けるヘッダー
          "expires_in_seconds": int, "max_bytes": int,
          "note": str,               # 作れなかった理由（作れたときは空）
        }
    """
    import secrets
    from datetime import datetime, timezone

    out: dict[str, Any] = {"object_key": "", "upload_url": "", "method": "PUT", "headers": {},
                           "expires_in_seconds": UPLOAD_TTL_SEC, "max_bytes": UPLOAD_MAX_BYTES, "note": ""}
    content_type = (content_type or "").strip().lower()
    suffix = UPLOAD_TYPES.get(content_type)
    if not suffix:
        out["note"] = f"content_type は {' / '.join(UPLOAD_TYPES)} のいずれかを指定してください"
        return out
    key = f"{_gcs_prefix()}/uploads/{datetime.now(timezone.utc):%Y%m%d}/{secrets.token_hex(16)}{suffix}"
    size_range = {"x-goog-content-length-range": f"0,{UPLOAD_MAX_BYTES}"}
    try:
        url = _sign(_bucket().blob(key), UPLOAD_TTL_SEC, method="PUT", content_type=content_type, headers=size_range)
    except Exception as e:  # noqa: BLE001
        out["note"] = f"アップロード用の URL を作れません ({_err_detail(e)})"
        return out
    out.update(object_key=key, upload_url=url, headers={"Content-Type": content_type, **size_range})
    return out


# ── 共通ヘルパ ──────────────────────────────────────────────────
# ── 実行の記録の保存と復元（改稿の起点） ────────────────────────
_RUN_FILE_MAX_BYTES = 40 * 1024 * 1024
_RUN_SUMMARY = "pipeline_summary.json"
#: 軽い加筆 (quick) が使い回す、Stage 1 の土台
_RUN_EXTRA_FILES = ("stage1_prompt/prompt_base_gemini.txt",)


def _run_prefix(run_id: str) -> str:
    return f"{_gcs_prefix()}/runs/{Path(run_id).name}/"


def run_relative(path: str, run_name: str) -> PurePosixPath | None:
    """記録に残ったパス（実行したサーバーでの絶対・相対パス）を、実行フォルダーからの相対パスにする。

    実行フォルダーの外を指すパスと、``..`` を含むパスは None。
    """
    parts = PurePosixPath(str(path).replace("\\", "/")).parts
    if run_name not in parts:
        return None
    tail = parts[len(parts) - 1 - parts[::-1].index(run_name) + 1:]
    if not tail or ".." in tail:
        return None
    return PurePosixPath(*tail)


def run_final_files(summary: dict[str, Any], run_name: str) -> list[PurePosixPath]:
    """``pipeline_summary.json`` の完成画像（``stage5_paths.all``）を、実行フォルダーからの相対パスで返す。"""
    finals = (summary.get("stage5_paths") or {}).get("all") or []
    relatives = (run_relative(str(path), run_name) for path in finals)
    return list(dict.fromkeys(rel for rel in relatives if rel is not None))


def store_run(run_dir: str) -> dict[str, Any]:
    """実行の ``pipeline_summary.json``・完成画像・Stage 1 の土台を GCS に置く。

    サーバーが止まって出力フォルダーが消えたあとも、実行フォルダー名で改稿の起点にできるようにする。
    Returns ``{"stored": [object_key, ...], "note": 置けなかった理由}``。
    """
    root = Path(run_dir)
    out: dict[str, Any] = {"stored": [], "note": ""}
    summary_file = root / _RUN_SUMMARY
    if not summary_file.is_file():
        out["note"] = f"{_RUN_SUMMARY} がありません"
        return out
    try:
        bucket = _bucket()
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
        files = [*run_final_files(summary, root.name), *(PurePosixPath(rel) for rel in _RUN_EXTRA_FILES)]
        for rel in [*files, PurePosixPath(_RUN_SUMMARY)]:      # 記録は、画像がそろってから置く
            local = root.joinpath(*rel.parts)
            if local.is_file():
                key = _run_prefix(root.name) + rel.as_posix()
                bucket.blob(key).upload_from_filename(str(local))
                out["stored"].append(key)
    except ValueError as e:
        out["note"] = str(e)
    except Exception as e:  # noqa: BLE001
        out["note"] = f"GCS への保存に失敗 ({_err_detail(e)})"
    return out


def restore_run(run_id: str, output_base: Path | str) -> Path | None:
    """手元に無い実行の記録と完成画像を、GCS から出力フォルダーへ戻す。戻せたら実行フォルダーのパス。

    戻す先は、生成時と同じ ``<出力フォルダー>/<YYYYMMDD>/<実行フォルダー名>/``。
    """
    name = Path(run_id).name
    try:
        raw = read_object(_run_prefix(name) + _RUN_SUMMARY, _RUN_FILE_MAX_BYTES)
        summary = json.loads(raw)
    except ValueError:                       # 無い・読めない・JSON でない
        return None
    if not isinstance(summary, dict):
        return None
    date = name[:8]
    run_dir = (Path(output_base) / date / name) if date.isdigit() else (Path(output_base) / name)
    for rel in [*run_final_files(summary, name), *(PurePosixPath(rel) for rel in _RUN_EXTRA_FILES)]:
        try:
            data = read_object(_run_prefix(name) + rel.as_posix(), _RUN_FILE_MAX_BYTES)
        except ValueError:
            continue
        target = run_dir.joinpath(*rel.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / _RUN_SUMMARY).write_bytes(raw)     # 最後に置く（途中で止まった復元を「実行あり」と見せない）
    return run_dir


def list_stored_runs(limit: int = 20) -> list[dict[str, Any]]:
    """GCS に残っている実行を、新しい順に ``limit`` 件まで返す。使えなければ空。"""
    try:
        names = sorted((blob.name for blob in _bucket().list_blobs(prefix=f"{_gcs_prefix()}/runs/")
                        if blob.name.endswith(f"/{_RUN_SUMMARY}")), reverse=True)
    except Exception:  # noqa: BLE001 — 一覧は補助。取れなければ、いま動いているジョブだけを見せる
        return []
    rows: list[dict[str, Any]] = []
    for name in names[:limit]:
        try:
            summary = json.loads(read_object(name, _RUN_FILE_MAX_BYTES))
        except ValueError:
            continue
        run_id = PurePosixPath(name).parent.name
        rows.append({
            "run_id": run_id, "status": summary.get("status"),
            "nums": summary.get("nums") or [summary.get("num")],
            "forms": summary.get("forms") or [summary.get("form")],
            "scene_used": summary.get("scene_used", ""),
            "final_count": len(run_final_files(summary, run_id)),
        })
    return rows


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
