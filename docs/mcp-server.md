# MCP サーバ運用ガイド（ナンバーテールズ画像生成）

`src/mcp_server/` は、画像生成パイプライン（`src.pipeline.image_pipeline`）を
**MCP ツールとして公開**するサーバです。ローカル(stdio)でもリモート(Cloud Run / Streamable HTTP)でも動きます。

> 関連: [usage-generation.md](usage-generation.md) / [usage-iterate.md](usage-iterate.md) / [output-and-logs.md](output-and-logs.md)

---

## 1. 公開ツール

| ツール名 | 対応する入口 | 概要 |
|---|---|---|
| `numbertales_generate_character` | `run_image_pipeline` | 単体キャラ生成（Stage 1〜5） |
| `numbertales_generate_joint` | `run_combined_pipeline` | 複数キャラを 1 枚に合同生成 |
| `numbertales_generate_from_natural` | `parse_generation_request` → 上記 | 自然文からディスパッチ |
| `numbertales_iterate` | `run_image_pipeline(iterate_from=…)` | i2i 改稿 |
| `numbertales_job_status` | — | ジョブ進捗・完成画像リンク照会（読取専用） |
| `numbertales_list_runs` | — | 直近ジョブ一覧（読取専用） |

### 非同期ジョブ方式

パイプラインは数分かかるため、生成系ツールは **ジョブを登録して即 `job_id` を返す**。
完成画像のリンクは `numbertales_job_status` をポーリングして取得する。

```
generate_character → {"job_id": "ab12…", "status": "pending"}
            ↓ (数分後)
job_status(job_id) → {"status": "succeeded", "result": {"outputs": [ {url …} ]}}
```

---

## 2. 環境変数

| 変数 | 既定 | 説明 |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio`（ローカル）/ `streamable-http`（リモート） |
| `PORT` | `8080` | HTTP 待受ポート（Cloud Run が注入） |
| `HOST` | `0.0.0.0` | 待受ホスト |
| `MCP_ISSUER_URL` | — | HTTP 運用時の公開 URL（OAuth discovery issuer）。例: `https://mcp.numbertales-radiann.net` |
| `OUTPUT_SINK` | `local` | `local` / `drive` / `gcs` |
| `DRIVE_FOLDER_ID` | — | `OUTPUT_SINK=drive` 時のアップロード先フォルダ ID |
| `DRIVE_CLIENT_ID` | — | Drive OAuth クライアント ID（GCP Console で発行） |
| `DRIVE_CLIENT_SECRET` | — | Drive OAuth クライアントシークレット |
| `DRIVE_REFRESH_TOKEN` | — | Drive OAuth リフレッシュトークン（`scripts/get_drive_token.py` で取得） |
| `GCS_BUCKET` | — | `OUTPUT_SINK=gcs` 時のバケット名 |
| `GCS_PREFIX` | `numbertales` | GCS オブジェクトキー接頭辞 |
| `GCS_SIGNED_URL_TTL_SEC` | `604800` | 署名 URL の有効秒数（7 日） |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | SA キーファイルのパス（GCS 署名 URL 生成に必要） |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` / `CANVA_ACCESS_TOKEN` | — | パイプラインが使う API キー（`.env` 互換） |
| `OUTPUT_BASE_DIR` | — | 生成画像のベースディレクトリ |

> **重要**: リモート実行では `OUTPUT_SINK=local` だと生成画像がコンテナ内に残り手元に届きません。
> 必ず `drive` か `gcs` を指定してください。
>
> **Drive 利用時の注意**: GCE のデフォルト SA は Drive ストレージ容量を持たないため
> `storageQuotaExceeded (403)` が発生します。`DRIVE_REFRESH_TOKEN` を設定して
> ユーザー OAuth 認証を使うことで解消します（詳細: [docs/setup.md](setup.md) §4）。

---

## 3. ローカル実行（stdio）

```bash
pip install -r requirements-mcp.txt
# stdio で起動（Claude Desktop 等のローカル MCP クライアントから接続）
python -m src.mcp_server.server
```

Claude Desktop の `claude_desktop_config.json` 例:

```json
{
  "mcpServers": {
    "numbertales": {
      "command": "python",
      "args": ["-m", "src.mcp_server.server"],
      "cwd": "/path/to/100BeautiesLab_GeneratorsAI",
      "env": { "MCP_TRANSPORT": "stdio", "OUTPUT_SINK": "local" }
    }
  }
}
```

---

## 4. Docker（ローカル / リモート共通）

```bash
docker build -t numbertales-mcp .
docker run --rm -p 8080:8080 \
  -e MCP_TRANSPORT=streamable-http \
  -e OUTPUT_SINK=local \
  --env-file .env \
  numbertales-mcp
# → http://localhost:8080/mcp で待受
```

---

## 5. Google Cloud Run へのデプロイ（先輩が実行）

> 以下は **GCP アカウント側の操作**のため、ご自身で実行してください。
> `PROJECT_ID` / `REGION` は環境に合わせて置き換えます。

### 5.1 事前準備

```bash
gcloud auth login
gcloud config set project PROJECT_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
    secretmanager.googleapis.com cloudbuild.googleapis.com
```

### 5.2 API キーを Secret Manager に登録

```bash
printf '%s' "$GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=-
printf '%s' "$OPENAI_API_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=-
printf '%s' "$CANVA_ACCESS_TOKEN" | gcloud secrets create CANVA_ACCESS_TOKEN --data-file=-
```

### 5.3 出力先の準備

- **Drive を使う場合**: アップロード先フォルダを作成し、デプロイ先サービスアカウントと共有。`DRIVE_FOLDER_ID` を控える。
- **GCS を使う場合**: バケットを作成し、サービスアカウントに `roles/storage.objectAdmin` と `roles/iam.serviceAccountTokenCreator`（署名 URL 用）を付与。

### 5.4 ビルド & デプロイ

```bash
gcloud run deploy numbertales-mcp \
  --source . \
  --region REGION \
  --port 8080 \
  --cpu 2 --memory 2Gi \
  --no-cpu-throttling \
  --timeout 3600 \
  --min-instances 1 --max-instances 1 \
  --set-env-vars MCP_TRANSPORT=streamable-http,OUTPUT_SINK=drive,DRIVE_FOLDER_ID=xxxx \
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,CANVA_ACCESS_TOKEN=CANVA_ACCESS_TOKEN:latest
```

> **`--min-instances 1 --max-instances 1` は必須**です。ジョブはプロセス内メモリに
> 保持されるため、複数インスタンスにスケールすると別インスタンスのジョブが
> `job_status` から見えなくなります。`--no-cpu-throttling` はレスポンス後も
> バックグラウンドのジョブを走らせ続けるために指定します。

### 5.5 リモート MCP コネクタとして登録

デプロイ後の URL（例 `https://numbertales-mcp-xxxx.run.app/mcp`）を、Claude の
コネクタ設定で **カスタム（リモート / Streamable HTTP）MCP** として追加します。
公開アクセスを避けるため、Cloud Run の認証 + IAM、または前段の認証プロキシを
かけることを推奨します。

---

## 6. GCE（Google Compute Engine）へのデプロイ

Cloud Run 以外に、GCE の常駐プロセスとしてデプロイする構成です。
**詳細な動作確認手順は [docs/usage-mcp-multi-llm-gce.md](usage-mcp-multi-llm-gce.md) を参照してください。**
コスト感・セキュリティ・設計の背景は [`_ideas/mcp-multi-llm-bridge-gce-design.md`](../_ideas/mcp-multi-llm-bridge-gce-design.md) を参照。

### 6.1 インスタンス・配置

```bash
# GCE インスタンス上で実行
git clone https://github.com/radiann-kswg/100BeautiesLab_GeneratorsAI /opt/100beautieslab
cd /opt/100beautieslab
python3 -m venv .venv
.venv/bin/pip install -r requirements-mcp.txt
cp .env.example .env   # GEMINI_API_KEY / OPENAI_API_KEY などを設定
chmod 600 .env
```

### 6.2 MCP_TRANSPORT 環境変数

GCE では HTTP トランスポートを使います（Streamable HTTP）。
`.env` に以下を追記:

```
MCP_TRANSPORT=streamable-http
HOST=127.0.0.1
PORT=8000
MCP_ISSUER_URL=https://mcp.numbertales-radiann.net
OUTPUT_SINK=local          # GCE ローカル保存（または drive / gcs）
```

### 6.3 systemd 常駐

`deploy/numbertales-mcp.service` をコピーして有効化:

```bash
sudo cp deploy/numbertales-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now numbertales-mcp
journalctl -u numbertales-mcp -f
```

### 6.4 HTTPS / リバースプロキシ（Caddy）

```bash
sudo apt install caddy
# deploy/Caddyfile の YOUR_DOMAIN をサブドメインに書き換えてから:
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl enable --now caddy
```

DNS の A レコードを GCE の静的外部 IP に向けると Caddy が自動で Let's Encrypt 証明書を取得します。

### 6.5 Claude カスタムコネクタ登録

1. `claude.ai/customize/connectors` → **「+」→「Add custom connector」**
2. URL に `https://YOUR_DOMAIN/mcp` を入力
3. **「Add」** で確定 → 会話の「+」→ Connectors でトグル ON

---

## 7. 既知の制約 / 今後

- ジョブ状態は**プロセス内メモリ**。再デプロイ・再起動で消える。複数インスタンス不可。
  → 将来は Firestore 等の共有ストアへ差し替え可能（`src/mcp_server/jobs.py` を実装差し替え）。
- 進捗は粗い（pending / running / succeeded / failed）。ステージ単位の細かい進捗は未実装。
- `OUTPUT_SINK=drive|gcs` は依存ライブラリ・クレデンシャルが無い場合、エラーで落とさず
  `local` にフォールバックし結果の `note` に理由を残す。
- `drive` シンクのアップロードは **サーバ自身のサービスアカウント**で行う（Claude の
  Drive コネクタとは別物）。フォルダをそのサービスアカウントと共有しておくこと。
