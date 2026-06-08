# src ディレクトリ

画像生成スクリプト群を配置しています。

## 構成

- `gemini/generate.py` — Google Imagen 3 による画像生成
- `openai/generate.py` — DALL-E 3 による画像生成 / GPT-4o によるプロンプト補助
- `utils/dataset.py` — `manifest-training.jsonl` 読み込み・プロンプト組み立てユーティリティ
- `utils/paths.py` — 実行ごとの出力ディレクトリ生成ユーティリティ
- `utils/run_log.py` — 実行ごとの `prompt.txt` / `run_meta.json` / `notes.md` 保存ユーティリティ

## セットアップ

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# .env を作成して API キーを設定
copy .env.example .env
# .env を編集して GEMINI_API_KEY / OPENAI_API_KEY を入力
```

## 使用例

```bash
# Imagen 3 で 57(イズナ) のコアフォルダ形態を生成
python -m src.gemini.generate --num 57 --form corefolder

# DALL-E 3 で生成
python -m src.openai.generate --num 57 --form corefolder

# GPT-4o でプロンプト改善提案を取得
python -m src.openai.generate --num 57 --mode prompt-assist --scene "図書館で本を読んでいるシーン"
```

## 出力パス規則

- 生成画像は実行ごとに `output/{YYYYMMDD_HHMMSS}_{provider}_{form}_num{NNN}/` へ保存されるようになったよ。
  - 例: `output/20260608_174532_gemini_corefolder_num057/num057_corefolder_01.png`
  - 例: `output/20260608_174604_openai_humanoid_num057/num057_humanoid_dalle.png`
- ベースディレクトリは `OUTPUT_BASE_DIR` (なければ `OUTPUT_DIR`、それもなければ `output`) を読む。
- `--out <dir>` を指定してもその配下にタイムスタンプ付きサブフォルダを切るため、上書き事故は起きないよ。

## 参照画像の扱い

- `manifest-training.jsonl` の `ai_hints.*.reference_images` と、レコード内の `images` (創作DB由来ローカル画像) を自動収集します。
- Gemini 生成では、参照画像 URL/ローカルパスをプロンプトに明示して作風合わせを強化します。
- OpenAI の `prompt-assist` では、既存画像を GPT-4o へマルチモーダル入力として添付します（URL + ローカル画像）。

## 形態共通データセット (作品別)

- 作品ごとの形態共通特徴は `_ideas/form_common_datasets/{Works_XXX}.json` に置きます。
  - 例: `_ideas/form_common_datasets/Works_NumberTales.json`
- 読み込み優先順位は `FORM_COMMON_DATASET_PATH` (環境変数) → 作品別ファイル → (フォールバックなし)。
- corefolder / humanoid 双方について、`definition_*` / `surface_description_*` / `texture_traits[]` / `common_equipment[]` / `required_shape_keywords[]` / `disallow_cross_form_keywords[]` などを定義しておくと、プロンプト本文に自動で差し込まれます。

## 実行ログ

- 各実行ごとに `output/{ts}_{provider}_{form}_numNNN/` の中に次の 3 ファイルを保存します。
  - `prompt.txt` — モデルに渡したプロンプト本文
  - `run_meta.json` — 実行メタ（provider/model/参照画像/生成結果/エラー要旨など）
  - `notes.md` — 手書きレビュー用テンプレ（成功度・気になった点・改善案）
- 失敗時もログは残るので、成功プロンプトと失敗プロンプトを後から見比べやすくしています。
