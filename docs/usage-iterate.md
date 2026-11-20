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
- 値が **パイプラインの実行フォルダー**（`pipeline_summary.json` がある）なら、記録にある完成画像（`stage5_paths.all`）の先頭を起点にする。
- 値が **実行フォルダー名だけ**（例: `20261120_150049_pipeline_corefolder_num57`）なら、出力フォルダーの `{YYYYMMDD}/` から探す。手元に無く、`OUTPUT_SINK` が `local` 以外なら、GCS の `<GCS_PREFIX>/runs/<実行フォルダー名>/` から記録・完成画像・Stage 1 の土台を戻す（コネクタのサーバーが止まって出力フォルダーが消えたあとも、改稿の起点にできる）。
- 値が **それ以外のディレクトリ** なら配下の `num*.{png,jpg,jpeg,webp}` を mtime 降順で 1 件選ぶ。
  - 見つからない場合は `*.{png,jpg,jpeg,webp}` まで広げてフォールバック。
  - それでも 0 件なら `FileNotFoundError` で異常終了する。
- 値が **GCS URL** (`gs://` または `https://storage.googleapis.com/...`) なら
  一時ファイルに自動ダウンロードして起点として採用する。
  - `gs://` スキーム → `google-cloud-storage` ライブラリで取得
  - `https://` 署名 URL → `urllib.request` で取得
  - 受け付けるのは、`GCS_BUCKET` の `GCS_PREFIX`（既定 `numbertales`）の下の画像だけ。ほかのバケットやほかの接頭辞の URL は起点にしない（`GCS_BUCKET` が未設定なら、リモートの画像は起点にできない）
  - 30 秒で打ち切り、10MB を超える画像は受け付けない
  - MCP スキルの `numbertales_get_run_logs` が返す `intermediate` URL をそのまま渡せる。
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
python -m src.gemini.generate --badge 57 --form corefolder `
  --iterate-from "output/20260609/20260609_15/20260609_150049_gemini_corefolder_num057" `
  --revisions "尻尾は元のまま; 表情だけ笑顔にして"
```

### OpenAI (gpt-image-1) で改稿

```powershell
# 画像ファイル直指定でもOK
python -m src.openai.generate --badge 57 --form corefolder --mode dalle `
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
- ただし左右の向き・非対称要素の配置 (尻尾の束構成・マーキング位置・髪の分け目など) は、起点画像ではなく後続の公式 DB 参照画像を正とします。起点画像が原典と左右反転している場合は、原典の向きに合わせて修正してください。
- 修正: 尻尾は元のまま
- 修正: 表情だけ笑顔にして
```

> 「左右の向きは原典を正とする」の行は 2026-07-15 に恒常ルールとして追加された
> （i2i 起点画像由来の左右反転対策）。あわせて Stage 4 の違反分析にも、
> 公式 DB 参照画像 (Stage 1 `ref_locals` の先頭 1 枚) を 2 枚目として添付し、
> 左右反転を `violations`（`左右反転: <要素>` 形式）として検出・修正させる仕組みが入っている。

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
python -m src.pipeline.image_pipeline --badge 57 --form corefolder `
    --iterate-from "output/20260616/.../20260616_150049_gemini_corefolder_num057" `
    --revisions "尻尾は元のまま; 表情だけ笑顔にして" `
    --skip-canva

# Canva 仕上げも含めてフル実行
python -m src.pipeline.image_pipeline --badge 57 --form corefolder `
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

## 8. 作風LoRA参照画像を起点にする（外部参照画像ワークフロー）

`--iterate-from` は「前回 run の画像」だけでなく、**パイプライン外で生成した画像ファイル**も起点にできる
（`resolve_iterate_source()` はファイル直指定を無条件で受け付ける。`run_meta.json` への依存はない）。

これを利用して、`NumberTales-GeneratorsAI` 側で学習したコアフォルダ作風LoRA
（Illustrious-XL v0.1 + `nt-corefolder-v1-000004.safetensors`）の出力を
**作風・シルエットの参照起点**として Stage 3 に流し込める。

### 参照画像の置き場所

- 正: [`_ideas/lora-refs/corefolder-v1/`](../_ideas/lora-refs/corefolder-v1/README.md)（出典対応表・ライセンス注意を含む）
- 新しい参照が必要な場合は、GCE VM `lora-l4-trial`（停止中・再利用可）でエポック4重みを使って生成し、
  同フォルダに README の出典表とセットで追加する。

### コマンド例

```powershell
# LoRA出力を起点に 5 ステージ全体を回す（i2i モード）
python -m src.pipeline.image_pipeline --badge 57 --form corefolder `
    --iterate-from "_ideas/lora-refs/corefolder-v1/im_20260714132141_000_478163327.png" `
    --revisions "扇状に分離した尻尾のシルエットと太い主線・フラットカラーの作風を維持; 番号マーキングは57に" `
    --skip-canva

# シーン指定と組み合わせる場合
python -m src.pipeline.image_pipeline --badge 57 --form corefolder `
    --scene "図書館で本を読んでいるシーン" `
    --iterate-from "_ideas/lora-refs/corefolder-v1/im_20260714132149_000_107420369.png" `
    --revisions "作風（フラットカラー・太い主線）は参照画像に合わせる" `
    --skip-canva
```

### 通常 i2i との違い・注意

| 項目 | 通常 i2i（前回 run 起点） | LoRA参照起点 |
|---|---|---|
| 起点画像のキャラ正確性 | Stage 4 通過済みで高い | **保証なし**（作風LoRAは形態の雰囲気のみ） |
| `--revisions` の書き方 | 変えたい部分を指示 | **維持したい作風要素**を明示する |
| 不変特徴の担保 | Stage 2 + Stage 4 | 同じく Stage 2 + Stage 4 が必須（**`--skip-canva` はよいが Stage 4 はスキップしない**） |

- **配色の引きずりに注意**: カラーの LoRA サンプルを起点にすると、生成結果の配色がサンプル側に
  引きずられる（2026-07-15 初回運用で確認）。作風だけ引き継ぎたい場合は
  `_ideas/lora-refs/corefolder-v1/grayscale/` の**グレースケール版**を起点にし、
  revisions で「引き継ぐ要素（線・塗り・シルエット）」と「引き継がない要素（配色は DB 定義に従う）」を
  明示的に分離する。`--scene` も必ず指定する（未指定だと revisions がシーン扱いされる）。
- 参照画像は Web用縮小データ学習の v1 LoRA 出力のため、ディテールは Gemini 側の仕上げに任せる前提。
- ライセンス: 参照画像・LoRA重みの公開時は Fair AI Public License 1.0-SD を再確認（非商用の創作補助利用は問題なし）。

---

## 9. バッチ実行との関係

`src.batch_generate` には **意図的に `--iterate-from` を実装していない**。
i2i は「直前の結果を見ながら 1 件ずつ調整する」用途のため、複数キャラ × 形態を機械的に回すバッチとは目的が異なる。

複数キャラの初稿バッチを `batch_generate` で回し → 気になった結果だけ単発 `--iterate-from` で詰める、というワークフローを推奨。

---

## 10. トラブルシュート

| 症状                                   | 対処                                                                                                                                                 |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `[ERROR] --iterate-from の解決に失敗`  | パスが存在するか、画像拡張子が `.png/.jpg/.jpeg/.webp` のどれかを確認                                                                                |
| 改稿後の画像が前回とまったく別物になる | プロバイダが i2i を効かせていない可能性。`gpt-image-1` 利用中か、Gemini 側で参照画像が空でないかを `run_meta.json` の `reference_local_paths` で確認 |
| 修正指示が反映されない                 | `--revisions` の `;` 区切りが正しく分割されているか `prompt.txt` 先頭で確認。複数行 here-string は PowerShell 構文に注意                             |
| `iter` ラベルが毎回 `iter1` のまま     | 起点ファイル名・親ディレクトリ名のどちらにも `iterN` パターンが無い。生成済みフォルダ名を直接渡す (例: `output/.../..._num057_iter1`)                |

---

## 11. 入力画像・事前確認・軽い加筆（パイプライン）

`src.pipeline.image_pipeline` とコネクタ（`numbertales_*`）は、文字の指示に加えて画像を受け取れる。対象は単体（`--badge`）、合同（`--nums`）、改稿（`--iterate-from`）。`--natural` / `--story` は対象外。

### 入力画像（`--images`、コネクタの `images`）

役割ごとに、枚数と渡すステージが決まっている（実装: `src/pipeline/input_images.py`）。

| 役割 | 意味 | 枚数 | Stage 3 ラフ | Stage 4 検査 | Stage 5 合成 |
| --- | --- | --- | --- | --- | --- |
| `base` | 加筆の起点。`--iterate-from` より優先する | 1 | ○（先頭） | × | ○ |
| `markup` | 起点に赤で描き込んだ赤入れ。起点（`base` か `--iterate-from`）が必須 | 1 | ○ | ○ | × |
| `composition` | 構図参考。ポーズ・配置・画角だけを借りる。グレースケールにして渡す | 1 | ○ | × | × |
| `reference` | 生成画像と関係のない参考。`note`（何の参考にするか）が必須 | 3 | ○ | × | ○ |

- 添付の順は、起点 → 赤入れ → 構図参考 → 公式の参照画像 → 参考画像。画像ごとに役割のラベルを付け、プロンプトの先頭に `[入力画像の扱い]` を添える。キャラクターの外見は、公式の参照画像と設定資料が正しいものとして扱う。
- 合同生成では、キャラクターごとのラフと検査には渡さず、全員を 1 枚にまとめる Stage 5 でだけ使う。赤入れだけを渡した場合は、改稿の起点を加筆の起点として合成に添える。
- 赤入れは、起点の絵にそのまま描き込んだ画像を渡す。縦横比が起点と 2% 以上違うと受け付けない。Stage 4 は、指示した場所が直っていない場合と、赤い印や指示の文字が絵に残っている場合を `composition_issues` に数える。`--revisions` は任意で、あれば両方使う。
- 起点があって場面も修正指示も無いとき（赤入れだけ、など）は、ランダムな場面を作らず、起点の場面を保つ。
- 1 枚 10MB まで、PNG・JPEG・WebP（拡張子ではなく中身で判定）。`provenance`（出所）は毎回必須で、受け付けるのは `own_generated`（このパイプラインの生成結果）・`own_work`（依頼者自身の作品）・`own_photo`（依頼者自身が撮った写真）だけ。第三者の素材は渡せない。
- 置き場: CLI の `path` は、出力フォルダー（`output/`）かリポジトリ直下の `references/`（Git の追跡対象外）の中のファイル。コネクタの `object_key` は、`numbertales_create_upload_slot` で上げた、このサーバーの置き場の画像。base64、Drive のファイル ID、任意の URL は受け付けない。
- 検証は課金の前に行う。通らなければ `status: failed` で止まり、理由が `errors` に入る。通った画像は実行フォルダーの `inputs/` に書き出し、`pipeline_summary.json` の `input_images` に役割・出所・大きさ・SHA-256・渡したステージを残す。

```powershell
# 赤入れで加筆する（--revisions は任意）
python -m src.pipeline.image_pipeline --badge 57 --form corefolder --skip-canva `
    --iterate-from "output/20261120/20261120_150049_pipeline_corefolder_num57" `
    --images '[{"role": "markup", "path": "references/57_markup.png", "provenance": "own_work"}]'

# 構図参考と参考画像を添えて新しく描く（JSON を書いたファイルも渡せる）
python -m src.pipeline.image_pipeline --badge 57 --form corefolder --scene "窓辺で振り返る" --images references/images.json
```

### 事前確認（`--dry-run`、コネクタの `dry_run`）

生成せずに、プロンプトの土台、選べる状態と衣装の名前、公式の参照画像、役割の付いた入力画像の一覧を JSON で返す。課金のある API は呼ばず、出力フォルダーにも何も書かない（入力画像は検証のために読む）。

- Stage 1 は本番で LLM がプロンプトを加工するので、返すのは加工前の土台（`base_prompt`）。場面が空のときは、本番でランダムに決まる。
- 権利のゲートが拒否するキャラクター、選べない衣装、検証に通らない入力画像は、ここでエラーになる。
- 課金を伴う本番の前に実行し、結果を依頼者に示して承認を得る。

```powershell
python -m src.pipeline.image_pipeline --badge 35 --form humanoid --costume miko --dry-run
```

### 軽い加筆（`--quick`、コネクタの `numbertales_iterate` の `quick`）

起点（`--iterate-from` か、役割 `base` の画像）の絵を 1 回だけ編集し、完成画像 1 枚を新しい実行フォルダー（`…_pipeline_{form}_num{N}_iterN/`）に保存する。単体だけ。

- 残すもの: 権利のゲート、状態と衣装の指定、プロンプト。起点が以前のパイプライン実行の中の画像なら、その `stage1_prompt/prompt_base_gemini.txt` を使い回す。無ければ土台を組み直す。
- 省くもの: Stage 1 の LLM 加工、Stage 2 の観察、Stage 4 の検査、Canva。
- 入力画像は、役割のラベルを付けて、この 1 回の編集にすべて渡す。

```powershell
python -m src.pipeline.image_pipeline --badge 57 --form corefolder --quick `
    --iterate-from "output/20261120/20261120_150049_pipeline_corefolder_num57/stage5_final/synth/…/num057_corefolder_01.png" `
    --revisions "表情だけ笑顔にして"
```
