"""Simple in-memory OAuth 2.0 Authorization Server Provider for FastMCP.

個人専用サーバ向け。認可リクエストは、合言葉（環境変数 ``MCP_AUTH_PASSPHRASE``）を
確認画面（``/consent``）で入力したときだけ承認する。合言葉が未設定のサーバーは、認可をすべて断る
（URL を知っているだけでは、課金を伴う生成を呼べないようにするため）。
トークンはプロセス内メモリに保持されるためサービス再起動でリセットされる。
"""
from __future__ import annotations

import hmac
import html
import os
import secrets
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

PASSPHRASE_ENV = "MCP_AUTH_PASSPHRASE"
CONSENT_PATH = "/consent"
PENDING_TTL = 600          # 確認画面を開いてから承認までの猶予（秒）
MAX_PENDING = 200          # 同時に待たせる認可リクエストの数。超えたら古いものから捨てる
MAX_ATTEMPTS = 5           # 1 件の認可リクエストで合言葉を試せる回数
LOCKOUT_FAILURES = 10      # LOCKOUT_WINDOW 秒のあいだにこの回数まちがえたら、全体をしばらく止める
LOCKOUT_WINDOW = 600


@dataclass
class _Pending:
    client_id: str
    params: AuthorizationParams
    expires_at: float
    attempts: int = 0


class SimpleOAuthProvider(OAuthAuthorizationServerProvider):
    """個人用 MCP サーバ向け in-memory OAuth 2.0 プロバイダ。

    単一ユーザーの個人サーバを想定した最小実装。認可は合言葉の確認画面を通す。
    ``issuer_url`` はこのサーバーの公開 URL（確認画面へのリダイレクト先を組み立てる）。
    ``passphrase`` を省くと環境変数 ``MCP_AUTH_PASSPHRASE`` を読む。
    """

    def __init__(self, issuer_url: str = "", passphrase: str | None = None) -> None:
        self._issuer_url = issuer_url.rstrip("/")
        self._passphrase = (os.getenv(PASSPHRASE_ENV, "") if passphrase is None else passphrase).strip()
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._auth_codes: dict[str, AuthorizationCode] = {}
        self._access_tokens: dict[str, AccessToken] = {}
        self._refresh_tokens: dict[str, RefreshToken] = {}
        self._pending: dict[str, _Pending] = {}
        self._failures: list[float] = []

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(
        self, client_info: OAuthClientInformationFull
    ) -> OAuthClientInformationFull:
        self._clients[client_info.client_id] = client_info
        return client_info

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        # 合言葉の確認画面へ送る。認可コードは、合言葉が合ったときに approve() が発行する
        if not self._passphrase:
            raise AuthorizeError(
                error="access_denied",
                error_description=f"{PASSPHRASE_ENV} is not set on this server; authorization is disabled.",
            )
        self._drop_expired()
        while len(self._pending) >= MAX_PENDING:      # 手続きを大量に始められても、メモリーを使い切らない
            del self._pending[next(iter(self._pending))]
        request_id = secrets.token_urlsafe(24)
        self._pending[request_id] = _Pending(client.client_id, params, time.time() + PENDING_TTL)
        return f"{self._issuer_url}{CONSENT_PATH}?rid={request_id}"

    # ── 合言葉の確認 ───────────────────────────────────────────────

    def is_pending(self, request_id: str) -> bool:
        self._drop_expired()
        return request_id in self._pending

    def describe_pending(self, request_id: str) -> tuple[str, str]:
        """確認画面に出す、接続を求めているアプリの名前と、承認後の戻り先のホスト。

        他人が用意した接続（承認すると、その人のアプリへトークンが渡る）に、気付かず合言葉を入れないようにする。
        """
        pending = self._pending.get(request_id)
        if pending is None:
            return "", ""
        client = self._clients.get(pending.client_id)
        return (getattr(client, "client_name", None) or "（名前なし）",
                urlparse(str(pending.params.redirect_uri)).netloc)

    def locked_out(self) -> bool:
        cutoff = time.time() - LOCKOUT_WINDOW
        self._failures = [stamp for stamp in self._failures if stamp > cutoff]
        return len(self._failures) >= LOCKOUT_FAILURES

    def approve(self, request_id: str, passphrase: str) -> str | None:
        """合言葉が合えば認可コードを発行し、クライアントへ戻るリダイレクト先を返す。合わなければ None。"""
        self._drop_expired()
        pending = self._pending.get(request_id)
        if pending is None or self.locked_out():
            return None
        if not hmac.compare_digest(passphrase.encode("utf-8"), self._passphrase.encode("utf-8")):
            self._failures.append(time.time())
            pending.attempts += 1
            if pending.attempts >= MAX_ATTEMPTS:
                del self._pending[request_id]
            return None
        del self._pending[request_id]
        params = pending.params
        code = secrets.token_urlsafe(32)
        self._auth_codes[code] = AuthorizationCode(
            code=code,
            client_id=pending.client_id,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            expires_at=time.time() + 300,  # 5 分
            scopes=list(params.scopes or []),
            code_challenge=params.code_challenge,
            code_challenge_method="S256",
        )
        return construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state)

    def _drop_expired(self) -> None:
        now = time.time()
        for request_id in [key for key, item in self._pending.items() if item.expires_at < now]:
            del self._pending[request_id]

    # ── トークン ───────────────────────────────────────────────────

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> AuthorizationCode | None:
        code_obj = self._auth_codes.get(authorization_code)
        if code_obj is None or code_obj.expires_at < time.time():
            return None
        return code_obj

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        self._auth_codes.pop(authorization_code.code, None)
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        expires_in = 86400  # 24 時間

        self._access_tokens[access_token] = AccessToken(
            token=access_token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(time.time() + expires_in),
        )
        self._refresh_tokens[refresh_token] = RefreshToken(
            token=refresh_token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
        )
        return OAuthToken(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            refresh_token=refresh_token,
            scope=" ".join(authorization_code.scopes),
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        tok = self._access_tokens.get(token)
        if tok is None:
            return None
        if tok.expires_at and tok.expires_at < time.time():
            return None
        return tok

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> RefreshToken | None:
        return self._refresh_tokens.get(refresh_token)

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        new_access = secrets.token_urlsafe(32)
        expires_in = 86400
        effective_scopes = scopes if scopes else refresh_token.scopes

        self._access_tokens[new_access] = AccessToken(
            token=new_access,
            client_id=client.client_id,
            scopes=effective_scopes,
            expires_at=int(time.time() + expires_in),
        )
        return OAuthToken(
            access_token=new_access,
            token_type="bearer",
            expires_in=expires_in,
            refresh_token=refresh_token.token,
            scope=" ".join(effective_scopes),
        )


_PAGE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>{title}</title>
<style>body{{font-family:sans-serif;max-width:26rem;margin:4rem auto;padding:0 1rem;line-height:1.7}}
input,button{{font-size:1rem;padding:.5rem;width:100%;box-sizing:border-box;margin-top:.5rem}}
.error{{color:#b00020}}</style></head>
<body><h1>{title}</h1>{body}</body></html>"""

_FORM = """<p>接続を求めているアプリ: <b>{client}</b><br>承認後の戻り先: <b>{host}</b></p>
<p>心当たりのある接続なら、合言葉を入力してください。心当たりがなければ、入力せずにこの画面を閉じてください。</p>{error}
<form method="post" action="{action}"><input type="hidden" name="rid" value="{rid}">
<input type="password" name="passphrase" autocomplete="current-password" autofocus required>
<button type="submit">接続する</button></form>"""


def register_consent_route(mcp, provider: SimpleOAuthProvider, title: str = "MCP コネクタ") -> None:
    """合言葉の確認画面（GET で表示、POST で照合）を FastMCP サーバーに足す。"""
    from starlette.requests import Request
    from starlette.responses import HTMLResponse, RedirectResponse, Response

    headers = {"Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer"}

    def page(body: str, status: int = 200) -> Response:
        return HTMLResponse(_PAGE.format(title=html.escape(title), body=body), status_code=status, headers=headers)

    def form(request_id: str, error: str = "", status: int = 200) -> Response:
        note = f'<p class="error">{html.escape(error)}</p>' if error else ""
        client, host = provider.describe_pending(request_id)
        return page(_FORM.format(client=html.escape(client), host=html.escape(host), error=note,
                                 action=CONSENT_PATH, rid=html.escape(request_id, quote=True)), status)

    expired = "<p>この接続の手続きは期限が切れたか、試せる回数を超えました。コネクタの接続をやり直してください。</p>"

    @mcp.custom_route(CONSENT_PATH, methods=["GET", "POST"])
    async def consent(request: Request) -> Response:
        if request.method == "GET":
            request_id = request.query_params.get("rid", "")
            return form(request_id) if provider.is_pending(request_id) else page(expired, 400)
        fields = parse_qs((await request.body()).decode("utf-8", errors="replace"))
        request_id = (fields.get("rid") or [""])[0]
        if provider.locked_out():
            return page("<p>合言葉のまちがいが続いたため、しばらく受け付けません。10 分ほど待ってからやり直してください。</p>", 429)
        redirect = provider.approve(request_id, (fields.get("passphrase") or [""])[0])
        if redirect:
            return RedirectResponse(redirect, status_code=302, headers={"Cache-Control": "no-store"})
        if provider.is_pending(request_id):
            return form(request_id, "合言葉が違います。", 401)
        return page(expired, 400)
