"""
src/tools/refresh_canva_token.py — Canva OAuth2 PKCE でアクセストークンを再取得し .env を更新する。

手順 (通常フロー):
  1. スクリプトを実行すると認可 URL が表示される。
  2. ブラウザでその URL を開いて Canva にログインし、アクセスを許可する。
  3. ブラウザがローカルサーバーにリダイレクトされ、自動的にトークンを取得する。
  4. .env の CANVA_ACCESS_TOKEN と CANVA_REFRESH_TOKEN が更新される。

手順 (非対話リフレッシュ):
  --use-refresh-token を付けると、CANVA_REFRESH_TOKEN を使ってブラウザなしで更新できる。
  MCP サーバ側で呼ぶ場合は refresh_access_token() を直接 import する。

Usage:
    python -m src.tools.refresh_canva_token
    python -m src.tools.refresh_canva_token --use-refresh-token   # ブラウザ不要
    python -m src.tools.refresh_canva_token --dry-run             # .env を書き換えず表示のみ
    python -m src.tools.refresh_canva_token --env path/to/.env
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import os
import re
import secrets
import sys
import threading
import urllib.parse
import urllib.request
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_REDIRECT_URI = "http://127.0.0.1:3001/oauth/redirect"
_AUTH_BASE_URL = "https://www.canva.com/api"
_TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
_SCOPES = [
    "asset:read",
    "asset:write",
    "brandtemplate:content:read",
    "brandtemplate:meta:read",
    "design:content:read",
    "design:content:write",
    "design:meta:read",
    "profile:read",
]


def _pkce_pair() -> tuple[str, str]:
    """PKCE の code_verifier と code_challenge (S256) を生成する。"""
    verifier = secrets.token_urlsafe(96)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _load_credentials() -> tuple[str, str]:
    """CANVA_CLIENT_ID / CANVA_CLIENT_SECRET を環境変数から取得する。"""
    client_id = os.environ.get("CANVA_CLIENT_ID", "")
    client_secret = os.environ.get("CANVA_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise EnvironmentError(
            "CANVA_CLIENT_ID と CANVA_CLIENT_SECRET が .env に設定されていません。\n"
            "スターターキットの playground/.env を参照して .env に追記してください。"
        )
    return client_id, client_secret


def _build_auth_url(code_challenge: str, state: str, client_id: str) -> str:
    params = urllib.parse.urlencode({
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "scope": " ".join(_SCOPES),
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": _REDIRECT_URI,
        "state": state,
    })
    return f"{_AUTH_BASE_URL}/oauth/authorize?{params}"


def _exchange_code(code: str, code_verifier: str, client_id: str, client_secret: str) -> dict:
    """認可コードをアクセストークンに交換する (Basic Auth + PKCE)。"""
    payload = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": _REDIRECT_URI,
    }).encode("ascii")

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        _TOKEN_URL,
        data=payload,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _wait_for_redirect(expected_state: str, timeout: int = 120) -> str:
    """port 3001 でコールバックを待ち受け、認可コードを返す。"""
    _result: dict[str, str] = {}

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/oauth/redirect":
                self.send_response(404)
                self.end_headers()
                return

            params = dict(urllib.parse.parse_qsl(parsed.query))
            if "error" in params:
                _result["error"] = params["error"]
            elif params.get("state") != expected_state:
                _result["error"] = f"state mismatch (got: {params.get('state')})"
            else:
                _result["code"] = params.get("code", "")

            html = (
                "<html><body style='font-family:sans-serif;padding:2em'>"
                "<h2>認証完了 ✅</h2>"
                "<p>このタブを閉じてターミナルに戻ってください。</p>"
                "</body></html>"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)

        def log_message(self, *_):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 3001), _Handler)
    server.timeout = 2

    def _serve():
        deadline = __import__("time").time() + timeout
        while not _result and __import__("time").time() < deadline:
            server.handle_request()

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    t.join(timeout + 2)
    server.server_close()

    if "error" in _result:
        raise RuntimeError(f"Canva OAuth エラー: {_result['error']}")
    if "code" not in _result:
        raise TimeoutError(f"{timeout} 秒以内にコールバックが届きませんでした。")
    return _result["code"]


def _exchange_refresh_token(refresh_token: str, client_id: str, client_secret: str) -> dict:
    """リフレッシュトークンを使って新しいアクセストークンを取得する (非対話)。"""
    payload = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode("ascii")

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        _TOKEN_URL,
        data=payload,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def refresh_access_token() -> dict:
    """環境変数の CANVA_REFRESH_TOKEN を使ってアクセストークンを非対話的に更新する。

    MCP サーバ等からインポートして呼び出す想定。os.environ を直接更新する。

    Returns
    -------
    dict with keys:
        access_token (str)   — 新しいアクセストークン
        refresh_token (str)  — 新しいリフレッシュトークン (ローテーションされた場合)
    Raises
    ------
    EnvironmentError  — 必要な環境変数が不足
    RuntimeError      — トークン取得失敗
    """
    client_id, client_secret = _load_credentials()
    refresh_token = os.environ.get("CANVA_REFRESH_TOKEN", "").strip()
    if not refresh_token:
        raise EnvironmentError(
            "CANVA_REFRESH_TOKEN が設定されていません。"
            "先に python -m src.tools.refresh_canva_token を実行して初回トークンを取得してください。"
        )

    token_data = _exchange_refresh_token(refresh_token, client_id, client_secret)
    access_token = token_data.get("access_token", "")
    if not access_token:
        raise RuntimeError(f"Canva API からアクセストークンが返りませんでした: {token_data}")

    os.environ["CANVA_ACCESS_TOKEN"] = access_token
    new_refresh = token_data.get("refresh_token", refresh_token)
    os.environ["CANVA_REFRESH_TOKEN"] = new_refresh

    return {"access_token": access_token, "refresh_token": new_refresh}


def _update_env(token: str, env_path: Path, refresh_token: str = "") -> None:
    text = env_path.read_text(encoding="utf-8")

    def _upsert(t: str, key: str, value: str) -> str:
        new_line = f"{key}={value}"
        if re.search(rf"^{key}=", t, re.MULTILINE):
            return re.sub(rf"^{key}=.*$", new_line, t, flags=re.MULTILINE)
        return t.rstrip("\n") + f"\n{new_line}\n"

    text = _upsert(text, "CANVA_ACCESS_TOKEN", token)
    if refresh_token:
        text = _upsert(text, "CANVA_REFRESH_TOKEN", refresh_token)
    env_path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Canva アクセストークンを再取得し .env を更新する"
    )
    parser.add_argument(
        "--use-refresh-token", action="store_true",
        help="CANVA_REFRESH_TOKEN を使ってブラウザなしで更新する (初回以降)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="トークンを取得するが .env を書き換えない",
    )
    parser.add_argument(
        "--env", default=str(_PROJECT_ROOT / ".env"),
        help=".env ファイルのパス (デフォルト: プロジェクトルートの .env)",
    )
    parser.add_argument(
        "--timeout", type=int, default=120,
        help="コールバック待機タイムアウト (秒, デフォルト: 120)",
    )
    args = parser.parse_args()

    # .env を先に読み込む (dotenv がなければ手動ロード)
    env_path_for_load = Path(args.env)
    if env_path_for_load.exists():
        for line in env_path_for_load.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

    # ── 非対話モード (--use-refresh-token) ────────────────────────
    if args.use_refresh_token:
        print("=" * 64)
        print("Canva トークン非対話リフレッシュ")
        print("=" * 64)
        try:
            result = refresh_access_token()
        except (EnvironmentError, RuntimeError) as err:
            print(f"[ERROR] {err}")
            sys.exit(1)

        access_token = result["access_token"]
        refresh_token = result["refresh_token"]
        print(f"[OK] アクセストークン更新完了 (先頭 50 文字): {access_token[:50]}...")

        if args.dry_run:
            print("\n[dry-run] .env は変更しません。")
            return

        env_path = Path(args.env)
        if not env_path.exists():
            print(f"[ERROR] .env が見つかりません: {env_path}")
            sys.exit(1)

        _update_env(access_token, env_path, refresh_token)
        print(f"[OK] {env_path} の CANVA_ACCESS_TOKEN / CANVA_REFRESH_TOKEN を更新しました。")
        return

    # ── 通常フロー (PKCE ブラウザ認証) ───────────────────────────
    try:
        client_id, client_secret = _load_credentials()
    except EnvironmentError as err:
        print(f"[ERROR] {err}")
        sys.exit(1)

    code_verifier, code_challenge = _pkce_pair()
    state = secrets.token_urlsafe(32)
    auth_url = _build_auth_url(code_challenge, state, client_id)

    print("=" * 64)
    print("Canva OAuth2 トークン再取得")
    print("=" * 64)
    print("\n以下の URL をブラウザで開いて Canva にログイン・許可してください:\n")
    print(f"  {auth_url}\n")
    print(f"コールバックを {args.timeout} 秒間待ち受けています (port 3001)...")

    try:
        code = _wait_for_redirect(state, timeout=args.timeout)
    except (TimeoutError, RuntimeError) as err:
        print(f"\n[ERROR] {err}")
        sys.exit(1)

    print("[OK] 認可コードを受信。トークンを交換中...")
    try:
        token_data = _exchange_code(code, code_verifier, client_id, client_secret)
    except Exception as err:
        print(f"[ERROR] トークン交換失敗: {err}")
        sys.exit(1)

    access_token = token_data.get("access_token", "")
    if not access_token:
        print(f"[ERROR] access_token が返ってきませんでした。レスポンス: {token_data}")
        sys.exit(1)

    refresh_token = token_data.get("refresh_token", "")
    print(f"[OK] アクセストークン取得完了 (先頭 50 文字): {access_token[:50]}...")
    if refresh_token:
        print(f"[OK] リフレッシュトークン取得完了 (先頭 20 文字): {refresh_token[:20]}...")

    if args.dry_run:
        print("\n[dry-run] .env は変更しません。")
        print(f"\nCANVA_ACCESS_TOKEN={access_token}")
        if refresh_token:
            print(f"CANVA_REFRESH_TOKEN={refresh_token}")
        return

    env_path = Path(args.env)
    if not env_path.exists():
        print(f"[ERROR] .env が見つかりません: {env_path}")
        sys.exit(1)

    _update_env(access_token, env_path, refresh_token)
    saved = "CANVA_ACCESS_TOKEN"
    if refresh_token:
        saved += " / CANVA_REFRESH_TOKEN"
    print(f"\n[OK] {env_path} の {saved} を更新しました。")
    print("パイプラインを再実行すると Canva エクスポートが通るはずです。"
          + (" 次回以降は --use-refresh-token で更新できます。" if refresh_token else ""))


if __name__ == "__main__":
    main()
