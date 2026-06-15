# usage-iterate.md — i2i ループ (`--iterate-from` / `--revisions`)

前回 run の生成画像を起点に、 **修正したい部分だけ最優先で当て直す** ワークフローのページ。
2026-06-09 (A7-5) で導入された機能。

> 関連: [`docs/README.md`](README.md) / [`usage-generation.md`](usage-generation.md) / [`output-and-logs.md`](output-and-logs.md)

---

## 1. 何をする機能か

たとえばこういう状況:

> #57 corefolder を生成したけど、 **球体形態と尻尾は完璧**。
> ただ表情だけ笑顔にしたい。背景もシンプルにしたい。

普通に再生成すると、せっかく揃ったシルエットや色まで変わってしまう。
そこで **直前の画像を起点に渡し、変えたいところだけテキストで指示する** のが i2i ループ。

両プロバイダ共通で以下を行う:

1. 起点画像を **参照ローカルの先頭** に強制挿入
   - Gemini: `Part.from_bytes` の先頭で `gemini-3.1-flash-image` に渡す
   - OpenAI (`gpt-image-1`): `images.edit` の先頭画像として投入
2. プロンプト最先頭に **`[修正指示]` ブロック** を挿入 (他のブロックより優先される位置)
3. 出力先サブフォルダ名の末尾に **`_iter1` / `_iter2` ...** を付ける (既存 run を上書きしない)
4. `run_meta.json` に **`iteration: {label, source_image, source_dir, revisions[]}`** を記録

---

## 2. フラグ

| フラグ           | 型 / 既定値 | 役割                                                                       |
| ---------------- | ----------- | -------------------------------------------------------------------------- |
| `--iterate-from` | str / None  | 起点画像のパス。 **ファイル直指定** または **run ディレクトリ指定** が可能 |
| `--revisions`    | str / None  | 修正指示。 **`;` または改行で複数項目** に分割される                       |

### `--iterate-from` の解決ルール (`src/utils/iterate.py`)

- 値が **ファイル** ならそのまま起点として採用。
- 値が **ディレクトリ** なら配下の `num*.{png,jpg,jpeg,webp}` を mtime 降順で 1 件選ぶ。
  - 見つからない場合は `*.{png,jpg,jpeg,webp}` まで広げてフォールバック。
  - それでも 0 件なら `FileNotFoundError` で異常終了する。
- サポート拡張子: `.png` / `.jpg` / `.jpeg` / `.webp`。

### `iter` ラベルの自動計算 (`next_iteration_label`)

- 起点ファイル名 / 親ディレクトリ名に `iterN` パターンがあれば → `iter{N+1}`
- 無ければ → `iter1`
- 例:
  - `..._num057/num057_corefolder_01.png` → `iter1`
  - `..._num057_iter1/...png` → `iter2`
  - `..._num057_iter3/...png` → `iter4`

---

## 3. 使用例

### Gemini で改稿

```powershell
# 直前 run dir を起点に、修正指示を 2 件
python -m src.gemini.generate --num 57 --form corefolder `
  --iterate-from "output/20260609/20260609_15/20260609_150049_gemini_corefolder_num057" `
  --revisions "尻尾は元のまま; 表情だけ笑顔にして"
```

### OpenAI (gpt-image-1) で改稿

```powershell
# 画像ファイル直指定でもOK
python -m src.openai.generate --num 57 --form corefolder --mode dalle `
  --iterate-from "output/20260609/20260609_15/20260609_150100_openai_corefolder_num057/num057_corefolder_dalle.png" `
  --revisions "番号位置を頭部寄りに; マーキングを少し大きく"
```

> OpenAI で i2i を効かせるには、`.env` の `DALLE_MODEL=gpt-image-1` が必須。
> `dall-e-3` は `images.edit` で複数画像入力に未対応のため、純テキスト生成にフォールバックしてしまう。

### 修正指示の文法

```text
# セミコロン区切り
--revisions "尻尾は元のまま; 表情だけ笑顔にして; 背景は白"

# 改行区切りでもOK (PowerShell では here-string が便利)
--revisions @"
尻尾は元のまま
表情だけ笑顔にして
背景は白
"@
```

`parse_revisions()` は前後空白を除去し、空行を捨てる。最終的に `list[str]` でプロンプトに渡る。

---

## 4. プロンプト本文への差し込み位置

`build_dalle_prompt` / `build_gemini_prompt` で revisions が空でない場合、
プロンプト先頭に以下のブロックが入る (`_build_revision_block`)。

```text
[修正指示 (添付された前回生成画像を起点に・最優先で適用)]
- 添付の参照画像のうち先頭の 1 枚は『直前 run の生成結果』です。
- そのキャラクター個性 (シルエット / ポーズ / 配色) は可能な限り維持し、以下の修正項目だけを適用してください。
- 修正: 尻尾は元のまま
- 修正: 表情だけ笑顔にして
```

このブロックは `[参照画像]` / `[素体特徴]` / `[今回の姿]` などより **前** に置かれる。
モデルが「最初に読む長文」になるため、修正の優先度が最も高く伝わる。

---

## 5. 出力先と run_meta.json

### 出力先

```text
output/{YYYYMMDD}/{ts}_{provider}_{form}_num{NNN}_iter{N}/
```

- 例: `output/20260616/20260616_161200_gemini_corefolder_num057_iter1/`

通常 run と同じく `prompt.txt` / `run_meta.json` / `notes.md` + 生成画像が保存される。

### run_meta.json の `iteration` フィールド

```json
{
  "iteration": {
    "label": "iter1",
    "source_image": "output/20260609/20260609_15/20260609_150049_gemini_corefolder_num057/num057_corefolder_01.png",
    "source_dir": "output/20260609/20260609_15/20260609_150049_gemini_corefolder_num057",
    "revisions": ["尻尾は元のまま", "表情だけ笑顔にして"]
  }
}
```

これを辿ると、改稿チェーン全体 (どの画像 → どの修正 → どの結果) を後から再現できる。

---

## 6. ベストプラクティス

1. **1 回の改稿で当てる修正は 2〜3 件まで** に絞る。多すぎるとモデルが全部反映できず、元シルエットも崩れやすい。
2. **`scene` / `style` / `composition` / `background` も同時に指定可** 。シーン変更だけしたい場合 (例: 背景だけ変える) は `--revisions` を省略して `--background "white"` などでも OK。
3. **改稿チェーンが長くなったら一度仕切り直す** 。`iter3` を超えるとキャラ同一性が薄れることが多い。良い結果が出た時点で初期 run に近づけて再開する。
4. **`gpt-image-1` の `quality=high`** は表情の引き出しに有効。コアフォルダで笑顔・ウインクなどを当てたい時に活躍する。
5. 改稿後の `notes.md` には **元の run の相対パス** をメモしておくと、後で比較しやすい。

---

## 7. パイプライン経由の i2i (推奨)

`--iterate-from` / `--revisions` は `src.pipeline.image_pipeline` でも使用できる。
こちらを使うと **Stage 4 (違反修正) → Stage 5 (Canva 仕上げ)** も自動で走り、
完成画像 3 枚まで一気に生成できる。

### コマンド例

```powershell
# 単発 Gemini i2i の代わりに 5 ステージ全体を回す
python -m src.pipeline.image_pipeline --num 57 --form corefolder `
    --iterate-from "output/20260616/.../20260616_150049_gemini_corefolder_num057" `
    --revisions "尻尾は元のまま; 表情だけ笑顔にして" `
    --skip-canva

# Canva 仕上げも含めてフル実行
python -m src.pipeline.image_pipeline --num 57 --form corefolder `
    --iterate-from "output/20260616/.../num057_corefolder_01.jpg" `
    --revisions "背景を白に; 番号マーキングを大きく"
```

### 単体 i2i との違い

| 項目 | 単体 (`src.gemini.generate`) | パイプライン (`src.pipeline.image_pipeline`) |
|---|---|---|
| Stage 1 (プロンプト精製) | なし | あり (GPT-4o + Gemini Flash) |
| Stage 3 (ラフ生成) | 1〜4 枚 | 5 枚 (i2i) |
| Stage 4 (違反修正) | なし | あり |
| Stage 5 (Canva 仕上げ) | なし | あり |
| 用途 | 素早く 1 枚だけ確認 | 修正 → 品質保証 → 完成まで自動化 |

`--iterate-from` で指定した起点画像は Stage 3 の Gemini 参照先頭に挿入される。
revision block はパイプラインが Stage 1 で生成した高品質なキャラクタープロンプトの先頭に差し込まれる。
出力先サブフォルダに `_iter1` / `_iter2` ... サフィックスが付く点は単体と同じ。

### 使い分け指針

- **パイプライン**: Stage 4/5 まで一気に完成させたい場合。品質保証も兼ねてほしい場合。
- **単体 Gemini**: 修正内容だけ素早く確認したい場合。`iter` チェーンを回して比較したい場合。

---

## 8. バッチ実行との関係

`src.batch_generate` には **意図的に `--iterate-from` を実装していない**。
i2i は「直前の結果を見ながら 1 件ずつ調整する」用途のため、複数キャラ × 形態を機械的に回すバッチとは目的が異なる。

複数キャラの初稿バッチを `batch_generate` で回し → 気になった結果だけ単発 `--iterate-from` で詰める、というワークフローを推奨。

---

## 9. トラブルシュート

| 症状                                   | 対処                                                                                                                                                 |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `[ERROR] --iterate-from の解決に失敗`  | パスが存在するか、画像拡張子が `.png/.jpg/.jpeg/.webp` のどれかを確認                                                                                |
| 改稿後の画像が前回とまったく別物になる | プロバイダが i2i を効かせていない可能性。`gpt-image-1` 利用中か、Gemini 側で参照画像が空でないかを `run_meta.json` の `reference_local_paths` で確認 |
| 修正指示が反映されない                 | `--revisions` の `;` 区切りが正しく分割されているか `prompt.txt` 先頭で確認。複数行 here-string は PowerShell 構文に注意                             |
| `iter` ラベルが毎回 `iter1` のまま     | 起点ファイル名・親ディレクトリ名のどちらにも `iterN` パターンが無い。生成済みフォルダ名を直接渡す (例: `output/.../..._num057_iter1`)                |
