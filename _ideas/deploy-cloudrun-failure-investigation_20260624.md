# Deploy MCP Server to Cloud Run — 連続失敗 調査・修正方針（2026-06-24）

> 57(イズナ) による **読み取り専用** 調査の advisory。
> コード／ワークフロー／Dockerfile／設定は一切変更していない。git の書込系（add/commit/push/stash/reset）も未実行。
> 秘密情報は値を出力せず、参照名と存在有無のみ確認。
> 対象ワークフロー: `.github/workflows/deploy-mcp-server.yml`（最新変更 commit `838e1ab`）。

---

## 0. 確認した事実（リポジトリ実体）

- ワークフローは **Cloud Run へ直デプロイ**する構成（GCE+Caddy+systemd の `_ideas/mcp-multi-llm-bridge-gce-design.md` 設計から **Cloud Run へピボット済み**。`deploy/numbertales-mcp.service` `deploy/Caddyfile` は旧GCE構成の名残）。
- 認証は **Workload Identity Federation (WIF)**。`google-github-actions/auth@v2` が `secrets.GCP_WIF_PROVIDER` / `secrets.GCP_SERVICE_ACCOUNT` を参照。
- env 直書き: `PROJECT_ID=claude-radiannkswg` / `REGION=asia-northeast1` / `SERVICE=generators-ai` / `IMAGE=asia-northeast1-docker.pkg.dev/claude-radiannkswg/numbertales-mcp/numbertales-mcp`。
- `actions/checkout@v4` は **`submodules: recursive`** 指定。
- submodule 構成:
  - `_creations-ai` → `8d297c2`（master）
  - ネスト `_creations-ai/creations-db` → **非デフォルトブランチ `addon-ai-tag` の `5b17afdf`** にピン。
  - **`.gitmodules` に幻のエントリ**: トップレベル path `_creations-db`（url=CreationsDB.git）が宣言されているが、実体ディレクトリも gitlink も存在しない（`git submodule status` に出てこない）。`.gitmodules.bak_20260615` には `_creations-ai` 1件のみ。
- Dockerfile は build 時に `COPY _creations-ai/ai-dataset/` と `COPY _creations-ai/creations-db/data/` を実行 → **submodule がCIで空だと COPY が失敗**。
- `MCP_TRANSPORT=streamable-http` / server.py は `HOST`/`PORT` env を読む（`PORT=8080`）→ アプリ側のポート整合は問題なし。
- docs（`docs/mcp-server.md` `docs/setup.md`）に **必要 GitHub Secrets（WIF provider / SA / Artifact Registry 作成手順）の記載が無い** → CLAUDE.md の docs 同期ルール観点でも穴。

### commit 838e1ab で何を直したか
直前まで `--cpu-always-allocated`（gcloud が認識しない無効フラグ）を渡しており、`--no-cpu-throttling` に修正。つまり**それ以前の失敗の一因は無効フラグ**だった可能性が高い。838e1ab 以降も落ちているなら **別ステップ（前段）に第二の原因**がある。

---

## 1. 失敗原因の仮説（優先度つき）

> 約1.5分で fail＝「checkout〜build前半は走り、認証 or 取得 or push のいずれかで落ちる」帯。確定にはActionsの**赤いステップ名**の確認が必須（§3-1）。

### 🔴 H1 — submodule の recursive checkout 失敗（最有力・前段）
- ネスト `creations-db` が **非デフォルトブランチ `addon-ai-tag@5b17afdf`** にピン。当該 commit が **リモート未push** だと recursive checkout が "did not contain the requested ref" で失敗。
- 参照先 `radiann-kswg/100BeautiesLab_CreationsAI` / `…CreationsDB` が **private の場合**、CI 既定の `GITHUB_TOKEN` は他リポジトリにアクセス不可 → submodule clone が認証失敗。
- `.gitmodules` の幻 `_creations-db` エントリも recursive 解決を不安定化させうる。
- 過去トリアージ（`_tasks/.archive/20260621_gce-mcp-drive.md`）に **未push submodule の "not our ref" 問題**が実際に記録されており、再発の蓋然性が高い。

### 🔴 H2 — WIF 認証シークレット未設定／不正
- `secrets.GCP_WIF_PROVIDER` / `secrets.GCP_SERVICE_ACCOUNT` が空・誤りだと `auth@v2` が即失敗（〜20–30s）。
- WIF プールに **GitHubリポジトリの attribute condition / SA への `roles/iam.workloadIdentityUser` 紐付け**が無いと、token交換で失敗。
- docs に必要シークレット一覧が無いため設定漏れが起きやすい。

### 🟠 H3 — Artifact Registry リポジトリ未作成 / push権限不足（1.5分と最も整合）
- `IMAGE` の repo セグメント **`numbertales-mcp`** が未作成だと `docker push` が失敗。
- SA に **`roles/artifactregistry.writer`** が無いと push が 403。
- build（apt+pip〜60–90s）通過後に push で落ちる＝**所要≈1.5分の説明として最有力**。

### 🟠 H4 — Docker build の COPY 失敗（H1の二次効果）
- submodule が CI で未populate だと `COPY _creations-ai/creations-db/data/` が `not found` で build 失敗。H1 が真ならこちらに化ける。

### 🟡 H5 — Cloud Run deploy 段の権限／フラグ
- `--allow-unauthenticated` には SA に `run.services.setIamPolicy`（`roles/run.admin` 相当）が必要。不足だとデプロイ最終段で失敗。
- Secret Manager 参照（`GEMINI_API_KEY` 等10件）に SA の `roles/secretmanager.secretAccessor` 不足、または**該当 secret 未作成**だと deploy 失敗。
- ただしこれらは build/push 通過後で、通常1.5分より後ろにずれる。

---

## 2. 推奨アクション（安全・読み取り優先）

### まず原因を1点に確定（最重要）
1. GitHub → Actions → 失敗 run（最新 2026-06-23 11:06 UTC, `838e1ab`）を開き、**赤くなっているステップ名**を特定。
   - `gh run view <run-id> --log-failed` でも可（読み取りのみ）。
   - これでH1〜H5のどれかが即確定する。ログ無しに修正へ進まない。

### ステップ別の対処方針（確定後に着手）
- **Checkout（H1）が赤い場合**:
  - submodule の参照 commit `5b17afdf` がリモートに push 済みか確認。
  - 参照リポが private なら、checkout に **PAT/Deploy key（`token:` 入力）** を渡すか、submodule を recursive で引かず **ビルドに必要な `ai-dataset` / `creations-db/data` だけを別取得**する設計へ。
  - `.gitmodules` の幻 `_creations-db` エントリ整理（実体と一致させる）。
- **Authenticate（H2）が赤い場合**:
  - リポジトリ Secrets に `GCP_WIF_PROVIDER`（`projects/…/locations/global/workloadIdentityPools/…/providers/…` 形式）と `GCP_SERVICE_ACCOUNT`（SA メール）が**存在するか**を Settings→Secrets で確認（値は見ない）。
  - WIF プールの attribute condition に当該リポを許可、SA に `roles/iam.workloadIdentityUser` を紐付け。
- **Build & push（H3/H4）が赤い場合**:
  - `gcloud artifacts repositories describe numbertales-mcp --location=asia-northeast1` で repo 実在を確認。無ければ作成。
  - SA に `roles/artifactregistry.writer` を付与。
  - COPY 失敗なら H1 へ戻る。
- **Deploy（H5）が赤い場合**:
  - SA に `roles/run.admin` + `roles/iam.serviceAccountUser`、Secret 参照に `roles/secretmanager.secretAccessor`。
  - `secrets:` の10件が Secret Manager に実在するか確認。

### 恒久対策（別PRで）
- `docs/mcp-server.md`（または `docs/setup.md`）に **CI デプロイ前提（必要 GitHub Secrets / WIF セットアップ / Artifact Registry 作成 / SA ロール一覧）** を追記。CLAUDE.md の docs 同期ルールに準拠。
- 旧GCE資材（`deploy/`）と Cloud Run 構成の役割を README/docs で明記し、混在による誤解を解消。

---

## 3. 制約遵守メモ
- 本調査は読み取りのみ。`git log` / `git show` / `git submodule status` の参照に限定。書込系コマンドは未実行（過去の `.git/index` 破損対策）。
- シークレットは参照名のみ記載、値は未出力。
- 修正・コミットは行っていない（指示どおり調査と提案まで）。
