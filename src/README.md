# src ディレクトリ

画像生成・テキスト生成パイプラインおよびユーティリティ群を配置しています。
コマンドの詳細は [`docs/`](../docs/README.md) を参照してください。

## 構成

### パイプライン

- `pipeline/image_pipeline.py` — マルチ LLM 5 ステージ画像生成パイプライン（推奨）
- `pipeline/stage_cli.py` — 5 ステージを 1 ステージずつ分割実行する CLI（時間制約環境向け）
- `pipeline/text_pipeline.py` — GPT-4o 生成 → Gemini クロスレビューのテキスト生成パイプライン
- `pipeline/natural_parser.py` — 自然文からキャラクター番号・形態・シーン等を LLM 抽出

### 単体プロバイダ

- `gemini/generate.py` — Google Imagen 3/4 および Gemini multimodal による画像生成
- `openai/generate.py` — DALL-E 3 / gpt-image-1 による画像生成 / GPT-4o によるプロンプト補助
- `adobe/generate.py` — Adobe Firefly Services によるテキスト→画像生成
- `adobe/image_ops.py` — Adobe Lightroom/Photoshop API で構図ガイドを生成（Stage 3 内部利用）
- `canva/generate.py` — Canva Connect API による生成済み画像のデザイン化・書き出し（`--from-image` 必須）
- `batch_generate.py` — 複数キャラクター × 形態 × プロバイダのバッチラッパー

### MCP サーバ

- `mcp_server/server.py` — パイプラインを MCP ツールとして公開（stdio / Streamable HTTP）

### ユーティリティ

- `utils/dataset.py` — `manifest.jsonl` 読み込み・プロンプト組み立て
- `utils/paths.py` — 実行ごとの出力ディレクトリ生成 (`build_run_output_dir()`)
- `utils/run_log.py` — `prompt.txt` / `run_meta.json` / `notes.md` 保存
- `utils/image_io.py` — バイト列マジックによる MIME 自動補正付き画像保存
- `utils/iterate.py` — `--iterate-from` の起点解決（ファイル / ディレクトリ / GCS URL 対応）

### 補助ツール (`src/tools/`)

- `tools/check_image_mime.py` — 拡張子と実体 MIME の不一致を検出・修正する CLI
- `tools/migrate_output_layout.py` — 旧出力レイアウトを現行 2 階層形式へ移行するワンショットツール
- `tools/refresh_canva_token.py` — Canva の OAuth2 PKCE トークンを取得し `.env` を自動更新
- `tools/check_sync.py` — FUSE マウント等での同期完了を確認する汎用ツール

---

## セットアップ

```powershell
# 仮想環境作成（初回のみ）
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 依存パッケージのインストール
pip install -r requirements.txt

# .env を作成して API キーを設定
cp .env.example .env
# .env を編集して GEMINI_API_KEY / OPENAI_API_KEY などを入力
```

詳細は [`docs/setup.md`](../docs/setup.md) を参照。

---

## 使用例

```powershell
# マルチ LLM パイプライン（推奨）
python -m src.pipeline.image_pipeline --num 57 --form corefolder
python -m src.pipeline.image_pipeline --nums 25,57 --form corefolder --scene "並んでいるシーン"

# Gemini 単体
python -m src.gemini.generate --num 57 --form corefolder

# OpenAI 単体
python -m src.openai.generate --num 57 --form corefolder

# GPT-4o でプロンプト改善提案を取得
python -m src.openai.generate --num 57 --mode prompt-assist --scene "図書館で本を読んでいるシーン"

# 画像 MIME チェック
python -m src.tools.check_image_mime --strict
```

---

## 出力パス規則

生成画像は **日付フォルダ + 実行フォルダの 2 階層** に保存される。

```
output/{YYYYMMDD}/{YYYYMMDD_HHMMSS}_{provider}_{form}_num{NNN}/
    ├── num057_corefolder_01.jpg   # 生成画像
    ├── prompt.txt                 # 渡したプロンプト本文
    ├── run_meta.json              # 構造化メタ
    └── notes.md                  # 手書きレビュー用テンプレ
```

- ベースディレクトリは `OUTPUT_BASE_DIR`（なければ `OUTPUT_DIR`、それもなければ `output`）。
- `--out <dir>` を指定した場合はその dir 直下に実行フォルダを直置き（日付フォルダなし）。
- `prompt.txt` / `run_meta.json` / `notes.md` は失敗時も必ず残る（上書き禁止）。

詳細は [`docs/output-and-logs.md`](../docs/output-and-logs.md) を参照。
