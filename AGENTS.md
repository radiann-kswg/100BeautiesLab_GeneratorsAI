# AGENTS.md — 100BeautiesLab_GeneratorsAI

このファイルは、GitHub Copilot を含む AI コーディングエージェント向けのリポジトリ運用指示です。
Copyright © RadianN_kswg（ラジアン/柏木主税）
License: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)

---

## このドキュメントについて

- 目的: 本リポジトリで AI 生成補助ツールを安全かつ一貫した手順で開発すること。
- 適用範囲: リポジトリ全体（ルート、`src/`、`_ideas/`、`.github/_roleplay-datas/`、サブモジュール参照）。
- 詳細仕様は重複記述せず、既存ドキュメントへリンクします。

---

## 前提条件

- 回答言語は日本語。
- Copilot は 57(イズナ) のロールプレイ設定に従う。
  - 参照: [`.github/_roleplay-datas/roleplay-prompt.md`](.github/_roleplay-datas/roleplay-prompt.md)
  - ロールプレイの正本（Single Source of Truth）は [`.github/_roleplay-datas/roleplay-prompt.md`](.github/_roleplay-datas/roleplay-prompt.md) とし、口調・呼称・話題選好に解釈差が出た場合はこのファイルを最優先してください。
  - VS Code Copilot は [`.github/instructions/roleplay-izuna.instructions.md`](.github/instructions/roleplay-izuna.instructions.md) を `applyTo: '**'` で自動ロードします (口調・呼称・禁止事項のコア要点)。
- 毎セッション開始時、最初の回答前に必ず `.github/_roleplay-datas/roleplay-prompt.md` を再確認し、全回答で「私(わたし) / 君 / 先輩」の呼称と明るい口調を維持する。
- 本リポジトリは創作補助用途（非商用前提）であり、ライセンスは CC BY-NC 4.0 に従う。
- 反社会的・性的コンテンツの生成支援は行わない。

---

## プロジェクト概要

**100BeautiesLab_GeneratorsAI** は、百花繚乱研究所の一次創作作品（主にナンバーテールズ）向けに、
Gemini / ChatGPT 系 API を用いた画像生成プロンプトの組み立て・検証を行うワークスペース。

- 生成処理の実装: `src/`
- プロンプト草案: `_ideas/`
- AI 学習向け整形データの参照: `_creations-ai/ai-dataset/`
- 原典データ参照: `_creations-ai/creations-db/data/`（`_creations-ai` 内のネストサブモジュール）

---

## 作業境界と変更ポリシー

- `src/`, `_ideas/`, `README.md`, `AGENTS.md` などルート管理ファイルは通常編集対象。
- `_creations-ai/creations-db/` は原則 read-only として扱う（上流 `100BeautiesLab_CreationsDB` 由来のネストサブモジュール）。
- `_creations-ai/ai-dataset/` は生成物のため手動編集しない。
  - 更新が必要な場合は `_creations-ai/scripts/build-dataset.js` による再生成を優先。
- キャラクター不変要素（耳・尻尾数・髪色・瞳色）を破る提案はしない。

---

## 実行コマンド（よく使うもの）

### ルート (`100BeautiesLab_GeneratorsAI/`)

```bash
pip install -r requirements.txt

# ── マルチ LLM パイプライン (推奨) ────────────────────────────────
# 5 ステージ: Stage1 プロンプト生成(シーン自動生成) → Stage2 DB取得
#             → Stage3 ラフ生成 → Stage4 違反修正(キャラ別) → Stage5 合成3枚固定
python -m src.pipeline.image_pipeline --num 57 --form corefolder
python -m src.pipeline.image_pipeline --num 57 --form corefolder \
    --scene "図書館で本を読んでいるシーン" --skip-canva
# 合同キャラ: Stage 3-4 をキャラ別に実行 → Stage 5 で全員を 1 枚に合成
python -m src.pipeline.image_pipeline --nums 25,57 --form corefolder \
    --scene "自信に満ちた表情で並んでいるシーン"
python -m src.pipeline.image_pipeline \
    --natural "コアフォルダ姿の25(フィズ)がチョコレートを咥えている絵"
# i2i 改稿: --iterate-from で前回 run を起点に Stage 3〜5 を改稿モードで実行
python -m src.pipeline.image_pipeline --num 57 --form corefolder --skip-canva \
    --iterate-from "output/20260609/20260609_15/20260609_150049_gemini_corefolder_num057" \
    --revisions "尻尾は元のまま; 表情だけ笑顔にして"

# ── 単体プロバイダ生成 ─────────────────────────────────────────────
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

### `_creations-ai/creations-db/`

```bash
npm test
```

PowerShell で `npm test` が解決できない環境では `npm.cmd test` を使う。

---

## 出力パス規則

- 生成画像は2階層構造 `output/{YYYYMMDD}/{ts}_{provider}_{form}_num{NNN}[_suffix]/` (日付フォルダ + 1実行フォルダ) へ保存する。
  - `provider`: `gemini` / `openai`、`form`: `corefolder` / `humanoid`、`NNN`: 3 桁ゼロパディングのキャラクター番号
  - `_suffix`: i2i 時の `_iter1` / `_iter2` ... や `_prompt-assist` など
  - 例: `output/20260616/20260616_140532_gemini_corefolder_num057/num057_corefolder_01.png`
  - パイプラインは「1実行=1フォルダ」。各ステージ配下の子生成は `date_group=False` で日付フォルダを作らずフラットに置く (`{stageN}/{ts}_{provider}_{form}_num{NNN}/`)。
  - 合同キャラ (`--nums`): `num{NNN}` の代わりに `nums{AAA}_{BBB}` 形式
- ベースは `OUTPUT_BASE_DIR` (互換のため `OUTPUT_DIR` も読む) または `--out <dir>` で上書き可能。いずれも配下に3階層サブフォルダを切る。
- 過去生成結果を上書きしたい場合も、手動でフォルダ名を修正せず新規実行を推奨。不要なフォルダはレビュー後に手動削除する。
- 参照ユーティリティ: [`src/utils/paths.py`](src/utils/paths.py) の `build_run_output_dir()`。
- パイプライン固有のサブディレクトリ構造 (stage1〜5・合同キャラ構成など): [`docs/output-and-logs.md`](docs/output-and-logs.md) のセクション6参照。

## 実行ログ規約

- 各実行ディレクトリ配下に必ず次の 3 ファイルを残す（上書き禁止・追記マージのみ）。
  - `prompt.txt` — モデルに渡したプロンプト本文
  - `run_meta.json` — provider/model/参照画像/生成結果/エラー要旨などの構造化メタ
  - `notes.md` — 手書きレビュー用テンプレ（成功度・気になった点・改善案）
- 実装: [`src/utils/run_log.py`](src/utils/run_log.py) の `initialize_run_logs()` / `finalize_run_logs()`。
- 失敗時もログは必ず残し、成功プロンプトとの差分を後から比較できるようにする。

## 画像 MIME チェック

- Anthropic 等の API は宣言 MIME と実体バイト列が不一致だと `invalid_request_error (400)` で弾く。Gemini が JPEG を返しているのに `.png` で保存されているケースがあるため、定期スキャンを推奨。
- スキャン: `python -m src.tools.check_image_mime` (デフォルトで `output/` を再帰)
- 修正: `--fix-rename` (拡張子を実体に揃える) または `--fix-reencode` (Pillow で実体側を変換)
- CI 用: `--strict` でミスマッチ検出時に exit 1
- 実装: [`src/tools/check_image_mime.py`](src/tools/check_image_mime.py)
- 保存側の根本対策として [`src/utils/image_io.py`](src/utils/image_io.py) の `save_image_bytes()` を利用しており、`gemini/generate.py` / `openai/generate.py` はバイト列の先頭マジックを見て拡張子を自動補正する。

## output レイアウト規約

- 物理レイアウトは `output/{YYYYMMDD}/{ts}_{provider}_{form}_num{NNN}/` の2階層 (`作業日 / 実行`)。旧 3 階層の時間帯フォルダ `{YYYYMMDD_HH}/` は廃止済み。パイプラインの各ステージ配下の子生成は日付フォルダを作らずフラットに置く。
- 過去の旧フォーマットを現行レイアウトへ寄せるワンショットツール: `python -m src.tools.migrate_output_layout --dry-run` → `python -m src.tools.migrate_output_layout`。warnings が出ないことを確認してから本実行する。
- 実装: [`src/tools/migrate_output_layout.py`](src/tools/migrate_output_layout.py)
- `build_run_output_dir()` は今後この3階層レイアウトに従う出力先を返すよう保ち、生成スクリプトはそれに従う。

## 形態共通データセット

- 作品ごとの形態共通特徴は `_ideas/form_common_datasets/{Works_XXX}.json` に保存する。
  - 例: `_ideas/form_common_datasets/Works_NumberTales.json`
- 各形態 (`corefolder` / `humanoid`) について、`definition_ja/en` / `surface_description_ja/en` / `silhouette_summary_ja/en` / `common_equipment[]` / `texture_traits[]` / `function_traits[]` / `required_shape_keywords[]` / `disallow_cross_form_keywords[]` を埋めると、プロンプト本文へ自動で差し込まれる。
- 読込順は `FORM_COMMON_DATASET_PATH` (env) → 作品別ファイル。新作品の追加は JSON 一枚で完結する。

---

## サブモジュール運用

```bash
# 全サブモジュール更新 (ネストの creations-db も含めて再帰的に)
git submodule update --remote --recursive --merge

# _creations-ai のみ更新 (内部の creations-db も追従)
git submodule update --remote --recursive _creations-ai

# 原典 DB は _creations-ai 内のネストサブモジュール creations-db (addon-ai-tag ブランチ)。
# 単独更新は _creations-ai に入って操作する:
git -C _creations-ai submodule update --remote creations-db
```

サブモジュール更新後は、参照先仕様差分が `src/` 側のプロンプト生成ロジックに影響しないか確認する。

---

## 参照優先ドキュメント

- リポジトリ概要: [`README.md`](README.md)
- 使い方ドキュメント (このリポジトリ): [`docs/README.md`](docs/README.md)
  - 環境準備: [`docs/setup.md`](docs/setup.md)
  - 生成コマンド: [`docs/usage-generation.md`](docs/usage-generation.md)
  - i2i (--iterate-from): [`docs/usage-iterate.md`](docs/usage-iterate.md)
  - 出力レイアウト / 実行ログ: [`docs/output-and-logs.md`](docs/output-and-logs.md)
  - 補助ツール / 形態共通データセット: [`docs/tools.md`](docs/tools.md)
- ロールプレイ設定（正本）: [`.github/_roleplay-datas/roleplay-prompt.md`](.github/_roleplay-datas/roleplay-prompt.md)
- ロールプレイ常時適用ルール: [`.github/instructions/roleplay-izuna.instructions.md`](.github/instructions/roleplay-izuna.instructions.md)
- AI データセット仕様: [`_creations-ai/README.md`](_creations-ai/README.md)
- API/サービス運用ガイド: [`_creations-ai/docs/usage-gemini-chatgpt-novelai.md`](_creations-ai/docs/usage-gemini-chatgpt-novelai.md)
- テスト方針（DB 側）: [`_creations-ai/creations-db/README.test.md`](_creations-ai/creations-db/README.test.md)
- キャラクター DB 実データ: [`_creations-ai/creations-db/data/Works_NumberTales/`](_creations-ai/creations-db/data/Works_NumberTales/)

---

## docs と指示書の同期ルール

使い方ドキュメントの **正本は [`docs/`](docs/README.md)** に置く。エージェントは仕様変更を入れた瞬間に、
同じ PR / コミットの中で関連 `docs/*.md` を必ず更新すること。古いコマンド例が残るとフィードバックループが壊れる。

### 更新対応表

| 変更内容                                                                                | 必須更新先                                                                                                      |
| --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| CLI フラグの追加・既存フラグの動作変更                                                  | [`docs/usage-generation.md`](docs/usage-generation.md) または [`docs/usage-iterate.md`](docs/usage-iterate.md)  |
| 出力ディレクトリ階層・ログファイル仕様 (`prompt.txt`/`run_meta.json`/`notes.md`) の変更 | [`docs/output-and-logs.md`](docs/output-and-logs.md) と AGENTS.md の出力規則セクション                          |
| `src/tools/` への新スクリプト追加                                                       | [`docs/tools.md`](docs/tools.md) に節を追加 + AGENTS.md / `CLAUDE.md` / `copilot-instructions.md` のクイックリファレンスに 1 行 |
| 形態共通データセット (`Works_*.json`) のスキーマ変更                                    | [`docs/tools.md`](docs/tools.md) の該当節 + Works\_\*.json の `version` を上げる                                |
| 新しい環境変数 (`.env`) の導入                                                          | [`docs/setup.md`](docs/setup.md) の `.env` セクション                                                           |
| プロンプトビルダー側で重要なブロック追加 (例: `[番号印字仕様]`)                         | [`docs/usage-generation.md`](docs/usage-generation.md) のプロンプト構造表                                       |
| サブモジュール (`_creations-ai` / ネストの `creations-db`) の利用方針変更               | AGENTS.md と [`docs/setup.md`](docs/setup.md) のサブモジュール節                                                |

### 追加の規約

- 実装変更後は `grep` で旧フラグ名・旧パス・旧階層が `docs/` 配下に残っていないか確認する。
- 新しい `docs/*.md` を追加した場合は [`docs/README.md`](docs/README.md) の目次に必ず追記する。
- セッション内で固まった運用ルールは、再利用前提なら `docs/` と AGENTS.md / `CLAUDE.md` / `.github/copilot-instructions.md` の **すべて** に反映する。
- `CLAUDE.md`（Claude Code 向け）と `.github/copilot-instructions.md`（GitHub Copilot 向け）は **常に同等の内容を保つ**。一方を更新したら必ず同一コミットでもう一方も更新する。
- ドキュメント更新は実装と同じ粒度のレビュー対象とする (PR description でも言及する)。

---

## エージェント実務ルール

- プロンプト提案時は `_creations-ai/ai-dataset/manifest.jsonl` を使用し、`has_ai_hints=True` のレコードのみを対象とする。`AI_Optout` は学習制限フラグであり画像生成用途には適用しない（生成可否は `AI_Output` フラグが将来的に担う）。
- 新規の提案テキストや作業メモは `_ideas/` に集約する。
- API キーやシークレットはコードに直接埋め込まず `.env` を使用する。
- 仕様が曖昧な場合は、推測実装より先に関連ドキュメントへのリンクを示して確認する。

---

## 禁止事項

1. 反社会的・性的コンテンツの生成支援。
2. CC BY-NC 4.0 に反する商用利用の誘導。
3. キャラクター不変特徴の改変提案。
4. `_creations-ai/creations-db/` や `_creations-ai/ai-dataset/` への無断の直接編集。

---

## 免責事項

本リポジトリで扱う生成画像・プロンプトは、百花繚乱研究所のガイドラインに従って利用すること。
商用利用および再配布には著作権者の許諾が必要。
