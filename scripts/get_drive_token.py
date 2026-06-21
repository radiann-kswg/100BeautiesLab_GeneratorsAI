"""Drive OAuth リフレッシュトークン取得ヘルパー。

OUTPUT_SINK=drive を使う際、SA はストレージ容量がないため
ユーザー OAuth でアップロードする必要がある。
このスクリプトをローカル PC で一度だけ実行し、表示された
DRIVE_REFRESH_TOKEN を GCE の .env に貼り付けること。

事前準備:
  1. GCP Console → APIs & Services → 認証情報
     → 「認証情報を作成」→「OAuth クライアント ID」
     → アプリの種類: デスクトップ アプリ → 作成
  2. クライアント ID とシークレットをメモ

実行:
  pip install google-auth-oauthlib
  python scripts/get_drive_token.py
"""

import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
except ImportError:
    print("google-auth-oauthlib が必要です: pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

client_id = input("DRIVE_CLIENT_ID を貼り付け: ").strip()
client_secret = input("DRIVE_CLIENT_SECRET を貼り付け: ").strip()

client_config = {
    "installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uris": ["http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

print("\n" + "=" * 60)
print("以下を GCE の .env に追記してください:")
print("=" * 60)
print(f"DRIVE_CLIENT_ID={client_id}")
print(f"DRIVE_CLIENT_SECRET={client_secret}")
print(f"DRIVE_REFRESH_TOKEN={creds.refresh_token}")
print("=" * 60)
