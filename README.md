# 100BeautiesLab GeneratorsAI

百花繚乱研究所（RadianN_kswg）のナンバーテールズシリーズ向け AI 画像生成補助リポジトリです。

**Copyright © RadianN_kswg（ラジアン/柏木主税） — [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)**

---

## 概要

本リポジトリは、**百花繚乱研究所（RadianN_kswg）の一次創作作品「ナンバーテールズ」シリーズを対象とした AI 生成補助ツール**です。
キャラクター設定データベース（[100BeautiesLab_CreationsDB](https://github.com/radiann-kswg/100BeautiesLab_CreationsDB)）をサブモジュールとして参照し、Gemini / OpenAI / Adobe Firefly API を組み合わせた **5 ステージのマルチ LLM 画像生成パイプライン**で画像生成プロンプトの構築・検証・改稿を行います。

> **本リポジトリの生成物は百花繚乱研究所の二次創作物に該当します。**
> 利用・運用にあたっては、下記の公式ガイドラインへの同意が必要です。

GitHub Copilot / Claude Code のエージェントは **57(イズナ)** として作画補助を担当します。

---

## 主な機能

### マルチ LLM 画像生成パイプライン（5 ステージ）

| ステージ | 役割 | 主要モデル |
|---|---|---|
| Stage 1 | プロンプト生成・シーン自動生成 | GPT-4o + Gemini Flash |
| Stage 2 | キャラクター DB・参照画像取得 | manifest.jsonl + creations-db |
| Stage 3 | ラフ生成（単体 5 枚 / 合同 3 枚×N 人 + 構図ラフ） | Gemini Imagen 4 |
| Stage 4 | 違反特徴の検出・修正（キャラ別） | OpenAI Vision + Gemini i2i |
| Stage 5 | 完成画像 3 枚合成 → Canva 仕上げ | Gemini + Canva Connect API |

### その他の機能

- **自然文入力** — `--natural "コアフォルダ姿の25(フィズ)が…"` でパラメータを LLM 抽出
- **複数キャラクター合同生成** — `--nums 25,57` でキャラ別ラフ→全員 1 枚合成
- **i2i 改稿** — `--iterate-from` で前回生成画像を起点に修正指示だけ当て直す
- **衣装差分** — `--costume` で不変特徴を維持したまま衣装を指定
- **テキスト生成パイプライン** — GPT-4o 生成 → Gemini クロスレビュー
- **MCP サーバ** — Cloud Run / GCE 上でパイプラインを MCP ツールとして公開
- **バッチ実行** — 複数キャラクター × 形態 × プロバイダを一括で実行

---

## クイックスタート

```powershell
# 1. リポジトリを取得（サブモジュールを含む）
git clone --recurse-submodules https://github.com/radiann-kswg/100BeautiesLab_GeneratorsAI.git
cd 100BeautiesLab_GeneratorsAI

# 2. 仮想環境を作成して依存インストール
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. .env を作成して API キーを設定
cp .env.example .env
# .env を編集して GEMINI_API_KEY / OPENAI_API_KEY を入力

# 4. 動作確認（dry-run）
python -m src.batch_generate --nums 57 --forms both --provider both --dry-run

# 5. 生成実行
python -m src.pipeline.image_pipeline --num 57 --form corefolder
```

macOS はワンショットセットアップスクリプトも用意しています。詳細は [`docs/setup.md`](docs/setup.md) を参照してください。

---

## サブモジュール

```powershell
# クローン後（サブモジュール未取得の場合）
git submodule update --init --recursive
```

| ディレクトリ | リポジトリ | 用途 |
|---|---|---|
| `_creations-ai/` | [100BeautiesLab_CreationsAI](https://github.com/radiann-kswg/100BeautiesLab_CreationsAI) | AI 学習データセット。内部に `creations-db` をネストサブモジュールとして含む |
| `_creations-ai/creations-db/` | [100BeautiesLab_CreationsDB](https://github.com/radiann-kswg/100BeautiesLab_CreationsDB) (`addon-ai-tag` ブランチ) | キャラクター原典 DB（読み取り専用） |

---

## ディレクトリ構成

```
├── src/                         # 生成スクリプト群
│   ├── pipeline/                # マルチ LLM パイプライン
│   │   ├── image_pipeline.py    #   5 ステージ画像生成（メイン）
│   │   ├── stage_cli.py         #   ステージ分割 CLI（時間制約環境向け）
│   │   └── text_pipeline.py     #   テキスト生成（GPT-4o + Gemini）
│   ├── gemini/generate.py       # Gemini Imagen 単体
│   ├── openai/generate.py       # OpenAI DALL-E / gpt-image-1 単体
│   ├── adobe/                   # Adobe Firefly / Lightroom / Photoshop
│   ├── canva/generate.py        # Canva Connect API
│   ├── mcp_server/              # MCP サーバ（Cloud Run / GCE デプロイ対応）
│   ├── batch_generate.py        # バッチラッパー
│   ├── utils/                   # プロンプト組み立て・ログ・パス管理
│   └── tools/                   # 補助ツール（MIME チェック・レイアウト移行等）
├── _creations-ai/               # AI 学習データ（サブモジュール）
│   └── creations-db/            # キャラクター DB（ネストサブモジュール・読み取り専用）
├── _ideas/                      # プロンプト草案・アイデア・形態共通データセット
├── docs/                        # 使い方ドキュメント（docs/README.md が入口）
├── deploy/                      # Cloud Run / GCE / Caddy デプロイ設定
├── scripts/                     # セットアップスクリプト等
├── .github/                     # Copilot 指示・ロールプレイ設定
├── AGENTS.md                    # AI エージェント向けリポジトリ運用指示
└── LICENCE.md                   # CC BY-NC 4.0
```

---

## 使い方ドキュメント

詳細なコマンド・フラグ・設定は [`docs/README.md`](docs/README.md) を参照してください。

| ドキュメント | 内容 |
|---|---|
| [`docs/setup.md`](docs/setup.md) | 依存パッケージ・`.env`・API キーの準備 |
| [`docs/usage-generation.md`](docs/usage-generation.md) | パイプライン・単体生成・バッチ実行のコマンドとフラグ |
| [`docs/usage-iterate.md`](docs/usage-iterate.md) | i2i 改稿（`--iterate-from` / `--revisions`）のワークフロー |
| [`docs/output-and-logs.md`](docs/output-and-logs.md) | 出力レイアウト・`run_meta.json` / `notes.md` の仕様 |
| [`docs/tools.md`](docs/tools.md) | 補助ツール・形態共通データセット管理 |
| [`docs/mcp-server.md`](docs/mcp-server.md) | MCP サーバのデプロイと運用 |

---

## 公式ガイドライン（利用前に必読）

本リポジトリを使用・運用する場合は、**百花繚乱研究所の公式ガイドラインに同意したうえで利用してください。**
生成物の扱い・再配布・AI 学習利用・表現上の禁止事項はガイドラインで定められています。

- [ガイドライン（日本語）](https://github.com/radiann-kswg/100BeautiesLab_CreationsDB/blob/develop/guideline.md)
- [Guidelines (English)](https://github.com/radiann-kswg/100BeautiesLab_CreationsDB/blob/develop/guideline.en.md)

ガイドラインの主な要点:

- **非商用目的に限り**利用可。商用利用には著作権者の個別許可が必要。
- 生成物を共有・再配布する際は**出典（百花繚乱研究所 / radiann-kswg）を明記**すること。
- キャラクターの**不変特徴（耳・尻尾数・髪色・瞳色）の無断改変**は禁止。
- 反社会的・性的表現、作者偽称、印象を著しく損なう利用は禁止。
- AI 学習利用は非営利かつ `manifest-training.jsonl` の `ai_training.allowed = true` レコードに限る。

---

## ライセンス

本リポジトリは **CC BY-NC 4.0** で統一されています。詳細・帰属表示・利用条件は [`LICENCE.md`](LICENCE.md) を参照してください。

- 本リポジトリのコード・ドキュメント・プロンプト: CC BY-NC 4.0
- 生成された画像・出力物（`output/` 等）: 原著作物の派生物として CC BY-NC 4.0 を継承
- `_creations-ai/`（ネストの `creations-db/` を含む）: 各サブモジュールのライセンス（CC BY-NC 4.0）に従う
- **非商用目的に限り利用可。** 商用利用・再配布・AI 学習利用には [`LICENCE.md`](LICENCE.md) の条件遵守または著作権者の許諾が必要。
