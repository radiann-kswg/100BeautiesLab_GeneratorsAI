# src ディレクトリ

画像生成スクリプト群を配置しています。

## 構成

- `gemini/generate.py` — Google Imagen 3 による画像生成
- `openai/generate.py` — DALL-E 3 による画像生成 / GPT-4o によるプロンプト補助
- `adobe/generate.py` — Adobe Firefly Services によるテキスト→画像生成 (provider: adobe)
- `canva/generate.py` — Canva Connect API による生成済み画像のデザイン化・書き出し (provider: canva, `--from-image` 必須)
- `utils/dataset.py` — `manifest.jsonl` 読み込み・プロンプト組み立てユーティリティ
- `utils/paths.py` — 実行ごとの出力ディレクトリ生成ユーティリティ
- `utils/run_log.py` — 実行ごとの `prompt.txt` / `run_meta.json` / `notes.md` 保存ユーティリティ
- `tools/check_image_mime.py` — 画像ファイルの拡張子と実体フォーマット (PNG/JPEG/GIF/WEBP/BMP/TIFF) の不一致を検出・修正する CLI ツール

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

- `manifest.jsonl` の `ai_hints.*.reference_images` と、レコード内の `images` (創作DB由来ローカル画像) を自動収集します。
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

## 画像 MIME チェック (再発防止)

API 側 (Anthropic 等) は画像 base64 の宣言 MIME と実体バイト列が一致しないと
`invalid_request_error (400)` で弾きます。Gemini が JPEG を返しているのに
`.png` で保存しているケースがあるため、定期的に下記でスキャンしてください。

```bash
# output/ を再帰スキャンしてミスマッチを一覧表示
python -m src.tools.check_image_mime

# 拡張子を実体に合わせてリネーム (.png → .jpg など)
python -m src.tools.check_image_mime --fix-rename

# 実体を拡張子に合わせて Pillow で再エンコード
python -m src.tools.check_image_mime --fix-reencode

# CI 用: ミスマッチがあれば exit 1
python -m src.tools.check_image_mime --strict
```

### 保存時の MIME 自動判定

`src/utils/image_io.py` の `save_image_bytes()` がバイト列の先頭を見て
正しい拡張子を選びます。`gemini/generate.py` と `openai/generate.py` の保存処理は
このユーティリティ経由になっているので、Gemini が JPEG を返してきても
拡張子は `.jpg` で保存され、後段の MIME ミスマッチが発生しません。

## output レイアウト整理 (一回限り)

旧フォーマット (`output/{date}/{provider}/...`、`output/{ts}_..._num...` の日付階層なし、
旧 3 階層 `output/{date}/{date}_{HH}/{run}/`) を、現行 2 階層レイアウト
`output/{YYYYMMDD}/{ts}_{provider}_{form}_num{NNN}/` に
寄せるためのツールも用意しています。

```bash
# 計画だけ確認
python -m src.tools.migrate_output_layout --dry-run

# 本実行
python -m src.tools.migrate_output_layout
```
