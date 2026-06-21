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
```

> **ヒント**: `OUTPUT_SINK=drive` にすると生成画像を Google Drive にアップロードし URL を返してくれます。
> Drive を使う場合は `DRIVE_FOLDER_ID` も設定し、サービスアカウントと Drive フォルダを共有してください。

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

## 参考リンク

| リソース | URL |
|---|---|
| Anthropic カスタムコネクタ 入門 | https://support.claude.com/en/articles/11175166 |
| Anthropic カスタムコネクタ 構築 | https://support.claude.com/en/articles/11503834 |
| Remote MCP サーバ（API ドキュメント） | https://docs.claude.com/en/docs/agents-and-tools/remote-mcp-servers |
| Anthropic IP アドレス一覧 | https://platform.claude.com/docs/en/api/ip-addresses |
| FastMCP ドキュメント | https://gofastmcp.com |
