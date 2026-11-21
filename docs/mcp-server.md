# MCP サーバ運用ガイド（ナンバーテールズ画像生成）

`src/mcp_server/` は、画像生成パイプライン（`src.pipeline.image_pipeline`）を
**MCP ツールとして公開**するサーバです。ローカル(stdio)でもリモート(Cloud Run / Streamable HTTP)でも動きます。

> 関連: [usage-generation.md](usage-generation.md) / [usage-iterate.md](usage-iterate.md) / [output-and-logs.md](output-and-logs.md)

---

## 1. 公開ツール

| ツール名 | 対応する入口 | 概要 |
|---|---|---|
| `numbertales_generate_character` | `run_image_pipeline` | 単体キャラ生成（Stage 1〜5）。`costume` で衣装（DB の衣装名か衣装差分の文）、`state` で状態（DB の状態名か、体型と着用物を変える文）を指定可。`field_overrides` で `RaceType` 等の曖昧フィールドを明示指定可（未指定時はシーン文脈から LLM が自動判定） |
| `numbertales_generate_joint` | `run_combined_pipeline` | 複数キャラを 1 枚に合同生成。Stage 3 で単体ラフ + 全体構図ラフを同時生成。`field_overrides` は全キャラ共通の1値（`costume` と同じ扱い）。`states` でキャラクターごとの状態を指定可 |
| `numbertales_create_upload_slot` | `output_sink.create_upload_slot` | 入力画像 1 枚の受け取り口。署名付き PUT URL（15 分有効、10MB まで、PNG・JPEG・WebP）と `object_key` を返す。置き場は GCS の `<GCS_PREFIX>/uploads/<日付>/` で、バケットのライフサイクルで 7 日後に消す。受け取った画像を生成ツールへ渡す `images` は未実装（2026-11-20 時点） |
| `numbertales_generate_from_natural` | `parse_generation_request` → 上記 | 自然文からディスパッチ |
| `numbertales_iterate` | `run_image_pipeline(iterate_from=…)` / `run_quick_edit` | i2i 改稿。GCS URL を `iterate_from` に直接渡せる。`field_overrides` も指定可。`quick: true` で、起点の絵を 1 回だけ編集する軽い加筆。`images` に役割 `base` があれば `iterate_from` を、役割 `markup` があれば `revisions` を省ける |
| `numbertales_job_status` | — | ジョブ進捗・完成画像リンク照会（読取専用）。結果の `run_id`（実行フォルダー名）は、`numbertales_iterate` の `iterate_from` に渡せる |
| `numbertales_list_runs` | — | 直近ジョブ一覧（読取専用）。`stored_runs` に、GCS に残っている実行（新しい順に最大 20 件。`run_id`・状態・キャラクター・完成画像の枚数）も返す |
| `numbertales_get_run_logs` | — | 各ステージの中間ログ・プロンプト・画像 URL 照会（読取専用） |
| `numbertales_answer_reference_warning` | `JobManager.answer_reference` | Stage 2 の画像観察失敗について、利用者の続行/中止の回答を返す |

### 入力画像と事前確認

- 単体・合同・改稿の生成ツールは `images: [{object_key, role, provenance, note}]` を受け取る。先に `numbertales_create_upload_slot` で画像を上げ、返ってきた `object_key` を渡す。役割ごとの枚数と渡すステージ、受け付ける出所は [`usage-iterate.md`](usage-iterate.md) の「入力画像・事前確認・軽い加筆」。自然文のツールは対象外。
- 同じツールに `dry_run: true` を渡すと、ジョブを登録せずに、実行される内容（プロンプトの土台・選べる状態と衣装・公式の参照画像・役割の付いた入力画像）を JSON で返す。課金は無い。検証に通らない入力は `{"status": "error", "message": …}` で返る。本番の前に呼び、結果を利用者に示して承認を得る。
- 出所（`provenance`）は 1 枚ずつ利用者に確かめる。このパイプラインの生成結果には `own_generated` を付けてよい。推測では付けない。

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
| `MCP_ISSUER_URL` | — | HTTP 運用時の公開 URL（OAuth discovery issuer）。例: `https://mcp.numbertales-radiann.net`。HTTP で動かすときは必須（未設定だと起動を断る） |
| `MCP_AUTH_PASSPHRASE` | — | HTTP 運用時の合言葉。コネクタの接続時に確認画面（`/consent`）で入力する。未設定だと接続（OAuth の認可）をすべて断る |
| `MCP_ALLOW_UNAUTHENTICATED` | — | `1` で、`MCP_ISSUER_URL` なし（認証なし）の HTTP を許す。手元の検証専用 |
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

### 改稿の起点を GCS に残す

`OUTPUT_SINK` が `local` 以外で `GCS_BUCKET` があれば、完成画像が出た実行の `pipeline_summary.json`・完成画像・`stage1_prompt/prompt_base_gemini.txt` を、GCS の `<GCS_PREFIX>/runs/<実行フォルダー名>/` にも置く（`output_sink.store_run()`）。Cloud Run のインスタンスが止まって出力フォルダーが消えたあとも、`iterate_from` に `run_id` を渡せば、`output_sink.restore_run()` が出力フォルダーへ戻して改稿を続けられる。`runs/` には消す設定を入れていない。期間を決めてライフサイクルのルールを足すかどうかは、使ってみてから決める。

### Stage 別シンク分離

`OUTPUT_SINK=drive` を設定していても、Stage 3/4 の中間生成物は **GCS のみ**に保存します。
Drive へは Stage 5 完成画像のみアップロードし、Drive が中間画像で埋まることを防ぎます。

| Stage | 保存先 | 説明 |
|---|---|---|
| Stage 3/4 中間画像 | **GCS のみ** | `numbertales_get_run_logs` で署名 URL を取得してチャット上で確認・i2i に使う |
| Stage 3 構図ラフ (合同生成) | **GCS のみ** | `stage_summary.stage3.composition_rough.intermediate` で返す |
| Stage 5 完成画像 | 設定シンク (Drive / GCS) | Drive に上げるのはこの完成画像だけ |

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

### GPT / Codex から利用する

生成本体と MCP は共通で、Claude 専用ではない。Codex のローカルスキルは
`.agents/skills/100btys-lab-imagegen/` をそのまま利用できる。

Codex の MCP 設定例（`~/.codex/config.toml` またはプロジェクトの `.codex/config.toml` に追加）:

```toml
[mcp_servers.numbertales]
command = 'C:\Visual Studio Code UserFile\100BeautiesLab_GeneratorsAI\.venv\Scripts\python.exe'
args = ['-m', 'src.mcp_server.server']
cwd = 'C:\Visual Studio Code UserFile\100BeautiesLab_GeneratorsAI'
env = { MCP_TRANSPORT = 'stdio', OUTPUT_SINK = 'local', PYTHONUTF8 = '1' }
startup_timeout_sec = 30
```

パスは設置先に合わせる。依存関係は `requirements-mcp.txt` から準備する。
API キーは既存の `.env` に置き、設定例に埋め込まない。登録後はクライアントを再起動し、
まず `numbertales_list_runs` で読取接続を確かめる。

ChatGPT Web はローカル TOML を読まない。Developer mode のカスタム MCP アプリに
既存サーバーの HTTPS `/mcp` URL を登録する。利用アカウントの対応と管理者設定を確認し、
OAuth 接続後にツール一覧・`numbertales_list_runs` を確認する。
リモートの完成画像は GCS / Drive シンクのリンクで取得する。
**`SimpleOAuthProvider` は個人用の実装で、接続のたびに合言葉（`MCP_AUTH_PASSPHRASE`）の確認画面を通す。**
合言葉を知っている人を同じ利用者として扱い、利用者ごとの本人確認はしない。合言葉は 1 件の接続で 5 回まで、
全体で 10 分に 10 回まちがえると、しばらく受け付けない。
不特定利用者に公開する場合は本人確認する認証基盤への置換が必要。

公式仕様: [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)、
[ChatGPT Developer mode](https://developers.openai.com/api/docs/guides/developer-mode)。

### 画像観察失敗時の確認

1. 生成ツールでジョブを開始し、`numbertales_job_status` で進捗を取得する。
2. `status=awaiting_confirmation` なら `confirmation.reason` と質問を利用者に表示する。
   ネイティブの質問ダイアログが使えるクライアントではそれを使い、なければ会話で尋ねる。
3. 明示回答後だけ `numbertales_answer_reference_warning` を呼ぶ。

```json
{"params": {"job_id": "取得したジョブID", "request_id": "confirmation内のID", "proceed": true}}
```

`true` は AIHints と既存参照画像だけで課金を伴う生成を再開、`false` は中止。
続行後は同じジョブを照会する。古い確認ID、他ジョブのID、二重回答は拒否する。
無回答は30分で中止となり、自動続行しない。確認待ちは既存 worker を1枠使う（同時2枠）。
ジョブと待機中の実行はメモリ上にあるためサーバー再起動では失われる。警告・回答ログは
実行フォルダに残るが、再起動後のジョブ再開は未対応。
設定登録・実アカウントの OAuth・生成品質の確認は、ローカルのツール一覧確認とは別に行う。

```bash
docker build -t numbertales-mcp .
docker run --rm -p 8080:8080 \
  -e MCP_TRANSPORT=streamable-http \
  -e MCP_ALLOW_UNAUTHENTICATED=1 \
  -e OUTPUT_SINK=local \
  --env-file .env \
  numbertales-mcp
# → http://localhost:8080/mcp で待受（MCP_ALLOW_UNAUTHENTICATED=1 は認証なし。手元の検証専用）
```

---

## 5. Google Cloud Run へのデプロイ

> 以下は **GCP アカウント側の操作**のため、ご自身で実行してください。
> `PROJECT_ID` / `REGION` は環境に合わせて置き換えます。

### 5.1 事前準備

```bash
gcloud auth login
gcloud config set project PROJECT_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
    secretmanager.googleapis.com cloudbuild.googleapis.com
```

### 5.2 Secret Manager にシークレットを登録

Cloud Run の Revision 作成時にすべての `--set-secrets` 参照先が存在しないとデプロイが失敗します。
**初回デプロイ前に 11 件すべてを登録してください。**

```bash
# ── LLM API キー ────────────────────────────────────────
printf '%s' "$GEMINI_API_KEY"      | gcloud secrets create GEMINI_API_KEY      --data-file=-
printf '%s' "$OPENAI_API_KEY"      | gcloud secrets create OPENAI_API_KEY      --data-file=-

# ── コネクタの合言葉（接続時に確認画面で入力する）────────
printf '%s' "$MCP_AUTH_PASSPHRASE" | gcloud secrets create MCP_AUTH_PASSPHRASE --data-file=-

# ── Canva Connect API ────────────────────────────────────
printf '%s' "$CANVA_ACCESS_TOKEN"  | gcloud secrets create CANVA_ACCESS_TOKEN  --data-file=-
printf '%s' "$CANVA_REFRESH_TOKEN" | gcloud secrets create CANVA_REFRESH_TOKEN --data-file=-
printf '%s' "$CANVA_CLIENT_ID"     | gcloud secrets create CANVA_CLIENT_ID     --data-file=-
printf '%s' "$CANVA_CLIENT_SECRET" | gcloud secrets create CANVA_CLIENT_SECRET --data-file=-

# ── Google Drive 出力シンク ──────────────────────────────
printf '%s' "$DRIVE_FOLDER_ID"     | gcloud secrets create DRIVE_FOLDER_ID     --data-file=-
printf '%s' "$DRIVE_CLIENT_ID"     | gcloud secrets create DRIVE_CLIENT_ID     --data-file=-
printf '%s' "$DRIVE_CLIENT_SECRET" | gcloud secrets create DRIVE_CLIENT_SECRET --data-file=-
printf '%s' "$DRIVE_REFRESH_TOKEN" | gcloud secrets create DRIVE_REFRESH_TOKEN --data-file=-
```

> **シークレット更新時は `versions add` を使う**（`create` は初回のみ有効）:
> ```bash
> printf '%s' "$CANVA_ACCESS_TOKEN" | gcloud secrets versions add CANVA_ACCESS_TOKEN --data-file=-
> ```

登録確認:

```bash
gcloud secrets list --project=PROJECT_ID --format="table(name,createTime)"
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
  --set-env-vars MCP_TRANSPORT=streamable-http,MCP_ISSUER_URL=https://SERVICE_URL,OUTPUT_SINK=drive,DRIVE_FOLDER_ID=xxxx \
  --set-secrets MCP_AUTH_PASSPHRASE=MCP_AUTH_PASSPHRASE:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,CANVA_ACCESS_TOKEN=CANVA_ACCESS_TOKEN:latest
```

> **`--min-instances 1 --max-instances 1` は必須**です。ジョブはプロセス内メモリに
> 保持されるため、複数インスタンスにスケールすると別インスタンスのジョブが
> `job_status` から見えなくなります。`--no-cpu-throttling` はレスポンス後も
> バックグラウンドのジョブを走らせ続けるために指定します。

### 5.5 リモート MCP コネクタとして登録

デプロイ後の URL（例 `https://numbertales-mcp-xxxx.run.app/mcp`）を、Claude の
コネクタ設定で **カスタム（リモート / Streamable HTTP）MCP** として追加します。
接続の途中で合言葉の確認画面が開くので、`MCP_AUTH_PASSPHRASE` の値を入力します
（デプロイし直したあとの再サインインでも同じ）。URL は公開の場に書かないでください。

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
MCP_AUTH_PASSPHRASE=your_passphrase   # コネクタの接続時に入力する合言葉
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
3. **「Add」** で確定 → 合言葉の確認画面で `MCP_AUTH_PASSPHRASE` の値を入力 → 会話の「+」→ Connectors でトグル ON

---

## 7. GitHub Actions CI/CD デプロイ

`.github/workflows/deploy-mcp-server.yml` による自動デプロイの前提条件をまとめます。

### 7.1 トリガー

`master` ブランチへの push で、以下のパスが変更されたときに実行されます:

```
src/**  /  requirements*.txt  /  Dockerfile
.github/workflows/deploy-mcp-server.yml  /  _creations-ai
```

`workflow_dispatch` による手動実行も可能です。

### 7.2 必要な GitHub Secrets

リポジトリ → **Settings → Secrets and variables → Actions** で登録します。

| シークレット名 | 値の形式 | 用途 |
|---|---|---|
| `GCP_WIF_PROVIDER` | `projects/…/locations/global/workloadIdentityPools/…/providers/…` | Workload Identity Federation |
| `GCP_SERVICE_ACCOUNT` | `sa-name@PROJECT_ID.iam.gserviceaccount.com` | デプロイ用 SA |
| `GCP_PROJECT_ID` | プロジェクト ID | イメージの置き場と配置先 |
| `MCP_ISSUER_URL` | `https://…run.app`（Cloud Run のサービスの URL。末尾に `/mcp` を付けない） | OAuth の issuer。未設定だと認証が無効になるため、ワークフローが最初に止める |
| `GCS_BUCKET` | バケット名 | 中間画像・入力画像・改稿の起点の置き場 |

このリポジトリは公開で、Actions のログも公開される。プロジェクト ID・コネクタの URL・バケット名を
シークレットに置くのは、ワークフローのファイルとログの両方に出さないため（ログでは伏せ字になる）。

### 7.3 GCP 側の前提

| 項目 | 内容 |
|---|---|
| WIF プール | GitHub Actions リポジトリを `attribute.repository == "org/repo"` で許可 |
| SA に付与するロール | `roles/run.admin` / `roles/artifactregistry.writer` / `roles/iam.serviceAccountUser` / `roles/secretmanager.secretAccessor` |
| Artifact Registry | `asia-northeast1` に `numbertales-mcp`（Docker 形式）を作成済み |
| Secret Manager | **§5.2 の 11 件すべてが登録済み**（コネクタの合言葉 `MCP_AUTH_PASSPHRASE` を含む）（未登録だと Revision 作成で `not found` エラー） |

### 7.4 よくあるCI失敗パターン

| 失敗ステップ | 典型エラー | 対処 |
|---|---|---|
| `Deploy to Cloud Run` | `Secret …/versions/latest was not found` | §5.2 の残りシークレットを Secret Manager に登録（`gcloud secrets versions add`） |
| `Deploy to Cloud Run` | `PERMISSION_DENIED` | SA に `roles/run.admin` + `roles/secretmanager.secretAccessor` を付与 |
| `Authenticate to Google Cloud` | `Error creating token` | GitHub Secrets の `GCP_WIF_PROVIDER` / `GCP_SERVICE_ACCOUNT` を確認 |
| `Build and push Docker image` | `COPY … not found` | サブモジュール `_creations-ai` が空（checkout に問題あり） |

---

## 8. 既知の制約 / 今後

- ジョブ状態は**プロセス内メモリ**。再デプロイ・再起動で消える。複数インスタンス不可。
  → 将来は Firestore 等の共有ストアへ差し替え可能（`src/mcp_server/jobs.py` を実装差し替え）。
- 進捗は粗い（pending / running / succeeded / failed）。ステージ単位の細かい進捗は未実装。
- `OUTPUT_SINK=drive|gcs` は依存ライブラリ・クレデンシャルが無い場合、エラーで落とさず
  `local` にフォールバックし結果の `note` に理由を残す。
- `drive` シンクのアップロードは **サーバ自身のサービスアカウント**で行う（Claude の
  Drive コネクタとは別物）。フォルダをそのサービスアカウントと共有しておくこと。
