# setup.md — 環境準備

100BeautiesLab_GeneratorsAI を動かすための最小セットアップ手順をまとめたページ。

> 関連: [`docs/README.md`](README.md) (目次) / [`AGENTS.md`](../AGENTS.md) / [`README.md`](../README.md)

---

## 1. 前提環境

| 項目     | 推奨                                                                    |
| -------- | ----------------------------------------------------------------------- | ------------- |
| OS       | Windows 11 / macOS / Linux (本リポジトリは PowerShell 環境で運用中)     |
| Python   | 3.10 以上 (型注釈 `list[str]                                            | None` を多用) |
| 仮想環境 | `.venv` をリポジトリ直下に作成して使う運用                              |
| Git      | サブモジュール対応版                                                    |
| 任意     | VS Code + GitHub Copilot (エージェントは 57(イズナ) ロールプレイで応答) |

---

## 2. リポジトリ取得

```powershell
git clone --recurse-submodules <このリポジトリのURL>
cd 100BeautiesLab_GeneratorsAI
```

クローン済みで後からサブモジュールを取る場合:

```powershell
git submodule update --init --recursive
```

### サブモジュール

| ディレクトリ     | 用途                | 編集可否                              |
| ---------------- | ------------------- | ------------------------------------- |
| `_creations-ai/` | AI 学習データセット | 通常編集不可 (生成物)                 |
| `_creations-ai/creations-db/` | キャラクター原典 DB（`_creations-ai` 内のネストサブモジュール） | 原則 read-only (上流リポジトリで管理) |

> 原典 DB は `_creations-ai` のネストサブモジュール `creations-db` (`addon-ai-tag` ブランチ) として取り込まれる。clone・更新時は `--recursive` を付けること。

更新コマンド:

```powershell
# 全サブモジュール更新 (ネストの creations-db も含めて再帰的に)
git submodule update --remote --recursive --merge

# _creations-ai のみ (内部の creations-db も追従)
git submodule update --remote --recursive _creations-ai

# 原典 DB (ネストの creations-db, addon-ai-tag ブランチ) のみ更新
git -C _creations-ai submodule update --remote creations-db
```

---

## 3. Python 依存パッケージ

```powershell
# 仮想環境作成 (初回のみ)
python -m venv .venv

# アクティベート (PowerShell)
.\.venv\Scripts\Activate.ps1

# 依存インストール
pip install -r requirements.txt
```

[`requirements.txt`](../requirements.txt) には以下が含まれている。

- `google-genai>=1.0.0` — Gemini / Imagen
- `openai>=1.30.0` — DALL-E 3 / gpt-image-1 / GPT-4o
- `python-dotenv>=1.0.0` — `.env` ロード
- `requests>=2.31.0` — リファレンス画像 DL
- `Pillow>=10.0.0` — 画像 MIME 再エンコード

---

## 3.5 macOS ワンショットセットアップ (推奨)

macOS では付属スクリプトで venv 作成・依存インストール・サブモジュール取得・動作確認 (dry-run) を一括実行できる。

```bash
# 初回のみ実行権限を付与
chmod +x scripts/setup_mac.sh

# セットアップ実行 (venv 作成 → pip install → submodule → dry-run 検証)
./scripts/setup_mac.sh
```

オプション:

| オプション         | 役割                            |
| ------------------ | ------------------------------- |
| `--skip-submodule` | サブモジュール取得をスキップ    |
| `--skip-verify`    | 末尾の dry-run 動作確認をスキップ |
| `--recreate-venv`  | 既存 `.venv` を削除して作り直す |

- スクリプトは Python 3.10+ を自動検出し `.venv` を作る。
- **`.env` は作成・上書きしない**。鍵は手動で設定する (次節)。`.env` が無い場合は警告と手順を表示するだけ。
- 実行後は `source .venv/bin/activate` で venv を有効化してから各コマンドを使う。
- bash の `&&` がそのまま使えるので、PowerShell 用の `;` 区切り (第5節) は不要。

---

## 4. `.env` の作成

リポジトリ直下に `.env` を作り、最低限以下を入れる。 **絶対にコミットしない** こと (`.gitignore` で除外済)。
雛形は [`.env.example`](../.env.example) にあるので `cp .env.example .env` してから値を埋めるのが早い。

```ini
# --- 必須 (使うプロバイダの鍵だけでOK) ---
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# --- 任意 (デフォルト値) ---
# Gemini / Imagen
IMAGEN_MODEL=imagen-4.0-generate-001   # imagen-3.0-* は廃止。現行は imagen-4.0-* のみ
GEMINI_REFERENCE_MODEL=models/gemini-3.1-flash-image

# OpenAI
DALLE_MODEL=dall-e-3                   # この環境で dall-e-3 が NotFound なら gpt-image-1 にする
OPENAI_IMAGE_QUALITY=standard          # gpt-image-1 では medium / high が有効
GPT_MODEL=gpt-4o                       # prompt-assist モード用

# Adobe Firefly Services (provider: adobe) — OAuth Server-to-Server 資格情報
FIREFLY_CLIENT_ID=your_firefly_client_id
FIREFLY_CLIENT_SECRET=your_firefly_client_secret
FIREFLY_SIZE=1024x1024                 # 生成サイズ
FIREFLY_MODEL=                         # 任意: モデルバージョン (省略時は API デフォルト)

# Canva Connect API (provider: canva) — user OAuth アクセストークン
CANVA_CLIENT_ID=your_canva_client_id           # OAuth クライアント ID (Developer Portal で確認)
CANVA_CLIENT_SECRET=your_canva_client_secret   # OAuth クライアントシークレット (同上)
CANVA_ACCESS_TOKEN=your_canva_oauth_access_token  # 期限切れ時: python -m src.tools.refresh_canva_token
CANVA_EXPORT_FORMAT=png                # 書き出し形式 (png/jpg/pdf)

# 出力先
OUTPUT_BASE_DIR=output                 # 互換のため OUTPUT_DIR も読まれる

# MCP サーバ出力シンク（GCE / Cloud Run でリモート実行する場合）
OUTPUT_SINK=local                      # local / drive / gcs
DRIVE_FOLDER_ID=                       # OUTPUT_SINK=drive 時: アップロード先 Drive フォルダ ID
# Drive ユーザー OAuth — SA はストレージ容量 0 のため storageQuotaExceeded になる
# GCP Console で OAuth クライアント ID（デスクトップ型）を作成し、
# scripts/get_drive_token.py でリフレッシュトークンを取得して設定する
DRIVE_CLIENT_ID=                       # GCP Console の OAuth クライアント ID
DRIVE_CLIENT_SECRET=                   # OAuth クライアントシークレット
DRIVE_REFRESH_TOKEN=                   # scripts/get_drive_token.py で取得

# 形態共通データセット (作品別ファイルを上書きしたいときだけ)
FORM_COMMON_DATASET_PATH=

# 創作 DB パッケージ参照を一時的に無効化したい場合
CREATIONS_DB_PACKAGE_ENABLE=1

# 創作 DB 実物 API (database.numbertales-radiann.net)
# addon-ai-tag ブランチで公開している AIHints エンドポイント等にアクセスする際に必要。
# 通常の公開エンドポイント (/api/v1/works/…) はトークン不要。
CREATIONS_DB_API_TOKEN=
CREATIONS_DB_API_BASE_URL=https://database.numbertales-radiann.net/api/v1

# パス・実行系 (任意。パーソナルスキル/ランチャーから任意 cwd で実行する場合に使う)
NUMBERTALES_REPO=                       # ランチャーが使うリポジトリルートの明示指定 (最優先)
PROJECT_ROOT=                           # src 側の基準ルート。manifest/creations-db/形態共通データの解決に使用
                                        #   未設定時はモジュール位置 (src/utils) から自動解決
MANIFEST_PATH=                          # manifest.jsonl の上書き。未設定時は PROJECT_ROOT/_creations-ai/ai-dataset/manifest.jsonl
```

> `load_manifest` は cwd ではなく `PROJECT_ROOT` 基準で `manifest.jsonl` を探すため、
> リポジトリルート以外から実行しても動く。ランチャー (`bin/ntimg.ps1` / `bin/ntimg.sh`) は
> `PROJECT_ROOT` / `PYTHONPATH` を自動設定する。詳細は
> [`.claude/skills/numbertales-imagegen/REFERENCE.md`](../.claude/skills/numbertales-imagegen/REFERENCE.md)。

### プロバイダ別の鍵メモ

- **Adobe (Firefly)**: [Adobe Developer Console](https://developer.adobe.com/firefly-services/docs/firefly-api/) で OAuth Server-to-Server 資格情報を作り、Client ID / Secret を設定。`client_credentials` でトークンを自動取得する (有効期限 24h)。
- **Canva**: Canva Connect は **user OAuth トークン** が必要 (client_credentials 不可)。[Canva Connect](https://www.canva.dev/docs/connect/) で OAuth を済ませ、取得したアクセストークンを設定。Connect API にテキスト→画像生成は無く、`canva` プロバイダは「生成済み画像をデザイン化して書き出す」後段ツール。新規生成を Canva で行いたい場合は MCP ワークフロー ([`usage-mcp-canva-adobe.md`](usage-mcp-canva-adobe.md)) を使う。

### 検証されている組み合わせ

- **Gemini**: `imagen-4.0-generate-001` (上位互換) と multimodal `gemini-3.1-flash-image` を併用する経路が安定。
- **OpenAI**: 環境によって `dall-e-3` が `model does not exist` を返す。その場合は `DALLE_MODEL=gpt-image-1`、`OPENAI_IMAGE_QUALITY=medium` (または `high`) を指定すると通る。

---

## 5. PowerShell 利用時の注意

- 仮想環境アクティベート: `.\.venv\Scripts\Activate.ps1`
- コマンドの連結に `&&` を使わない。代わりに `;` で区切る。
- 日本語出力が文字化けする場合は `$env:PYTHONIOENCODING="utf-8"` を先に設定。
- `npm test` がうまく解決されない場合は `npm.cmd test` を使う ([`_creations-ai/creations-db/`](../_creations-ai/creations-db) でのみ使用)。

---

## 6. 動作確認

```powershell
# 1. キャラクターレコードが読めるか確認
python -c "from src.utils import find_character; r = find_character(57, '#Works_NumberTales'); print(r['data'].get('Name'))"

# 2. dry-run でバッチ実行計画だけ確認 (API 呼ばない・課金ゼロ)
python -m src.batch_generate --nums 57 --forms both --provider both --dry-run

# 3. 単発で 1 枚生成
python -m src.gemini.generate --num 57 --form corefolder --count 1
```

実行後、`output/{YYYYMMDD}/{ts}_gemini_corefolder_num057/` に
`prompt.txt` / `run_meta.json` / `notes.md` + 生成画像が出ていれば成功。

---

## 7. よくあるトラブル

| 症状                                                 | 対処                                                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `GEMINI_API_KEY が設定されていません`                | `.env` を作成・編集後、ターミナルを再起動 (または `Activate.ps1` を再実行)            |
| `invalid_request_error (400)` で画像が弾かれる       | [`tools.md`](tools.md) の `check_image_mime` を参照。実体 MIME と拡張子の不一致が原因 |
| OpenAI で `The model 'dall-e-3' does not exist`      | `.env` の `DALLE_MODEL=gpt-image-1` に切替                                            |
| 仮想環境を作ったのに `pip install` が global に入る  | `Activate.ps1` を実行したか確認。`where.exe python` で `.venv` 配下か確認             |
| サブモジュール (`_creations-ai/creations-db/data/...`) の中身が空 | `git submodule update --init --recursive` を実行 (ネストまで再帰必須)                  |
| (macOS) `permission denied: ./scripts/setup_mac.sh`  | `chmod +x scripts/setup_mac.sh` を実行                                                |
| (macOS) `python3` が無い                             | `brew install python@3.12` で導入                                                     |
| Firefly `401 Unauthorized`                           | `FIREFLY_CLIENT_ID` / `FIREFLY_CLIENT_SECRET` を確認。トークンは24hで失効             |
| Canva `401` / `403`                                  | `CANVA_ACCESS_TOKEN` の期限切れ。`python -m src.tools.refresh_canva_token` で再取得（自動的に `.env` を更新）              |
