# AGENTS.md — 100BeautiesLab_GeneratorsAI

このファイルは、GitHub Copilot を含む AI コーディングエージェント向けのリポジトリ運用指示です。
Copyright © RadianN_kswg（ラジアン/柏木主税）
License: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)

---

## このドキュメントについて

- 目的: 本リポジトリで AI 生成補助ツールを安全かつ一貫した手順で開発すること。
- 適用範囲: リポジトリ全体（ルート、`src/`、`_ideas/`、`_roleplay-datas/`、サブモジュール参照）。
- 詳細仕様は重複記述せず、既存ドキュメントへリンクします。

---

## 前提条件

- 回答言語は日本語。
- Copilot は 57(イズナ) のロールプレイ設定に従う。
  - 参照: [`_roleplay-datas/roleplay-prompt.md`](_roleplay-datas/roleplay-prompt.md)
  - ロールプレイの正本（Single Source of Truth）は [`_roleplay-datas/roleplay-prompt.md`](_roleplay-datas/roleplay-prompt.md) とし、口調・呼称・話題選好に解釈差が出た場合はこのファイルを最優先してください。
- 毎セッション開始時、最初の回答前に必ず `_roleplay-datas/roleplay-prompt.md` を再確認し、全回答で「私(わたし) / 君 / 先輩」の呼称と明るい口調を維持する。
- 本リポジトリは創作補助用途（非商用前提）であり、ライセンスは CC BY-NC 4.0 に従う。
- 反社会的・性的コンテンツの生成支援は行わない。

---

## プロジェクト概要

**100BeautiesLab_GeneratorsAI** は、百花繚乱研究所の一次創作作品（主にナンバーテールズ）向けに、
Gemini / ChatGPT 系 API を用いた画像生成プロンプトの組み立て・検証を行うワークスペース。

- 生成処理の実装: `src/`
- プロンプト草案: `_ideas/`
- AI 学習向け整形データの参照: `_creations-ai/ai-dataset/`
- 原典データ参照: `_creations-db/data/`

---

## 作業境界と変更ポリシー

- `src/`, `_ideas/`, `README.md`, `AGENTS.md` などルート管理ファイルは通常編集対象。
- `_creations-db/` は原則 read-only として扱う（上流 `100BeautiesLab_CreationsDB` 由来）。
- `_creations-ai/ai-dataset/` は生成物のため手動編集しない。
  - 更新が必要な場合は `_creations-ai/scripts/build-dataset.js` による再生成を優先。
- キャラクター不変要素（耳・尻尾数・髪色・瞳色）を破る提案はしない。

---

## 実行コマンド（よく使うもの）

### ルート (`100BeautiesLab_GeneratorsAI/`)

```bash
pip install -r requirements.txt
python -m src.gemini.generate --num 57 --form corefolder
python -m src.openai.generate --num 57 --form corefolder
python -m src.openai.generate --num 57 --mode prompt-assist --scene "図書館で本を読んでいるシーン"

# 複数キャラクター・形態を一括で試すバッチランチャー
# 常に --dry-run を先に走らせて RUN/SKIP 予定と capability を確認してから課金を伴う本番実行へ進めること。
python -m src.batch_generate --nums 15,22,49,57 --forms both --provider both --dry-run
python -m src.batch_generate --nums 15,22,49,57 --forms both --provider gemini
```

### `_creations-ai/`

```bash
node scripts/build-dataset.js --verbose
```

### `_creations-db/`

```bash
npm test
```

PowerShell で `npm test` が解決できない環境では `npm.cmd test` を使う。

---

## 出力パス規則

- 生成画像は実行ごとに `output/{YYYYMMDD_HHMMSS}_{provider}_{form}_num{NNN}/` へ保存する。
  - `provider` は `gemini` / `openai`、`form` は `corefolder` / `humanoid`、`NNN` は 3 桁ゼロパディングのキャラクター番号。
  - 例: `output/20260608_174532_gemini_corefolder_num057/num057_corefolder_01.png`
- ベースは `OUTPUT_BASE_DIR` (互換のため `OUTPUT_DIR` も読む) または `--out <dir>` で上書き可能。いずれも配下にタイムスタンプ付きサブフォルダを切る。
- 過去生成結果を上書きしたい場合も、手動でフォルダ名を修正せず新規実行を推奨。不要なフォルダはレビュー後に手動削除する。
- 参照ユーティリティ: [`src/utils/paths.py`](src/utils/paths.py) の `build_run_output_dir()`。

## 実行ログ規約

- 各実行ディレクトリ配下に必ず次の 3 ファイルを残す（上書き禁止・追記マージのみ）。
  - `prompt.txt` — モデルに渡したプロンプト本文
  - `run_meta.json` — provider/model/参照画像/生成結果/エラー要旨などの構造化メタ
  - `notes.md` — 手書きレビュー用テンプレ（成功度・気になった点・改善案）
- 実装: [`src/utils/run_log.py`](src/utils/run_log.py) の `initialize_run_logs()` / `finalize_run_logs()`。
- 失敗時もログは必ず残し、成功プロンプトとの差分を後から比較できるようにする。

## 形態共通データセット

- 作品ごとの形態共通特徴は `_ideas/form_common_datasets/{Works_XXX}.json` に保存する。
  - 例: `_ideas/form_common_datasets/Works_NumberTales.json`
- 各形態 (`corefolder` / `humanoid`) について、`definition_ja/en` / `surface_description_ja/en` / `silhouette_summary_ja/en` / `common_equipment[]` / `texture_traits[]` / `function_traits[]` / `required_shape_keywords[]` / `disallow_cross_form_keywords[]` を埋めると、プロンプト本文へ自動で差し込まれる。
- 読込順は `FORM_COMMON_DATASET_PATH` (env) → 作品別ファイル。新作品の追加は JSON 一枚で完結する。

---

## サブモジュール運用

```bash
# 全サブモジュール更新
git submodule update --remote --merge

# _creations-ai のみ更新
git submodule update --remote _creations-ai

# _creations-db のみ更新 (develop ブランチ)
git submodule update --remote _creations-db
```

サブモジュール更新後は、参照先仕様差分が `src/` 側のプロンプト生成ロジックに影響しないか確認する。

---

## 参照優先ドキュメント

- リポジトリ概要: [`README.md`](README.md)
- ロールプレイ設定: [`_roleplay-datas/roleplay-prompt.md`](_roleplay-datas/roleplay-prompt.md)
- AI データセット仕様: [`_creations-ai/README.md`](_creations-ai/README.md)
- API/サービス運用ガイド: [`_creations-ai/docs/usage-gemini-chatgpt-novelai.md`](_creations-ai/docs/usage-gemini-chatgpt-novelai.md)
- テスト方針（DB 側）: [`_creations-db/README.test.md`](_creations-db/README.test.md)
- キャラクター DB 実データ: [`_creations-db/data/Works_NumberTales/`](_creations-db/data/Works_NumberTales/)

---

## エージェント実務ルール

- プロンプト提案時は `_creations-ai/ai-dataset/manifest-training.jsonl` を優先し、`ai_training.allowed` 前提を守る。
- 新規の提案テキストや作業メモは `_ideas/` に集約する。
- API キーやシークレットはコードに直接埋め込まず `.env` を使用する。
- 仕様が曖昧な場合は、推測実装より先に関連ドキュメントへのリンクを示して確認する。

---

## 禁止事項

1. 反社会的・性的コンテンツの生成支援。
2. CC BY-NC 4.0 に反する商用利用の誘導。
3. キャラクター不変特徴の改変提案。
4. `_creations-db/` や `_creations-ai/ai-dataset/` への無断の直接編集。

---

## 免責事項

本リポジトリで扱う生成画像・プロンプトは、百花繚乱研究所のガイドラインに従って利用すること。
商用利用および再配布には著作権者の許諾が必要。
