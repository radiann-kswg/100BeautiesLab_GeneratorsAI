"""MCP コネクタの認可（合言葉の確認画面）の回帰テスト。生成 API は使わない。"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcp.server.auth.provider import AuthorizationParams, AuthorizeError  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402
from mcp.shared.auth import OAuthClientInformationFull  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from src.mcp_server import auth  # noqa: E402
from src.mcp_server.state_store import MemoryStore  # noqa: E402

ISSUER = "https://connector.example"
REDIRECT = "https://client.example/callback"


def _client() -> OAuthClientInformationFull:
    return OAuthClientInformationFull(client_id="client-1", redirect_uris=[REDIRECT])


def _params() -> AuthorizationParams:
    return AuthorizationParams(state="state-1", scopes=["mcp"], code_challenge="challenge",
                               redirect_uri=REDIRECT, redirect_uri_provided_explicitly=True)


def _authorize(provider: auth.SimpleOAuthProvider) -> str:
    url = asyncio.run(provider.authorize(_client(), _params()))
    assert url.startswith(f"{ISSUER}/consent?rid=")
    return url.split("rid=", 1)[1]


def test_authorization_is_refused_without_a_passphrase():
    with patch.dict("os.environ", {auth.PASSPHRASE_ENV: ""}):
        provider = auth.SimpleOAuthProvider(ISSUER)
    try:
        asyncio.run(provider.authorize(_client(), _params()))
    except AuthorizeError as error:
        assert error.error == "access_denied"
    else:
        raise AssertionError("合言葉が未設定なのに認可が通った")


def test_authorize_issues_no_code_until_the_passphrase_matches():
    provider = auth.SimpleOAuthProvider(ISSUER, "open-sesame")
    request_id = _authorize(provider)
    assert not provider._auth_codes
    assert provider.approve(request_id, "wrong") is None
    assert not provider._auth_codes and provider.is_pending(request_id)
    redirect = provider.approve(request_id, "open-sesame")
    assert redirect.startswith(REDIRECT) and "state=state-1" in redirect and "code=" in redirect
    code = redirect.split("code=", 1)[1].split("&", 1)[0]
    stored = asyncio.run(provider.load_authorization_code(_client(), code))
    assert stored.client_id == "client-1" and stored.code_challenge == "challenge"
    # 同じ手続きは 1 回しか使えない
    assert provider.approve(request_id, "open-sesame") is None


def test_a_request_is_dropped_after_too_many_wrong_passphrases():
    provider = auth.SimpleOAuthProvider(ISSUER, "open-sesame")
    request_id = _authorize(provider)
    for _ in range(auth.MAX_ATTEMPTS):
        assert provider.approve(request_id, "wrong") is None
    assert not provider.is_pending(request_id)
    assert provider.approve(request_id, "open-sesame") is None


def test_repeated_failures_lock_every_request_for_a_while():
    provider = auth.SimpleOAuthProvider(ISSUER, "open-sesame")
    for _ in range(auth.LOCKOUT_FAILURES):
        provider.approve(_authorize(provider), "wrong")
    assert provider.locked_out()
    request_id = _authorize(provider)
    assert provider.approve(request_id, "open-sesame") is None
    with patch.object(auth.time, "time", return_value=auth.time.time() + auth.LOCKOUT_WINDOW + 1):
        assert not provider.locked_out()


def test_pending_requests_are_capped():
    provider = auth.SimpleOAuthProvider(ISSUER, "open-sesame")
    first = _authorize(provider)
    for _ in range(auth.MAX_PENDING):
        last = _authorize(provider)
    assert len(provider._pending) == auth.MAX_PENDING
    assert not provider.is_pending(first) and provider.is_pending(last)


def test_an_expired_request_cannot_be_approved():
    provider = auth.SimpleOAuthProvider(ISSUER, "open-sesame")
    request_id = _authorize(provider)
    with patch.object(auth.time, "time", return_value=auth.time.time() + auth.PENDING_TTL + 1):
        assert not provider.is_pending(request_id)
        assert provider.approve(request_id, "open-sesame") is None


def test_consent_page_asks_for_the_passphrase_and_redirects_on_success():
    provider = auth.SimpleOAuthProvider(ISSUER, "open-sesame")
    server = FastMCP("auth-test")
    auth.register_consent_route(server, provider, "テスト <コネクタ>")
    asyncio.run(provider.register_client(
        OAuthClientInformationFull(client_id="client-1", redirect_uris=[REDIRECT], client_name="Test <App>")))
    request_id = _authorize(provider)
    with TestClient(server.streamable_http_app(), follow_redirects=False) as http:
        shown = http.get(f"/consent?rid={request_id}")
        assert shown.status_code == 200 and 'type="password"' in shown.text
        # 誰のアプリへ戻るのかを見せる（他人が用意した接続に合言葉を入れないため）
        assert "Test &lt;App&gt;" in shown.text and "<b>client.example</b>" in shown.text
        assert "テスト &lt;コネクタ&gt;" in shown.text and shown.headers["cache-control"] == "no-store"
        assert http.get("/consent?rid=unknown").status_code == 400
        wrong = http.post("/consent", data={"rid": request_id, "passphrase": "wrong"})
        assert wrong.status_code == 401 and "open-sesame" not in wrong.text
        done = http.post("/consent", data={"rid": request_id, "passphrase": "open-sesame"})
        assert done.status_code == 302 and done.headers["location"].startswith(REDIRECT)
        assert http.post("/consent", data={"rid": request_id, "passphrase": "open-sesame"}).status_code == 400


def _sign_in(provider: auth.SimpleOAuthProvider):
    """クライアントを登録し、合言葉で認可してトークンを受け取る。"""
    client = asyncio.run(provider.register_client(
        OAuthClientInformationFull(client_id="client-1", redirect_uris=[REDIRECT], client_name="Test App")))
    redirect = provider.approve(_authorize(provider), "open-sesame")
    code = asyncio.run(provider.load_authorization_code(client, redirect.split("code=", 1)[1].split("&", 1)[0]))
    return client, asyncio.run(provider.exchange_authorization_code(client, code))


def test_sign_in_survives_a_replaced_instance_when_a_store_is_given():
    # 2026-11-21、ジョブを登録した 3 分後に Cloud Run がインスタンスを入れ替え、サインインを求められた
    store = MemoryStore()
    client, token = _sign_in(auth.SimpleOAuthProvider(ISSUER, "open-sesame", store=store))

    replaced = auth.SimpleOAuthProvider(ISSUER, "open-sesame", store=store)      # 入れ替わったあとのインスタンス
    assert not replaced._access_tokens and not replaced._clients
    access = asyncio.run(replaced.load_access_token(token.access_token))
    assert access.client_id == "client-1" and access.scopes == ["mcp"] and access.expires_at > auth.time.time()
    restored = asyncio.run(replaced.get_client("client-1"))
    assert restored.client_name == "Test App" and [str(uri) for uri in restored.redirect_uris] == [REDIRECT]
    refresh = asyncio.run(replaced.load_refresh_token(restored, token.refresh_token))
    renewed = asyncio.run(replaced.exchange_refresh_token(restored, refresh, []))
    assert renewed.access_token != token.access_token and renewed.refresh_token == token.refresh_token
    assert asyncio.run(replaced.load_access_token(renewed.access_token)).client_id == "client-1"

    # 置き場には、トークンそのものを置かない（名前は合言葉を鍵にしたハッシュ、中身に秘密の値は無い）
    stored = json.dumps([list(key) for key in store.items]) + "".join(store.items.values())
    assert token.access_token not in stored and token.refresh_token not in stored and "open-sesame" not in stored
    assert {kind for kind, _ in store.items} == {"oauth-client", "oauth-access", "oauth-refresh"}

    # 置き場を渡さないサーバー（手元の stdio など）は、これまでどおりメモリーだけ
    alone = auth.SimpleOAuthProvider(ISSUER, "open-sesame")
    assert asyncio.run(alone.load_access_token(token.access_token)) is None
    assert asyncio.run(alone.get_client("client-1")) is None


def test_stored_sign_in_is_void_after_the_passphrase_changes_or_the_token_expires():
    store = MemoryStore()
    client, token = _sign_in(auth.SimpleOAuthProvider(ISSUER, "open-sesame", store=store))

    # 合言葉を変えると、保存済みのサインインは全部無効になる（全員が再サインイン）
    changed = auth.SimpleOAuthProvider(ISSUER, "new-passphrase", store=store)
    assert asyncio.run(changed.load_access_token(token.access_token)) is None
    assert asyncio.run(changed.get_client("client-1")) is None
    assert asyncio.run(changed.load_refresh_token(client, token.refresh_token)) is None

    # 期限を過ぎたトークンは通さず、置き場からも消す
    later = auth.SimpleOAuthProvider(ISSUER, "open-sesame", store=store)
    with patch.object(auth.time, "time", return_value=auth.time.time() + auth.ACCESS_TTL + 1):
        assert asyncio.run(later.load_access_token(token.access_token)) is None
        assert asyncio.run(later.load_refresh_token(client, token.refresh_token)) is not None
    assert not any(kind == "oauth-access" for kind, _ in store.items)
    with patch.object(auth.time, "time", return_value=auth.time.time() + auth.REFRESH_TTL + 1):
        fresh = auth.SimpleOAuthProvider(ISSUER, "open-sesame", store=store)
        assert asyncio.run(fresh.load_refresh_token(client, token.refresh_token)) is None


def test_unknown_tokens_do_not_keep_reading_the_store():
    class _Counting(MemoryStore):
        reads = 0

        def get(self, kind, name):
            type(self).reads += 1
            return super().get(kind, name)

    provider = auth.SimpleOAuthProvider(ISSUER, "open-sesame", store=_Counting())
    for _ in range(5):
        assert asyncio.run(provider.load_access_token("made-up-token")) is None
    assert _Counting.reads == 1                         # 同じでたらめなトークンで、置き場を読み続けない
    for index in range(auth.MAX_MISSES + 10):
        asyncio.run(provider.load_access_token(f"made-up-{index}"))
    assert len(provider._misses) <= auth.MAX_MISSES     # 覚えておく数にも上限がある
