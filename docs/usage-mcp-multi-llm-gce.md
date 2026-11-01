# GCE リモート MCP — 動作確認手順書

> **目的**: GCE（Google Compute Engine）上で MCP サーバを常駐させ、
> Claude（Cowork / デスクトップ）から `numbertales_*` ツールを呼んで
> 画像生成パイプラインを実行できるようにする。
>
> 設計の背景: [_ideas/mcp-multi-llm-bridge-gce-design.md](../_ideas/mcp-multi-llm-bridge-gce-design.md)
> 関連: [docs/mcp-server.md](mcp-server.md) / [docs/usage-generation.md](usage-generation.md)

---

## 0. 前提チェックリスト

実際に作業を始める前に、以下が揃っていることを確認してください。

| 項目 | 確認内容 |
|---|---|
| GCE インスタンス | 起動中（e2-small 以上推奨）、外部 IP 割当済み |
| 静的外部 IP | GCE インスタンスに予約・割当済み |
| ドメイン | サブドメイン（例: `mcp.numbertales-radiann.net`）の A レコードが静的 IP を指している |
| GCP ファイアウォール | 443/tcp を Anthropic IP レンジから許可（[公式 IP 一覧](https://platform.claude.com/docs/en/api/ip-addresses)）、22/tcp は自分の管理 IP のみ |
| API キー | `GEMINI_API_KEY` / `OPENAI_API_KEY` が手元にある |
| Claude プラン | Pro / Max（カスタムコネクタ機能が使えるプラン） |

---

## 1. GCE インスタンス上のセットアップ

以下は **GCE のターミナル（SSH）上で実行**します。

### 1.1 リポジトリのクローン・配置

```bash
sudo mkdir -p /opt/100beautieslab
sudo useradd -r -s /sbin/nologin mcp
sudo chown mcp:mcp /opt/100beautieslab

# mcp ユーザーとして実行
sudo -u mcp git clone https://github.com/radiann-kswg/100BeautiesLab_GeneratorsAI /opt/100beautieslab
cd /opt/100beautieslab
```

### 1.2 Python 仮想環境・依存インストール

```bash
sudo -u mcp python3 -m venv /opt/100beautieslab/.venv
sudo -u mcp /opt/100beautieslab/.venv/bin/pip install --upgrade pip
sudo -u mcp /opt/100beautieslab/.venv/bin/pip install -r /opt/100beautieslab/requirements-mcp.txt
```

### 1.3 `.env` の配置

```bash
sudo -u mcp cp /opt/100beautieslab/.env.example /opt/100beautieslab/.env
sudo chmod 600 /opt/100beautieslab/.env
sudo -u mcp nano /opt/100beautieslab/.env
```

`.env` に最低限以下を設定します:

```dotenv
# API キー
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key

# MCP サーバ設定（GCE 上は常に streamable-http）
MCP_TRANSPORT=streamable-http
HOST=127.0.0.1
PORT=8000
# OAuth discovery の issuer URL（GCE のドメインに合わせる）
MCP_ISSUER_URL=https://mcp.numbertales-radiann.net

# 出力シンク（GCE ローカルに保存する場合は local、Drive/GCS を使う場合は変更）
OUTPUT_SINK=local
# OUTPUT_SINK=drive にする場合は以下も設定する（Drive OAuth — SA はストレージ容量 0 のため必須）
# DRIVE_FOLDER_ID=your_drive_folder_id
# DRIVE_CLIENT_ID=your_oauth_client_id
# DRIVE_CLIENT_SECRET=your_oauth_client_secret
# DRIVE_REFRESH_TOKEN=your_refresh_token   # scripts/get_drive_token.py でローカル取得 → GCE に貼付
```

> **Drive 出力の設定手順**: GCE のデフォルト SA は Drive ストレージ容量を持たないため
> `storageQuotaExceeded (403)` が発生します。以下の手順でユーザー OAuth を設定してください:
>
> 1. GCP Console → APIs & Services → 認証情報 → 「OAuth クライアント ID」作成（デスクトップ アプリ）
> 2. ローカル PC で `pip install google-auth-oauthlib && python scripts/get_drive_token.py`
> 3. 表示された `DRIVE_CLIENT_ID` / `DRIVE_CLIENT_SECRET` / `DRIVE_REFRESH_TOKEN` を GCE の `.env` に追記
> 4. アップロード先フォルダの URL から `DRIVE_FOLDER_ID` を取得して設定
> 5. `sudo systemctl restart numbertales-mcp`

---

## 2. systemd サービスの設定

### 2.1 ユニットファイルの配置

```bash
sudo cp /opt/100beautieslab/deploy/numbertales-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 2.2 サービス起動・自動起動設定

```bash
sudo systemctl enable --now numbertales-mcp
```

### 2.3 起動確認

```bash
sudo systemctl status numbertales-mcp
# → Active: active (running) と表示されれば OK

# ログをリアルタイムで確認する場合
journalctl -u numbertales-mcp -f
# → FastMCP の起動ログが流れ、エラーが無ければ OK
```

**よくある起動エラーと対処:**

| エラー | 原因 | 対処 |
|---|---|---|
| `ModuleNotFoundError: No module named 'mcp'` | pip install が venv に当たっていない | `ExecStart=` のパスが `.venv/bin/python` になっているか確認 |
| `Port already in use` | 8000 番が別プロセスに使われている | `PORT=8001` に変更し `.env` と一致させる |
| `.env` 読み込みエラー | `EnvironmentFile` のパスが違う | `systemctl cat numbertales-mcp` でパスを確認 |

---

## 3. Caddy によるリバースプロキシ・HTTPS 設定

### 3.1 Caddy のインストール

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy -y
```

### 3.2 Caddyfile の配置

`deploy/Caddyfile` の `YOUR_DOMAIN` を実際のサブドメインに置き換えてコピーします:

```bash
# YOUR_DOMAIN を置き換えてコピー
sudo sed 's/YOUR_DOMAIN/mcp.numbertales-radiann.net/g' \
    /opt/100beautieslab/deploy/Caddyfile | sudo tee /etc/caddy/Caddyfile

sudo systemctl enable --now caddy
```

### 3.3 証明書取得の確認

```bash
# A レコードが正しく向いていれば Let's Encrypt 証明書が自動取得される
journalctl -u caddy -f
# → "certificate obtained successfully" が出れば OK

# 外部から HTTPS 到達確認
curl -I https://mcp.numbertales-radiann.net/mcp
# → 200 または 405 (Method Not Allowed) が返れば MCP エンドポイントに到達している
```

---

## 4. 段階別動作確認（Phase 0 → 3）

### Phase 0 — 疎通確認（最重要）

**目標**: 「GCE リモート MCP が Claude から呼べる」を最小コストで確定する。

#### ステップ 4-1: GCE ローカルでの curl 確認

GCE 上のターミナルで実行します（MCP Inspector が使える場合はそちらでも可）:

```bash
# MCP ツール一覧を取得する JSON-RPC リクエスト
curl -s -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 -m json.tool
```

**期待する出力** (抜粋):
```json
{
  "result": {
    "tools": [
      { "name": "numbertales_generate_character", ... },
      { "name": "numbertales_job_status", ... },
      ...
    ]
  }
}
```

ツール名 6 件が返れば MCP サーバは正常動作しています。

#### ステップ 4-2: Claude カスタムコネクタ登録

1. `claude.ai` の **「Customize」→「Connectors」**（または `claude.ai/customize/connectors`）を開く
2. **「+」→「Add custom connector」** をクリック
3. **URL** に `https://mcp.numbertales-radiann.net/mcp` を入力
4. **「Add」** で確定

#### ステップ 4-3: 会話からの疎通確認

Claude の会話画面で:

1. 左下の **「+」→「Connectors」** から `numbertales_mcp` をトグル ON
2. 以下のように話しかける:

```
ping_providers ツールを使って OpenAI と Gemini への疎通を確認してください。
```

**期待する結果**:
```json
{
  "openai": { "ok": true, "status": 200, "latency_ms": 350, "key_present": true },
  "gemini": { "ok": true, "status": 200, "latency_ms": 210, "key_present": true }
}
```

> `ok: true` が両方返れば **Phase 0 完了**。
> GCE から OpenAI / Gemini に到達できること、Claude からコネクタを呼べることが確定します。

**Phase 0 が失敗する場合:**

| 症状 | 原因候補 | 確認先 |
|---|---|---|
| コネクタ接続エラー | ドメイン未解決 / Caddy 未起動 / ポート未解放 | §3.3 の curl / GCP FW ルール |
| `ok: false`, `key_present: false` | `.env` のキー未設定 | GCE 上の `.env` を確認 |
| `ok: false`, `hint: 到達不可` | GCE から外部 API への egress がブロックされている | GCP VPC の外向きルール |
| タイムアウト | 処理が遅い / MCP エンドポイントへ到達不可 | journalctl で MCP サーバ側のログを確認 |

---

### Phase 1 — テキスト生成（課金極小）

**目標**: エンドツーエンドの呼び出し経路を画像課金なしで確認する。

```
57(イズナ)のコアフォルダ姿の画像生成プロンプトを組み立ててください。
```

MCP 経由で `numbertales_generate_character` が呼ばれ `job_id` が返されれば OK です。
続いて:

```
さっきのジョブ（job_id: XXXXXXXX）の状態を確認してください。
```

`numbertales_job_status` が `"status": "succeeded"` を返せば Phase 1 完了。

---

### Phase 2 — 単一画像生成

**目標**: 実際に 1 枚生成し、出力パス（または Drive/GCS URL）が返ることを確認する。

```
57(イズナ)をコアフォルダ形態で、図書館で本を読んでいるシーンで生成してください。
Canva はスキップして構いません。
```

`numbertales_generate_character` → `job_id` → `numbertales_job_status` のループを経て
`"status": "succeeded"` と `"outputs": [{"url": ...}]` が返れば Phase 2 完了です。

> `OUTPUT_SINK=local` の場合 `url` は `null`、`local_path` に GCE 上のパスが返ります。
> 手元で画像を確認したい場合は `OUTPUT_SINK=drive` に変更するか、
> `scp` で GCE から取得してください。

---

### Phase 3 — フルパイプライン・合同・i2i（本番運用）

Phase 0〜2 の通過を確認してから進めてください。

**合同生成（25 と 57 を並べる）:**
```
25(フィズ)と57(イズナ)を自信に満ちた表情で並べて生成してください（コアフォルダ形態）。
```

**i2i 改稿:**
```
前回の画像（run-dir: output/...）を起点に、表情だけ笑顔にしてください。尻尾は元のまま。
```

> フルパイプラインは数分かかります。`numbertales_job_status` をポーリングしながら待ってください。
> MCP タイムアウトが発生する場合は `--skip-canva` を指定するか、
> GCE に SSH して CLI 直叩き（`python -m src.pipeline.image_pipeline ...`）にフォールバックしてください。

---

## 5. 運用メモ

### ログ確認

```bash
# MCP サーバのログ
journalctl -u numbertales-mcp -f

# Caddy のログ
journalctl -u caddy -f
# または /var/log/caddy/numbertales-mcp.log（Caddyfile でファイルログを設定した場合）
```

### サービスの再起動

```bash
sudo systemctl restart numbertales-mcp
```

### コードの更新手順

```bash
cd /opt/100beautieslab
sudo -u mcp git pull
sudo -u mcp /opt/100beautieslab/.venv/bin/pip install -r requirements-mcp.txt
sudo systemctl restart numbertales-mcp
```

### コネクタの OFF/ON

会話の「+」→「Connectors」で会話単位にトグルできます。
生成系ツール（非 readOnly）は実行ごとに承認ダイアログが出ます。
信頼できるツールのみ「Allow always」に設定してください。

---

## 6. セキュリティチェックリスト

- [ ] `.env` のパーミッションが `600`（`mcp` ユーザーのみ読み取り可）
- [ ] `.gitignore` に `.env` が含まれている（うっかり push しない）
- [ ] GCP ファイアウォールの 443 許可元が Anthropic IP レンジのみ
- [ ] 8000 番ポートが外部に直接公開されていない（Caddy 経由のみ）
- [ ] 生成系ツールの「Allow always」を安易に設定しない（課金暴発防止）

---

## 7. SSH/CLI 実行基盤（stdio over SSH・常駐なし）

§1〜6 の常駐構成（systemd＋Caddy＋DNS）は Cloud Run 版 MCP と機能が重なるため、
GCE VM を **使うときだけ起動する SSH/CLI 実行基盤** として使う構成も用意する。
公開ポート・Caddy・DNS は不要で、Claude Code からは SSH 越しの stdio MCP として接続する（コード変更なし）。

> Drive への出力は MCP サーバー（`numbertales_*` ツール）経由でのみ行われる（`src/mcp_server/output_sink.py`）。
> CLI 直叩きの出力は VM 内 `output/` に残り、Drive には上がらない。

以下の例は VM `generators-ai`（`us-central1-f`）。自分の環境に合わせて読み替えること。

### 7.1 事前スナップショット

```bash
gcloud compute disks snapshot generators-ai --zone=us-central1-f \
  --snapshot-names=generators-ai-pre-vmsetup-$(date +%Y%m%d) --storage-location=us
```

### 7.2 セットアップ（`scripts/setup_gce_vm.sh`）

clone（サブモジュール含む・公開リポジトリ）→ venv → `requirements-mcp.txt` → 自己チェック（API 未呼び出し）。何度実行しても壊れない。

```bash
gcloud compute scp scripts/setup_gce_vm.sh generators-ai:~/setup_gce_vm.sh --zone=us-central1-f
gcloud compute ssh generators-ai --zone=us-central1-f --command 'bash ~/setup_gce_vm.sh'
```

期待: `imports OK` / `image_pipeline --help OK` / `stage_cli --help OK`（この時点では `.env なし`）。

### 7.3 `.env` の配置

ローカル `.env` から **必要行だけ** 抜いた `.env.vm`（`.gitignore` の `.env.*` 対象）を作って scp する。Canva / Firefly / SDXL 行は入れない。

```powershell
# ローカル PowerShell（リポジトリルートで）
$keys = 'GEMINI_API_KEY','OPENAI_API_KEY','IMAGEN_MODEL','GEMINI_REFERENCE_MODEL','DALLE_MODEL','GPT_MODEL','OPENAI_IMAGE_QUALITY','DRIVE_CLIENT_ID','DRIVE_CLIENT_SECRET','DRIVE_REFRESH_TOKEN','DRIVE_FOLDER_ID','CREATIONS_DB_PACKAGE_ENABLE'
$lines = @(Get-Content .env | Where-Object { $_ -match '^[A-Z_]+=' -and ($keys -contains ($_ -split '=',2)[0]) }) + 'OUTPUT_SINK=drive','MCP_TRANSPORT=stdio','OUTPUT_BASE_DIR=output'
[IO.File]::WriteAllText("$PWD\.env.vm", ($lines -join "`n") + "`n", (New-Object Text.UTF8Encoding $false))
# 先に VM 側で 600 の空ファイルを作る（scp の上書きは既存の権限を保つ）。失敗したら転送しない
gcloud compute ssh generators-ai --zone=us-central1-f --command 'install -m 600 /dev/null /opt/100beautieslab/.env'
if ($LASTEXITCODE -eq 0) { gcloud compute scp .env.vm generators-ai:/opt/100beautieslab/.env --zone=us-central1-f }
Remove-Item .env.vm
gcloud compute ssh generators-ai --zone=us-central1-f --command 'bash ~/setup_gce_vm.sh'
```

- `.env.vm` は **BOM なし・LF** で作る。BOM 付きだと dotenv が先頭キーを読めず、CRLF だと §7.5 の `. ./.env` が値の末尾に `\r` を残す。
  `Set-Content` は行末が CRLF になり、Windows PowerShell 5.1 には `utf8NoBOM` も無いため、上の `[IO.File]::WriteAllText` を使う。
- 再実行で `.env あり（600）` とキー名一覧が出る（値は表示しない）。

### 7.4 dry-run（課金ゼロ）

```bash
gcloud compute ssh generators-ai --zone=us-central1-f --command \
  'cd /opt/100beautieslab && .venv/bin/python -m src.batch_generate --nums 57 --forms corefolder --provider gemini --dry-run'
```

期待: `#57 corefolder gemini -> RUN ...` と `-> DRY-RUN (API 未実行)` が出て、`BATCH SUMMARY` の `[skipped]` の理由が `dry-run` であること。
集計 `skipped=1` だけでは判定しない（未取得・オプトアウトでも同じ数になる）。
`-> NOT_FOUND` ならサブモジュール未取得（`git submodule update --init --recursive`）、`-> SKIP (ai-optout)` なら権利ゲートで除外されている。

### 7.5 Claude Code から stdio MCP で接続

```bash
claude mcp add --transport stdio numbertales-vm -- gcloud compute ssh generators-ai --zone=us-central1-f --project=claude-radiannkswg --quiet --ssh-flag=-T --command "cd /opt/100beautieslab && set -a && . ./.env && set +a && exec .venv/bin/python -m src.mcp_server.server"
claude mcp list
```

- `numbertales-vm` に `numbertales_*` ツールが **11 件** 見えれば OK。
- gcloud の進行メッセージは stderr に出るので stdio は汚れない。切れる場合は `--ssh-flag=-T` を外すか、素の `ssh <外部IP>` に置き換える。
- VM 停止中はつながらない。使う前に起動し、使い終わったら停止する。長期間使わないなら `.env` を削除してから停止する。

---

## 参考リンク

| リソース | URL |
|---|---|
| Anthropic カスタムコネクタ 入門 | https://support.claude.com/en/articles/11175166 |
| Anthropic カスタムコネクタ 構築 | https://support.claude.com/en/articles/11503834 |
| Remote MCP サーバ（API ドキュメント） | https://docs.claude.com/en/docs/agents-and-tools/remote-mcp-servers |
| Anthropic IP アドレス一覧 | https://platform.claude.com/docs/en/api/ip-addresses |
| FastMCP ドキュメント | https://gofastmcp.com |
