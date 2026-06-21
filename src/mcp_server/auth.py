"""Simple in-memory OAuth 2.0 Authorization Server Provider for FastMCP.

個人専用サーバ向け: 認可リクエストを自動承認する（ログイン画面なし）。
トークンはプロセス内メモリに保持されるためサービス再起動でリセットされる。
"""
from __future__ import annotations

import secrets
import time

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken


class SimpleOAuthProvider(OAuthAuthorizationServerProvider):
    """個人用 MCP サーバ向け in-memory OAuth 2.0 プロバイダ。

    認可フローを自動承認する（ユーザー確認画面なし）。
    単一ユーザーの個人サーバを想定した最小実装。
    """

    def __init__(self) -> None:
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._auth_codes: dict[str, AuthorizationCode] = {}
        self._access_tokens: dict[str, AccessToken] = {}
        self._refresh_tokens: dict[str, RefreshToken] = {}

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
        # 個人サーバ: 確認画面なしで即承認し、認可コードを返す
        code = secrets.token_urlsafe(32)
        scopes = list(params.scopes or [])
        self._auth_codes[code] = AuthorizationCode(
            code=code,
            client_id=client.client_id,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri is not None,
            expires_at=time.time() + 300,  # 5 分
            scopes=scopes,
            code_challenge=params.code_challenge,
            code_challenge_method="S256",
        )
        return construct_redirect_uri(
            str(params.redirect_uri),
            code=code,
            state=params.state,
        )

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
