# usage-generation.md — 基本生成コマンドの使い方

`src.gemini.generate` / `src.openai.generate` / `src.batch_generate` の使い方をまとめたページ。
i2i (前回画像をベースに改稿) は [`usage-iterate.md`](usage-iterate.md) を参照。

> 関連: [`docs/README.md`](README.md) / [`AGENTS.md`](../AGENTS.md) / [`output-and-logs.md`](output-and-logs.md)

---

## 1. 共通フラグ一覧

3 スクリプト (`gemini` / `openai dalle` / `batch_generate`) 共通で使えるフラグ。

| フラグ          | 必須       | 型 / 既定値                                     | 役割                                                                   |
| --------------- | ---------- | ----------------------------------------------- | ---------------------------------------------------------------------- |
| `--num`         | ○ (single) | int                                             | キャラクター番号 (例: `57`)。`batch_generate` では `--nums "15,22,57"` |
| `--form`        | ―          | `corefolder` / `humanoid` (default: corefolder) | 描画する形態                                                           |
| `--work`        | ―          | `#Works_NumberTales`                            | 作品キー                                                               |
| `--out`         | ―          | None                                            | 出力ベース。省略時は env `OUTPUT_BASE_DIR` → `output`                  |
| `--scene`       | ―          | `""`                                            | シーン/ポーズ説明 (プロンプト末尾 `[シーン・追加要望]` に追加)         |
| `--style`       | ―          | `""`                                            | 作風ヒント (例: `"watercolor"`, `"pixel art"`)                         |
| `--composition` | ―          | `""`                                            | 構図ヒント (例: `"bust shot"`, `"low angle, full body"`)               |
| `--background`  | ―          | `""`                                            | 背景ヒント (例: `"white background"`, `"sunset library"`)              |

i2i 用フラグ (`--iterate-from` / `--revisions`) は [`usage-iterate.md`](usage-iterate.md) を参照。
`batch_generate` には **意図的に追加していない** (i2i は単発実行専用)。

---

## 2. Gemini (Imagen 3 / 4) — `src.gemini.generate`

### コマンド

```powershell
python -m src.gemini.generate --num 57 --form corefolder [オプション]
```

### Gemini 専用フラグ

| フラグ    | 既定値 | 役割            |
| --------- | ------ | --------------- |
| `--count` | 1      | 生成枚数 (1〜4) |

### 動作モード

1. **参照画像あり** (`ai_hints.*.reference_images` または DB レコード `images` が解決できる場合)
   → `gemini-3.1-flash-image` モデルで `generate_content` + `Part.from_bytes / from_uri` を使う i2i 風生成。
2. **参照画像なし**
   → `imagen-3.0-generate-001` (env で上書き可) の `generate_images` を使う純テキスト→画像生成。

参照モデルは `GEMINI_REFERENCE_MODEL` (env) で上書き可能。

### 使用例

```powershell
# シンプルな単発生成 (corefolder)
python -m src.gemini.generate --num 57

# humanoid を 2 枚生成
python -m src.gemini.generate --num 57 --form humanoid --count 2

# シーン+作風+構図+背景を全部指定
python -m src.gemini.generate --num 22 --form humanoid `
  --scene "天文台で星図を見ているシーン" `
  --style "soft watercolor with starry highlights" `
  --composition "three quarter view, waist up" `
  --background "domed observatory at night"

# 出力先を一時的に変える
python -m src.gemini.generate --num 49 --out "C:\tmp\gen-test"
```

---

## 3. OpenAI — `src.openai.generate`

OpenAI スクリプトは **2 モード** ある。`--mode` で切替 (デフォルト `dalle`)。

### 3-1. `--mode dalle` (画像生成)

```powershell
python -m src.openai.generate --num 57 --form corefolder [オプション]
```

#### OpenAI dalle 専用フラグ

| フラグ   | 既定値      | 役割                                             |
| -------- | ----------- | ------------------------------------------------ |
| `--size` | `1024x1024` | `1024x1024` / `1792x1024` / `1024x1792` から選択 |
| `--mode` | `dalle`     | `dalle` or `prompt-assist`                       |

#### モデル選択ロジック

- `.env` の `DALLE_MODEL` で指定 (`dall-e-3` or `gpt-image-1` 推奨)。
- モデルが `gpt-image-` 系で **ローカル参照画像が 1 枚以上ある** 場合、自動的に `images.edit` 経由 (i2i) で投入される。
  - 起点画像が無ければ `images.generate` (純テキスト→画像) にフォールバック。
- `OPENAI_IMAGE_QUALITY`:
  - `dall-e-3` は `standard` / `hd`。
  - `gpt-image-1` は `medium` / `high` を使う (`standard` 指定時は `medium` に自動補正)。

#### 使用例

```powershell
# 基本
python -m src.openai.generate --num 57 --form corefolder

# サイズ変更 + シーン指定
python -m src.openai.generate --num 73 --form humanoid `
  --size 1024x1792 --scene "工房の作業机に向かう様子"
```

### 3-2. `--mode prompt-assist` (GPT-4o プロンプト改善提案)

API キーで GPT-4o (env `GPT_MODEL`) を呼び、現状のプロンプトに対する改善案を **テキストで** 返してもらうモード。
画像は生成しない。

```powershell
python -m src.openai.generate --num 57 --mode prompt-assist `
  --scene "図書館で本を読んでいるシーン"
```

出力先は `output/.../{ts}_openai_{form}_num{NNN}_prompt-assist/` で、
通常の `prompt.txt` / `run_meta.json` / `notes.md` に加えて `gpt_response.md` も保存される。

---

## 4. バッチ実行 — `src.batch_generate`

複数キャラクター × 形態 × プロバイダを順番に流すラッパー。

### コマンド

```powershell
python -m src.batch_generate --nums 15,22,49,57 --forms both --provider both [オプション]
```

### バッチ専用フラグ

| フラグ               | 既定値      | 役割                                                                         |
| -------------------- | ----------- | ---------------------------------------------------------------------------- |
| `--nums`             | (必須)      | カンマ区切りキャラ番号 (例: `15,22,49,57`)                                   |
| `--forms`            | `both`      | `corefolder` / `humanoid` / `both`                                           |
| `--provider`         | `gemini`    | `gemini` / `openai` / `both`                                                 |
| `--count`            | 1           | Gemini のみに有効                                                            |
| `--size`             | `1024x1024` | OpenAI のみに有効                                                            |
| `--sleep`            | `0.0`       | 各実行間に挟む秒数 (rate-limit 回避用)                                       |
| `--no-skip-no-hints` | OFF         | デフォルトでは ai_hints が無い形態は自動 skip。これを付けると強制実行        |
| `--dry-run`          | OFF         | 実 API を呼ばずに RUN/SKIP 予定と capability だけ出力。 **本番前に必ず実行** |

`--scene` / `--style` / `--composition` / `--background` も使え、 **全実行に同じ値が共通で差し込まれる**。

### 推奨ワークフロー

```powershell
# 1. 必ず dry-run で RUN/SKIP 件数と各キャラの capability を確認
python -m src.batch_generate --nums 15,22,49,57 --forms both --provider both --dry-run

# 2. 問題なければ本実行 (課金発生)
python -m src.batch_generate --nums 15,22,49,57 --forms both --provider both

# 3. rate-limit が心配なら間隔をあける
python -m src.batch_generate --nums 15,22,49,57 --forms both --provider both --sleep 1.5
```

### 出力

実行ごとに通常通り `output/{YYYYMMDD}/{YYYYMMDD_HH}/{ts}_{provider}_{form}_num{NNN}/` が切られる。
バッチ自体に専用のサマリ JSON は出ないが、最後にコンソールへ `BATCH SUMMARY` (total / ok / skipped / failed の件数) が表示される。

---

## 5. プロンプトの内部構造

`src.utils.dataset.build_dalle_prompt` / `build_gemini_prompt` が組み立てる本文の主要ブロック (上から順)。

| 順序 | ブロック名                                            | 内容                                                                                                          | 出典フィールド                                                                 |
| ---- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 1    | 導入文                                                | 「このキャラクターを描いてください」「同じキャラクターを別ポーズで〜」                                        | (固定文)                                                                       |
| 1.5  | `[修正指示]` (i2i 時のみ)                             | iterate-from の修正項目を最優先で適用させる。詳細は [`usage-iterate.md`](usage-iterate.md)                    | `--revisions`                                                                  |
| 2    | `[参照画像]` / `[参照画像URL]` / `[参照画像ローカル]` | URL とローカル添付の存在告知                                                                                  | `ai_hints.*.reference_images`, レコード `images`                               |
| 3    | `[素体特徴]`                                          | 不変特徴 (耳・尻尾・髪色・瞳色)                                                                               | `ai_hints.common.immutable_traits` / `identity_tags`                           |
| 4    | `[今回の姿]`                                          | 現在形態の自然文記述                                                                                          | `ai_hints.forms.{form}.natural_language_description`                           |
| 5    | **`[番号印字仕様 (必須・最優先)]`**                   | キャラ番号の刻印位置・字形ルール (例: 「57 の文字そのものを刻印」「corefolder は表面 / humanoid は左胸寄り」) | identity_tags / immutable_traits / outfit_features / silhouette_notes から抽出 |
| 6    | `[形態固定ルール]`                                    | 形態固有の immutable_constraints / 形態共通データセット (`required_shape_keywords[]`)                         | `Works_NumberTales.json` + `ai_hints.forms.{form}.immutable_constraints`       |
| 7    | `[現在形態の重点要素]`                                | `silhouette_notes` の body_description / attached_items を 2 行に分けて提示                                   | `ai_hints.forms.{form}.silhouette_notes`                                       |
| 8    | `[禁止語]` / negative                                 | 形態共通データセットの `disallow_cross_form_keywords[]` + `negative_keywords`                                 | `Works_NumberTales.json` + `ai_hints.forms.{form}.negative_keywords`           |
| 6.5  | `[形態共通データセット]`                              | 形態定義・シルエット要約・共通装備 + **DB原典/識別モチーフ(en)** (両形態) / **DB原典/尾の構造(en)** (humanoid 限定) | `_ideas/form_common_datasets/{Work}.json` + `db_record.IdentityMotif.Motif_EN` / `db_record.TailsUnit_EN` |
| 9    | `[シーン・追加要望]`                                  | `--scene` / `--style` / `--composition` / `--background` の指定値                                             | CLI フラグ                                                                     |

> **重要**: 番号印字ブロック (5) と禁止語ブロック (8) は2026-06-09に再強化済み。詳細は [`AGENTS.md`](../AGENTS.md) の `output レイアウト規約` セクションと、リポジトリメモリの A7 ノートを参照。

> **2026-06-13 更新**: `[形態共通データセット]` (ブロック 6.5) に `_creations-db` 英語フィールド拡張対応の DB原典補足行を追加。`IdentityMotif.Motif_EN`（形態別英語モチーフタグ、89キャラ対応）は両形態で注入。humanoid 形態には `TailsUnit_EN`（英語表記の尾構造、32キャラ対応）を優先使用し、未設定時は日本語版にフォールバック。corefolder 形態の Motif_EN には humanoid 衣装フィルタを通してから注入する。

---

## 6. 失敗時の挙動

- API エラーや認証失敗で生成が落ちても、 **`prompt.txt` と `run_meta.json` は必ず残る**。
- `run_meta.json` の `status: "failed"` + `errors[]` で原因が辿れる。
- 同じプロンプトで成功した過去 run と diff を取ると、何が悪化したか分かりやすい。

---

## 7. レビュー → 改善ループ

1. 生成完了後、 [`output-and-logs.md`](output-and-logs.md) のテンプレに従って `notes.md` を埋める (`観察` / `気になった点` / `改善案`)。
2. 必要なら `--iterate-from` で当該 run を起点に改稿 ([`usage-iterate.md`](usage-iterate.md))。
3. 構造的な悪化を発見したら、形態共通データセット ([`tools.md`](tools.md#形態共通データセット works_jsondisallow--required-shape の編集)) や プロンプト builder 側の調整を検討。
