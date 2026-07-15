# usage-generation.md — 基本生成コマンドの使い方

`src.gemini.generate` / `src.openai.generate` / `src.batch_generate` および
マルチ LLM パイプライン (`src.pipeline.*`) の使い方をまとめたページ。
i2i (前回画像をベースに改稿) は [`usage-iterate.md`](usage-iterate.md) を参照。
MCP (Adobe / Canva) との連携は [`usage-mcp-canva-adobe.md`](usage-mcp-canva-adobe.md) を参照。

> 関連: [`docs/README.md`](README.md) / [`AGENTS.md`](../AGENTS.md) / [`output-and-logs.md`](output-and-logs.md)

---

## 0. マルチ LLM パイプライン (`src.pipeline`) — 推奨

複数のプロバイダ・LLM の得意分野を活かした **5 ステージ**画像生成ワークフロー。

### 0-1. 画像生成パイプライン

| ステージ | 役割 | 使用モデル / ツール |
|---|---|---|
| Stage 1 | コマンド解析 + ベースプロンプト生成 (シーン未指定時はキャラクターに合ったシーンを自動生成) | OpenAI GPT-4o + Gemini Flash |
| Stage 2 | キャラクター選定 + 創作 DB から原典画像・特徴を取得 | manifest.jsonl + 参照画像索引 |
| Stage 3 | ラフ生成 (単体: **5 案** / 合同: キャラ別 **3 枚×N 人** + **全体構図ラフ 1 枚**) | Adobe 非 Firefly (構図ガイド) + Gemini Imagen |
| Stage 4 | 違反特徴の除去 + 構図修正 (単体・合同ともキャラ別に実行) | OpenAI Vision (違反分析) + Gemini i2i (修正適用) |
| Stage 5 | 完成画像 **3 枚**生成 → Canva 仕上げ | Gemini (マルチ参照合成) + Canva Connect API |

```bash
# 基本実行（キャラクター番号直接指定・シーンは自動生成）
python -m src.pipeline.image_pipeline --num 57 --form corefolder

# シーン・作風を明示指定
python -m src.pipeline.image_pipeline --num 57 --form corefolder \
    --scene "図書館で本を読んでいるシーン" --style "watercolor"

# ★ 自然文でリクエスト（LLM がキャラクター・シーン等を抽出）
python -m src.pipeline.image_pipeline \
    --natural "コアフォルダ姿の25(フィズ)がチョコレートを咥えている絵を生成してほしい"

# ★ 短編ストーリーファイルから指定
python -m src.pipeline.image_pipeline --story "_ideas/my_scene.txt"

# ★ 複数キャラクターを 1 枚に合同生成 (マルチキャラクターシーン)
# --nums に 2 件以上指定すると合同パイプラインが走る。
# Stage 3-4 をキャラ別に実行し、Stage 5 で全員を 1 枚に合成する。
python -m src.pipeline.image_pipeline --nums 25,52 --form corefolder \
    --scene "研究所のラボで並んでいるシーン" --skip-canva

# Stage 5 Canva フィニッシングをスキップ（CANVA_ACCESS_TOKEN 不要）
python -m src.pipeline.image_pipeline --num 57 --form corefolder --skip-canva
```

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--num` | (いずれか必須) | キャラクター番号 (単体生成) |
| `--nums` | — | 複数キャラクター番号 カンマ区切り (例: `25,52`) — **2 件以上で全員を 1 枚に合同生成** |
| `--natural TEXT` | — | 自然文からパラメータを LLM 抽出 |
| `--story FILE` | — | テキストファイルから LLM 抽出 |
| `--form` | corefolder | 形態 (`--natural` 時は LLM 判定を優先) |
| `--scene` | `""` | シーン説明。**省略時は Stage 1 でキャラクターに合ったシーンを自動生成** |
| `--style` / `--composition` / `--background` | `""` | 作風・構図・背景ヒント |
| `--skip-canva` | false | Stage 5 の Canva をスキップ |
| `--costume TEXT` | `""` | 衣装差分の説明 (例: `"黒いワンピース姿の差分"`)。指定時は Stage 1 でデフォルト衣装を上書きしてプロンプト生成する。不変特徴（耳・尻尾・髪色・瞳色）は維持される |
| `--correction-mode` | `t2i` | Stage 4 重度違反時の対処モード。`t2i`: Stage 4 内で T2I 再生成 / `stage3`: Stage 3 に差し戻してラフを再生成 |
| `--iterate-from PATH` | None | 前回生成画像を起点に Stage 3 を **i2i モード**で実行。Stage 4/5 は通常通り走る。詳細は [`usage-iterate.md`](usage-iterate.md) |
| `--revisions TEXT` | None | 修正指示（`; `/改行区切り）。`--iterate-from` と組み合わせて使用 |
| `--prefer-gemini-parse` | false | `--natural` / `--story` のパース時に Gemini を OpenAI より優先 |
| `--field-override FIELD=VALUE` | None | `RaceType` 等の曖昧フィールド（複数候補から1つ選ぶ必要があるもの）を明示指定。繰り返し指定可能（例: `--field-override RaceType=最終的な設計目標 --field-override Height_cm=190`）。未指定時はシーン文脈から LLM が自動判定する |
| `--non-interactive` | false | 実ターミナル (TTY) 実行時でも曖昧フィールドの対話確認プロンプトを出さない |

**出力構成 (単体キャラ `--num`):**
```
{OUTPUT_BASE_DIR}/{YYYYMMDD}/{ts}_pipeline_{form}_num{NNN}/      # 1 実行 = 1 フォルダ
  stage1_prompt/     — 生成済みプロンプト (openai/gemini/base テキスト) + stage1_meta.json
  stage2_db/         — DB サマリー + キャラクタースペック (violation_features 等)
  stage3_rough/      — Gemini Imagen ラフ 5 案
                       └── regen/  — Stage 3 差し戻し再生成分 (--correction-mode stage3 時のみ)
  stage4_correct/    — 違反分析ログ (analysis_log.json) + 修正済み画像
  stage5_final/      — Canva 仕上げ完成画像 3 枚
                       └── synth/  — Gemini マルチ参照合成の中間出力 (Canva 前)
  pipeline_summary.json
```

**出力構成 (合同キャラ `--nums`):**
```
{OUTPUT_BASE_DIR}/{YYYYMMDD}/{ts}_pipeline_{form}_nums{AAA}_{BBB}/
  stage1_prompt/char_{AAA}/   — キャラ別生成プロンプト
  stage1_prompt/char_{BBB}/
  char_{AAA}/
    stage3_rough/             — ラフ 3 枚/キャラ
    stage4_correct/           — 違反修正済み画像 (キャラ別)
  char_{BBB}/
    stage3_rough/
    stage4_correct/
  stage3_comp_rough/          — 全キャラ単体ラフをもとに全員が揃う構図ラフ (1 枚)
                                 Stage 5 最終合成の確認・i2i 起点に活用できる
  stage5_final/
    synth/                    — 全キャラ画像を参照して 1 枚に合成 (3 案)
    canva/
  pipeline_summary.json
```

詳細な構造説明は [`output-and-logs.md`](output-and-logs.md) のセクション 6 を参照。

#### 自然文パーサー単体実行

```bash
# パラメータ抽出結果のみ確認（画像生成しない）
python -m src.pipeline.natural_parser "コアフォルダ姿の25(フィズ)がチョコレートを咥えている絵"
# → [{"num": 25, "form": "corefolder", "scene": "チョコレートを咥えているシーン", ...}]
```

#### 作風データセットビルダー

全キャラクターのコアフォルダイラストを Gemini Vision で分析し、
原典作風の共通傾向を `_ideas/form_common_datasets/Works_NumberTales.json` に保存する。
このデータは生成プロンプトに自動注入されて再現性を高める。

```bash
# まず dry-run で分析対象を確認
python scripts/build_style_dataset.py --dry-run

# 実行（最大 30 キャラクターを分析、約 45 秒〜）
python scripts/build_style_dataset.py

# 分析数を絞る（API コスト節約）
python scripts/build_style_dataset.py --max-chars 10
```

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--form` | corefolder | 分析形態 |
| `--max-chars` | 30 | 最大分析キャラクター数 |
| `--output` | `_ideas/form_common_datasets/Works_NumberTales.json` | 出力先 |
| `--dry-run` | false | 対象一覧のみ表示 (API 未呼び出し) |
| `--sleep` | 1.5 | キャラクター間の待機秒 |

### 0-2. テキスト生成パイプライン

GPT-4o でプライマリ生成 → Gemini でクロスレビュー・改善。

```bash
# シーン文章 (創作向け)
python -m src.pipeline.text_pipeline --num 57 --mode scene \
    --prompt "図書館で先輩と本を読んでいるシーン"

# キャラクター紹介・外見描写 (Wiki/DB 向け)
python -m src.pipeline.text_pipeline --num 57 --mode description

# イラストキャプション (100文字以内)
python -m src.pipeline.text_pipeline --num 57 --mode caption \
    --prompt "夕暮れの研究所テラスでたたずむシーン"
```

必要な環境変数 (`.env`):

| 変数 | 用途 |
|---|---|
| `GEMINI_API_KEY` | Gemini Imagen + Gemini テキスト + 自然文パーサー + シーン自動生成 (Stage 1) |
| `OPENAI_API_KEY` | GPT-4o (Stage 1 プロンプト加工・自然文パーサー・Stage 4 違反分析) |
| `FIREFLY_CLIENT_ID` / `FIREFLY_CLIENT_SECRET` | Adobe IMS 認証 (Lightroom/Photoshop API 共通、Stage 3 構図ガイド用) |
| `ADOBE_STORAGE_TYPE` | Adobe 非Firefly ストレージ: `local` (PIL fallback, デフォルト) / `dropbox` / `s3` |
| `CANVA_ACCESS_TOKEN` | Canva フィニッシング (Stage 5、`--skip-canva` で不要) |
| `GEMINI_TEXT_MODEL` | Gemini テキストモデル (デフォルト: `gemini-2.5-flash`) |
| `GPT_MODEL` | OpenAI テキストモデル (デフォルト: `gpt-4o`、Stage 1/4 で使用) |

> **Adobe 非 Firefly について**: `ADOBE_STORAGE_TYPE=local`（デフォルト）の場合、
> Lightroom/Photoshop API の代わりに Pillow でローカル処理する (Stage 3 構図ガイド)。
> クラウド API を有効にする場合は `ADOBE_STORAGE_TYPE=dropbox` 等を設定のうえ、
> `ADOBE_INPUT_URL_1` / `ADOBE_OUTPUT_URL_1` に presigned URL を指定する。

> **Stage 4 (違反分析) について**: `OPENAI_API_KEY` が未設定の場合は OpenAI Vision 分析をスキップし、
> ラフ画像を pass-through として Stage 5 に送る。設定することで
> 「コアフォルダ形態に腕が描かれている」等の違反を自動検出して Gemini i2i で修正できる。

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
   → `gemini-3.1-flash-image` モデルで `generate_content` + `Part.from_bytes` を使う i2i 風生成。
     参照 URL は実バイトを DL してから添付する (Gemini サーバーが任意 URL を直接 fetch できないため)。
2. **参照画像なし**
   → `imagen-4.0-generate-001` (env で上書き可。imagen-3.0 系は廃止) の `generate_images` を使う純テキスト→画像生成。

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

## 3.5 Adobe Firefly / Canva プロバイダ

ローカル CLI から API で動かす追加プロバイダ。Claude(Cowork) 経由の対話的連携は
[`usage-mcp-canva-adobe.md`](usage-mcp-canva-adobe.md) を参照 (2 ルートの使い分けはそちらに整理)。

### 3-5-1. Adobe 非 Firefly — `src.adobe.image_ops` (構図ガイド生成)

Firefly での text-to-image **ではなく**、Adobe Lightroom / Photoshop API で
DB 参照画像を加工して構図ガイドを作成するモジュール。
パイプライン Stage 3 から内部的に呼び出されるほか、単体実行も可能。

```bash
# 単体で構図ガイド確認
python -m src.adobe.image_ops --num 57 --form corefolder \
    --scene "図書館で本を読んでいるシーン" --background "図書館" --out output/test_guide
```

| env                     | 役割                                          |
| ----------------------- | --------------------------------------------- |
| `FIREFLY_CLIENT_ID`     | IMS 認証 Client ID (Lightroom/Photoshop 共通) |
| `FIREFLY_CLIENT_SECRET` | IMS 認証 Client Secret                        |
| `ADOBE_STORAGE_TYPE`    | `local` (PIL fallback) / `dropbox` / `s3`     |

出力は指定 `--out` 配下に `num{NNN}_{form}_composition_guide_NN.png`。

> **Firefly 単体生成スクリプト** (`src.adobe.generate`) は引き続き単独プロバイダとして使用可能。
> ただしパイプライン Stage 2 では使用しない（Adobe の役割を非 Firefly 構図ガイドに変更済み）。

```bash
# Firefly 単体 (パイプライン外で使う場合)
python -m src.adobe.generate --num 57 --form corefolder --count 1 --dry-run
```

### 3-5-2. Canva — `src.canva.generate` (デザイン化・書き出し)

**Canva Connect API にテキスト→画像生成は無い**ため、すでに生成済みの画像を入力に取り、
Canva へアップロード → デザイン作成 → PNG/JPG/PDF 書き出しする **後段ツール**。`--from-image` が必須。

```bash
# Gemini 出力を Canva デザイン化して書き出す
python -m src.canva.generate --num 57 --form corefolder \
    --from-image output/20260615/20260615_06/20260615_060000_gemini_corefolder_num057/num057_corefolder_01.png

# 予定確認だけ (課金ゼロ)
python -m src.canva.generate --num 57 --from-image <path> --dry-run
```

| env                  | 役割                                  |
| -------------------- | ------------------------------------- |
| `CANVA_ACCESS_TOKEN` | Canva Connect の user OAuth トークン  |
| `CANVA_EXPORT_FORMAT`| 書き出し形式 (`png`/`jpg`/`pdf`)      |

| Canva 専用フラグ | 役割                              |
| ---------------- | --------------------------------- |
| `--from-image`   | (必須) Canva に取り込む画像のパス |
| `--title`        | Canva デザインのタイトル          |

出力は `output/.../{ts}_canva_{form}_num{NNN}/num{NNN}_{form}_canva_NN.png`。

> Canva で「新規生成」したい場合は MCP ワークフロー ([`usage-mcp-canva-adobe.md`](usage-mcp-canva-adobe.md)) を使う。

### 3-5-3. SDXL + 作風LoRA — `src.sdxl.generate` (B案・GCE VM SSH バッチ)

Illustrious-XL v0.1 + コアフォルダ作風LoRA (`nt-corefolder-v1-000004.safetensors`, エポック4) で
ラフを生成するプロバイダ。推論は GCE VM `lora-l4-trial` 上で行い、gcloud ssh/scp で結果を回収する。
計画書: `_ideas/sdxl-provider-plan-v1.md`

```powershell
# dry-run (gcloud コマンド列の確認のみ・VM 操作なし・課金ゼロ)
python -m src.sdxl.generate --num 57 --form corefolder --count 2 --dry-run

# 本番 (VM 起動を伴う = スポットL4課金。事前に RUN 予定を共有すること)
python -m src.sdxl.generate --num 57 --form corefolder --count 3 `
    --scene-tags "reading a book, library"
```

| env | 役割 |
| --- | --- |
| `SDXL_GCP_PROJECT` | GCP プロジェクト (default: `claude-radiannkswg`) |
| `SDXL_VM_NAME` / `SDXL_VM_ZONE` | 推論 VM (default: `lora-l4-trial` / `asia-east1-b`) |
| `SDXL_REMOTE_WORKDIR` | VM 上の作業ディレクトリ (default: `/home/s-chi/sdxl-infer`) |
| `SDXL_REMOTE_BASE_MODEL` | (必須) VM 上の Illustrious-XL チェックポイント絶対パス |
| `SDXL_REMOTE_LORA` | (必須) VM 上の LoRA 重み絶対パス |
| `SDXL_LORA_SCALE` | LoRA 適用強度 (default: `0.8`) |
| `SDXL_REMOTE_PYTHON` | 推論に使う VM 上の python (default: `python3`)。diffusers/peft 入りの venv 絶対パスを推奨 (例: `/home/s-chi/sd-scripts/venv/bin/python`) |

| SDXL 専用フラグ | 役割 |
| --- | --- |
| `--scene-tags` | シーンのタグ列 (英語推奨。WD14 タグ体系) |
| `--seed` | 乱数シード固定 |
| `--keep-vm` | 生成後に VM を停止しない (連続実行用・課金継続注意) |
| `--dry-run` | gcloud コマンド表示のみ (課金ゼロ) |

- プロンプトは `src/sdxl/prompt_map.py` が「trigger word (`nt-corefolder`) + 既定タグ +
  DB 定義色タグ (ColorPalette → `yellow arms` 等へ自動変換) + シーンタグ」に変換する。
- 生成後は VM を**自動停止**する (失敗時は手動停止コマンドを警告表示)。
- v1 は `corefolder` 形態のみ (humanoid の作風LoRAは未学習)。
- VM 側前提スクリプト: `scripts/sdxl_vm/infer_sdxl_lora.py` (client が自動転送)。
- **VM 初回セットアップ (一度きり)**: 推論は diffusers + peft が必要。kohya 学習環境の venv
  (`/home/s-chi/sd-scripts/venv`) に torch/diffusers が同居しているので、これを
  `SDXL_REMOTE_PYTHON` に指定して流用する。venv に peft が無い場合は一度だけ
  `<venv>/bin/python -m pip install peft` を実行する (2026-07-15 に `peft 0.19.1` 導入済み)。
  システムの `python3` には diffusers が無いため、既定のままだと `ModuleNotFoundError` になる。

**パイプライン統合 (`--rough-provider`)**: `src.pipeline.image_pipeline` に
`--rough-provider {gemini|sdxl|both}` を追加済み (既定 `gemini`・完全後方互換)。
`both` (併走式) では Gemini ラフと SDXL ラフの両方が Stage 4 (違反修正) へ渡る。
合同生成 (`--nums`) は未対応 (gemini 固定)。

```powershell
# 併走式: Gemini + SDXL 両方のラフから Stage 4/5 を回す
python -m src.pipeline.image_pipeline --num 57 --form corefolder `
    --scene "図書館で本を読んでいるシーン" --rough-provider both --skip-canva
```

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
| `--provider`         | `gemini`    | `gemini` / `openai` / `adobe` / `canva` / `both` / `all` (both=gemini+openai, all=+adobe) |
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

実行ごとに通常通り `output/{YYYYMMDD}/{ts}_{provider}_{form}_num{NNN}/` が切られる。
バッチ自体に専用のサマリ JSON は出ないが、最後にコンソールへ `BATCH SUMMARY` (total / ok / skipped / failed の件数) が表示される。

---

## 5. プロンプトの内部構造

`src.utils.dataset.build_dalle_prompt` / `build_gemini_prompt` が組み立てる本文の主要ブロック (上から順)。

| 順序 | ブロック名                                            | 内容                                                                                                          | 出典フィールド                                                                 |
| ---- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 0    | **`[最優先ルール - 画像内テキスト禁止]`**             | 参照画像のテキスト・注釈・ラベルを画像内に再現しない。キャラ番号はバッジ造形としてのみ描く。英語/日本語で二重に明示 | (固定文、`build_gemini_prompt` 先頭 + `gemini/generate.py` 末尾サフィックスで二重適用) |
| 1    | 導入文                                                | 「このキャラクターを描いてください」「同じキャラクターを別ポーズで〜」                                        | (固定文)                                                                       |
| 1.5  | `[修正指示]` (i2i 時のみ)                             | iterate-from の修正項目を最優先で適用させる。詳細は [`usage-iterate.md`](usage-iterate.md)                    | `--revisions`                                                                  |
| 2    | `[参照画像]` / `[参照画像URL]` / `[参照画像ローカル]` | URL とローカル添付の存在告知 (humanoid 形態は尾構造参考画像 `images.tails_unit` も含む)                       | `ai_hints.*.reference_images`, レコード `images`（`concept`/`corefolder`/`humanoid`/`arts`/`design_alt`/`tails_unit`） |
| 3    | `[素体特徴]`                                          | 不変特徴 (耳・尻尾・髪色・瞳色)                                                                               | `ai_hints.common.immutable_traits` / `identity_tags`                           |
| 4    | `[今回の姿]`                                          | 現在形態の自然文記述                                                                                          | `ai_hints.forms.{form}.natural_language_description`                           |
| 5    | **`[番号印字仕様 (必須・最優先)]`**                   | キャラ番号の刻印位置・字形ルール (例: 「57 の文字そのものを刻印」「corefolder は表面 / humanoid は左胸寄り」) | identity_tags / immutable_traits / outfit_features / silhouette_notes から抽出 |
| 6    | `[形態固定ルール]`                                    | 形態固有の immutable_constraints / 形態共通データセット (`required_shape_keywords[]`)                         | `Works_NumberTales.json` + `ai_hints.forms.{form}.immutable_constraints`       |
| 6.8  | **`[配色仕様 (DB実測値・遵守すること)]`**             | 作者が設定画に描いたカラーチップ由来の HEX を Role (主色/補助色/差し色/副色) 別に列挙し、`AppliesTo` の適用部位を併記 (例: `- 主色 #E8F152 : arm, foot`)。参照画像と矛盾して見える場合は参照画像を優先させる | `db_record.ColorPalette` / `data.ColorPalette`（不在時は `ai_hints.common.palette_priority` へフォールバック） |
| 7    | `[現在形態の重点要素]`                                | `silhouette_notes` の body_description / attached_items を 2 行に分けて提示                                   | `ai_hints.forms.{form}.silhouette_notes`                                       |
| 8    | `[禁止語]` / negative                                 | 形態共通データセットの `disallow_cross_form_keywords[]` + `negative_keywords`                                 | `Works_NumberTales.json` + `ai_hints.forms.{form}.negative_keywords`           |
| 6.5  | `[形態共通データセット]`                              | 形態定義・シルエット要約・共通装備 + **DB原典/識別モチーフ(en)** (両形態) / **DB原典/尾の構造(en)・種別・身長** (humanoid 限定) | `_ideas/form_common_datasets/{Work}.json` + `db_record.AppearanceDetail`(`#Element_Motif`/`#Element_CostumeItem`、旧 `IdentityMotif.Motif_EN` 廃止済み) / `db_record.TailsUnit`（構造化） / `db_record.RaceType`・`Height_cm`（曖昧フィールド解決） |
| 9    | `[シーン・追加要望]`                                  | `--scene` / `--style` / `--composition` / `--background` の指定値                                             | CLI フラグ                                                                     |

> **重要**: 番号印字ブロック (5) と禁止語ブロック (8) は2026-06-09に再強化済み。詳細は [`AGENTS.md`](../AGENTS.md) の `output レイアウト規約` セクションを参照。

> **2026-06-13 更新**: `[形態共通データセット]` (ブロック 6.5) に `_creations-db` 英語フィールド拡張対応の DB原典補足行を追加。`IdentityMotif.Motif_EN`（形態別英語モチーフタグ、89キャラ対応）は両形態で注入。humanoid 形態には `TailsUnit_EN`（英語表記の尾構造、32キャラ対応）を優先使用し、未設定時は日本語版にフォールバック。corefolder 形態の Motif_EN には humanoid 衣装フィルタを通してから注入する。
> **2026-06-29 更新**: ブロック 6.5 の DB原典補足行に **AppearanceDetail フォールバック** を追加（src 側 `src/utils/dataset.py`）。`IdentityMotif.Motif_EN` 不在時は `db_record.AppearanceDetail` の `#Element_Motif` / `#Element_CostumeItem` エントリの `#DesignAttr_Overview.value_EN`（旧形式 `Value_EN` も可）から識別モチーフを収集してフォールバックする。humanoid 形態で `TailsUnit_EN` が空の場合は `#Element_TailsUnit` の Shape / Count / Branch 属性から英語の尾構造文字列を再構築してフォールバックする。既存フィールドが存在する間は従来動作を維持（非破壊）。AppearanceDetail の有無は ai-dataset 側 `has_appearance_detail` フラグで確認できる。
> **2026-07-10 更新**: DB 側で `TailsUnit_JP`/`TailsUnit_EN`（単純文字列）が廃止され、構造化フィールド `TailsUnit`（`$Def_TailsUnit[]`: `TailShapeType`/`Count`/`Branches[]`/`Note_JP`/`Note_EN`）へ全面移行（2026-07-07）。`src/utils/dataset.py` の `_extract_tails_unit_texts()` が `TailShapeType` の列挙値（`_TAIL_SHAPE_TYPE_LABELS`）と `Branches[].Laterality` から JP/EN 文字列を再構築する。優先順位: 旧 `TailsUnit_JP`/`TailsUnit_EN`（残っていれば）→ 新 `TailsUnit` 構造からの再構築 → 旧 `AppearanceDetail(#Element_TailsUnit)` フォールバック。
> **2026-07-10 追加更新（addon-ai-tag 側の TailsUnit 拡張フィールド追従）**: `TailsUnit` に `Segment`（節数。Scorpion/Nekomata(Special)/CaudalFin 等の型で使用）と `LayoutDirection`（`LayoutFrom`/`LayoutTo`、分岐配置の起点→終点。例: Periphery→Center）が追加されたのに追従し、`_describe_tails_unit_entry()` を拡張（例: 「サソリ型2本11節」「上→下の配置」）。`Branches[].Laterality` が `null`（Upper/Lower に挟まれた中間層等）の場合も「中間 / middle」で欠落させず表記する。また `TailsUnit[*].TailsUnit_PNGName` 由来の尾構造参考画像（レコード `images.tails_unit[]`、DB 上のパスは `DB_Primary/attr/tailsUnit/`）を `collect_reference_images()` が収集するようになった。既存の「corefolder に TailsUnit を注入すると球体型への枝分かれシッポを誘発する」方針を踏襲し、この参考画像も **humanoid 形態限定**（corefolder では `_is_path_compatible_with_form()` が除外）。`collect_record_capabilities()` の `has_tails_unit` で有無を確認できる。
> **2026-07-11 更新（IdentityMotif / NumberMarkLocation 廃止）**: creations-db 側で `AppearanceDetail` への情報集約が完了し、旧フィールド `IdentityMotif`（識別モチーフ）と `NumberMarkLocation`（番号印字位置、ブロック 5 で使用）が完全廃止された（DB・API大幅整備 その18）。`IdentityMotif.Motif_EN` は 2026-06-29 実装済みの `AppearanceDetail(#Element_Motif/#Element_CostumeItem)` フォールバックが常時経路として機能するため追従不要。`NumberMarkLocation`（`Marks[].MarkPosition_EN`/`MarkColor_EN`/`MarkNotation_EN`）は新設の `_extract_number_mark_from_appearance_detail()` が `AppearanceDetail` の `#Element_NumberMark` エントリ（`#DesignAttr_Position`/`Color`/`Notation`、Formation が対象 form または null＝両形態共通のエントリを収集）からフォールバック値を再構築する。複数箇所印字（例: Num28 の胸+左肩+右肩+イヤリング）にも対応。
> **2026-07-13 更新（`ColorPalette` 新設への追従 / ブロック 6.8）**: creations-db に構造化フィールド `ColorPalette`（`$Def_ColorPalette[]`: `Role`/`Hex`/`ColorName_JP`/`ColorName_EN`/`AppliesTo[]`/`Formation`/`Note_JP`/`Note_EN`）が新設され、設定画のカラーチップから実測した**作者指定の HEX** が NumberTales/Primary の 94 件に投入された。あわせて AIHints の `common.palette_priority` が `ColorPalette` からの機械導出値となり、従来 **全件 `null`** だった配色が 91 件で 3 色確定した。
> これを受けて `src/utils/dataset.py` に `extract_color_palette()` / `_build_color_palette_block()` を新設し、**Gemini・DALL-E の両ビルダーへ `[配色仕様]` ブロックを注入**する（従来の Gemini 限定 `[パレット参考]`（3 スロットの裸 HEX・プロンプト末尾）は本ブロックに統合・置換。DALL-E 側は配色情報を一切持っていなかった）。`Formation` が対象 form または `null`（両形態共通）のエントリのみを採り、Role を 主色 → 補助色 → 差し色 → 副色 の順に整列する（副色は最大 4 件）。`ColorPalette` 不在のレコード・作品では `ai_hints.common.palette_priority` の 3 スロットへフォールバックし、いずれも無ければブロックごと省略する。`Hex` は DB の `#Hexcode_Color` 型（`#RRGGBB` / `#RRGGBBAA`）で検証し、不正値は捨てる。
> パイプライン側は Stage 2 (`db_collector`) の `character_spec.color_palette` に配色を載せ（`db_summary.json` に記録）、Stage 4 (`correction_generator`) の違反分析へ配色照合を追加した（**明らかな色相ズレのみ違反**とし、陰影・ハイライト・照明差は違反としない）。i2i 修正プロンプトの「維持すること」にも配色を明記し、修正で色が飛ぶのを防ぐ。Stage 1 (`prompt_refiner`) はリファイン時に HEX と適用部位を**逐語で保持**するようシステム指示を強化した。
> `ColorName_JP` / `ColorName_EN` / `Note_*` は**創作内容にあたるため上流のツールも Claude も埋めない**（先輩が手入力する領域）。値が入れば `- 主色 #E8F152 (Izuna Yellow) : arm, foot — 補足` の形で自動的にプロンプトへ載る。テキスト生成（`src.pipeline.text_pipeline`）は散文・キャプション用途のため HEX は注入しない。
>
> **2026-07-10 更新（曖昧フィールド解決）**: `RaceType` / `Height_cm` のように DB 側で複数候補
> （`#DictIndex_withAbout[]` 型: `[{"value":...,"about_JP":...,"about_EN":...}, ...]`）を持ちうる
> フィールドは、`src/utils/dataset.py` の `_AMBIGUOUS_FIELD_SPECS` レジストリ + `_resolve_ambiguous_field()`
> が汎用的に解決する。シーン文（`--scene` / `--natural` 抽出値 / i2i 時は `--revisions` をフォールバック）
> の文脈が候補の `about_JP`/`about_EN` の示す非日常的な状態を明示的に示唆していればその候補を、
> 示唆が無ければ既定・平常状態を表す候補を LLM（OpenAI→Gemini の順）が選ぶ。判定結果と理由は
> `stage1_meta.json` の `field_resolutions` に記録される。`--field-override FIELD=VALUE`
> （複数回指定可）で明示的に上書きでき、実ターミナル (TTY) 実行時は候補が複数ある場合に対話確認
> プロンプトが出る（`--non-interactive` でスキップ可）。詳細は [`AGENTS.md`](../AGENTS.md) と
> `src/utils/dataset.py` の `_AMBIGUOUS_FIELD_SPECS` を参照。新しい対象フィールドを追加する場合は
> レジストリに1行足すだけでよい（対象外: `Weight_kg` は「基本値+装備品加算」という別の意味構造のため
> 対象外）。

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
