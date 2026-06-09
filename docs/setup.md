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
| `_creations-db/` | キャラクター原典 DB | 原則 read-only (上流リポジトリで管理) |

更新コマンド:

```powershell
# 全サブモジュール更新
git submodule update --remote --merge

# _creations-ai のみ
git submodule update --remote _creations-ai

# _creations-db のみ (develop ブランチ)
git submodule update --remote _creations-db
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

## 4. `.env` の作成

リポジトリ直下に `.env` を作り、最低限以下を入れる。 **絶対にコミットしない** こと (`.gitignore` で除外済)。

```ini
# --- 必須 ---
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# --- 任意 (デフォルト値) ---
# Gemini / Imagen
IMAGEN_MODEL=imagen-3.0-generate-001
GEMINI_REFERENCE_MODEL=models/gemini-3.1-flash-image

# OpenAI
DALLE_MODEL=dall-e-3                   # この環境で dall-e-3 が NotFound なら gpt-image-1 にする
OPENAI_IMAGE_QUALITY=standard          # gpt-image-1 では medium / high が有効
GPT_MODEL=gpt-4o                       # prompt-assist モード用

# 出力先
OUTPUT_BASE_DIR=output                 # 互換のため OUTPUT_DIR も読まれる

# 形態共通データセット (作品別ファイルを上書きしたいときだけ)
FORM_COMMON_DATASET_PATH=

# 創作 DB パッケージ参照を一時的に無効化したい場合
CREATIONS_DB_PACKAGE_ENABLE=1
```

### 検証されている組み合わせ

- **Gemini**: `imagen-4.0-generate-001` (上位互換) と multimodal `gemini-3.1-flash-image` を併用する経路が安定。
- **OpenAI**: 環境によって `dall-e-3` が `model does not exist` を返す。その場合は `DALLE_MODEL=gpt-image-1`、`OPENAI_IMAGE_QUALITY=medium` (または `high`) を指定すると通る。

---

## 5. PowerShell 利用時の注意

- 仮想環境アクティベート: `.\.venv\Scripts\Activate.ps1`
- コマンドの連結に `&&` を使わない。代わりに `;` で区切る。
- 日本語出力が文字化けする場合は `$env:PYTHONIOENCODING="utf-8"` を先に設定。
- `npm test` がうまく解決されない場合は `npm.cmd test` を使う ([`_creations-db/`](../_creations-db) でのみ使用)。

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

実行後、`output/{YYYYMMDD}/{YYYYMMDD_HH}/{ts}_gemini_corefolder_num057/` に
`prompt.txt` / `run_meta.json` / `notes.md` + 生成画像が出ていれば成功。

---

## 7. よくあるトラブル

| 症状                                                 | 対処                                                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `GEMINI_API_KEY が設定されていません`                | `.env` を作成・編集後、ターミナルを再起動 (または `Activate.ps1` を再実行)            |
| `invalid_request_error (400)` で画像が弾かれる       | [`tools.md`](tools.md) の `check_image_mime` を参照。実体 MIME と拡張子の不一致が原因 |
| OpenAI で `The model 'dall-e-3' does not exist`      | `.env` の `DALLE_MODEL=gpt-image-1` に切替                                            |
| 仮想環境を作ったのに `pip install` が global に入る  | `Activate.ps1` を実行したか確認。`where.exe python` で `.venv` 配下か確認             |
| サブモジュール (`_creations-db/data/...`) の中身が空 | `git submodule update --init --recursive` を実行                                      |
