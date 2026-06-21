# GCE MCP サーバ → Google Drive 出力対応（2026-06-21）

## 概要

Claude.ai カスタムコネクタ経由でナンバーテールズ画像生成パイプラインを呼び出せる
GCE MCP サーバ環境を構築し、生成画像を Google Drive に自動保存できるようにした。

## 実施内容

### 1. MCP 基盤構築（前セッション分・参照のみ）

- FastMCP (Streamable HTTP) + Caddy リバースプロキシで GCE 常駐サーバを構築済み
- `src/mcp_server/auth.py` の `SimpleOAuthProvider` で Claude.ai との OAuth 認証を実装済み
- `deploy/numbertales-mcp.service` / `deploy/Caddyfile` を整備済み

### 2. `_creations-ai` サブモジュール GCE 同期

- ローカルの `e630176` コミットが未プッシュで GCE の `git pull` が "not our ref" になる問題を解消
- `git merge --abort → git rebase origin/master → git rebase --skip` でリベース
- メインリポジトリのサブモジュールポインタを更新してプッシュ

### 3. Pipeline フェーズ疎通確認（Claude.ai → MCP → GCE）

- Phase 1: テキスト生成（scene / description / caption）✅
- Phase 2: 単体キャラ画像生成（36(ミトム) corefolder）✅
- Phase 3: 複数キャラ合同生成（確認済み）✅

### 4. GCS 署名 URL 運用設定

- IAM Credentials API を有効化（`gcloud services enable iamcredentials.googleapis.com`）
- SA に `roles/iam.serviceAccountTokenCreator` を付与
- `GOOGLE_APPLICATION_CREDENTIALS=/opt/100beautieslab/sa-key.json` を `.env` に設定
- `gcs/sign-url` の `--duration` 上限 12h（impersonation 制約）を確認

### 5. GCS 重複ファイル名バグ修正

**ファイル**: `src/mcp_server/output_sink.py`

- **バグ**: stage5 synth の 3 枚がすべて同じ basename を持ち、GCS 上で上書きされて 1 枚だけ残る
- **修正**: `_remote_name()` に親ディレクトリ名（タイムスタンプ入り）を挿入してユニーク化

```python
def _remote_name(path: Path, run_label: str) -> str:
    label = (run_label or "").strip().replace("/", "_").replace("\\", "_")
    parent = path.parent.name
    if parent and parent != "." and parent != label:
        unique_name = f"{parent}_{path.name}"
    else:
        unique_name = path.name
    return f"{label}__{unique_name}" if label else unique_name
```

### 6. Google Drive 出力対応（SA 容量不足 → ユーザー OAuth）

**原因**: GCE のデフォルト SA は Drive ストレージ容量 0 のため `storageQuotaExceeded (403)` が発生。

**対応**:

1. `scripts/get_drive_token.py` を新規作成（ローカルで OAuth フローを回してリフレッシュトークンを取得するヘルパー）
2. `src/mcp_server/output_sink.py` に `_build_drive_creds()` を追加:
   - `DRIVE_REFRESH_TOKEN` 設定時: `google.oauth2.credentials.Credentials` でユーザー OAuth
   - 未設定時: `google.auth.default()` (ADC) にフォールバック（SA 認証）
3. `.env.example` に `DRIVE_CLIENT_ID` / `DRIVE_CLIENT_SECRET` / `DRIVE_REFRESH_TOKEN` を追記

**環境変数一覧**:

| 変数 | 説明 |
|---|---|
| `OUTPUT_SINK` | `drive` に設定 |
| `DRIVE_FOLDER_ID` | アップロード先 Drive フォルダ ID |
| `DRIVE_CLIENT_ID` | GCP Console の OAuth クライアント ID（デスクトップ型） |
| `DRIVE_CLIENT_SECRET` | OAuth クライアントシークレット |
| `DRIVE_REFRESH_TOKEN` | `scripts/get_drive_token.py` で取得 |

**動作確認**: Drive への画像アップロードを確認 ✅

## 残課題

- `_tasks/20260619_multi-char-images-phase2.md` の conceptAlt / designAlt 画像は creations-db に未取り込み（別セッション対応）

## 変更ファイル

| ファイル | 変更内容 |
|---|---|
| `src/mcp_server/output_sink.py` | `_remote_name()` バグ修正 + `_build_drive_creds()` 追加 |
| `scripts/get_drive_token.py` | 新規作成（Drive OAuth トークン取得ヘルパー） |
| `.env.example` | Drive OAuth 変数 3 つ追加 |
| `docs/mcp-server.md` | 環境変数テーブルに Drive OAuth 変数と SA 容量注意を追記 |
| `docs/setup.md` | `.env` セクションに Drive OAuth 変数ブロックを追記 |
| `docs/usage-mcp-multi-llm-gce.md` | Drive 設定手順を詳細化 |
