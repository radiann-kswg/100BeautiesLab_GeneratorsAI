# REFERENCE — numbertales-imagegen

`src.pipeline.image_pipeline` / `src.batch_generate` の詳細リファレンス。
正本は `docs/usage-generation.md` / `docs/usage-iterate.md` / `docs/output-and-logs.md`。

---

## 1. image_pipeline フラグ一覧

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--num` | (いずれか必須) | キャラクター番号（単体生成） |
| `--nums` | — | 複数番号 カンマ区切り（例 `25,52`）。**2件以上で全員を1枚に合同生成** |
| `--natural TEXT` | — | 自然文からパラメータを LLM 抽出 |
| `--story FILE` | — | テキストファイルから LLM 抽出 |
| `--form` | `corefolder` | 形態 `corefolder` / `humanoid`（`--natural` 時は LLM 判定優先） |
| `--scene` | `""` | シーン説明。省略時は Stage 1 で自動生成 |
| `--style` / `--composition` / `--background` | `""` | 作風・構図・背景ヒント |
| `--skip-canva` | false | Stage 5 の Canva をスキップ（`CANVA_ACCESS_TOKEN` 不要） |
| `--correction-mode` | `t2i` | Stage 4 重度違反時の対処。`t2i`:Stage4内でT2I再生成 / `stage3`:ラフから再生成 |
| `--iterate-from PATH` | None | 前回生成画像を起点に Stage 3 を i2i モードで実行 |
| `--revisions TEXT` | None | 修正指示（`;`/改行区切り）。`--iterate-from` と併用 |
| `--prefer-gemini-parse` | false | `--natural`/`--story` のパースで Gemini を OpenAI より優先 |
| `--work` | `#Works_NumberTales` | 作品キー |
| `--out` | env `OUTPUT_BASE_DIR` | 出力ベースディレクトリ |

関数エントリ: `src.pipeline.image_pipeline.run_image_pipeline(num, form, work_key, out_dir, scene, style, composition, background, skip_canva, correction_mode, iterate_from, revisions)`

---

## 2. batch_generate（量産用・単体プロバイダ）

| フラグ | 説明 |
|---|---|
| `--nums` | 対象番号 カンマ区切り |
| `--forms` | `corefolder` / `humanoid` / `both` |
| `--provider` | `gemini` / `openai` / `both` |
| `--dry-run` | 対象の確認のみ（**本実行前に必須**） |
| `--work` | 作品キー（既定 `#Works_NumberTales`） |

単体プロバイダ直叩き:
```bash
python -m src.gemini.generate --num 57 --form corefolder
python -m src.openai.generate --num 57 --form corefolder
python -m src.openai.generate --num 57 --mode prompt-assist --scene "図書館で本を読んでいるシーン"
```

---

## 3. 環境変数（.env）

| 変数 | 用途 |
|---|---|
| `GEMINI_API_KEY` | Gemini / Imagen（必須級） |
| `OPENAI_API_KEY` | GPT-4o（Stage1/4。必須級） |
| `IMAGEN_MODEL` / `GEMINI_REFERENCE_MODEL` / `GEMINI_TEXT_MODEL` | Gemini 系モデル指定 |
| `DALLE_MODEL` / `OPENAI_IMAGE_QUALITY` / `GPT_MODEL` | OpenAI 系モデル指定 |
| `FIREFLY_CLIENT_ID` / `FIREFLY_CLIENT_SECRET` / `FIREFLY_SIZE` / `FIREFLY_MODEL` | Adobe IMS 認証 |
| `ADOBE_STORAGE_TYPE` | `local`（既定 PIL fallback）/ `dropbox` / `s3` |
| `CANVA_ACCESS_TOKEN` / `CANVA_EXPORT_FORMAT` | Canva 仕上げ（`--skip-canva` で不要） |
| `OUTPUT_BASE_DIR`（互換 `OUTPUT_DIR`） | 出力ベース |
| `FORM_COMMON_DATASET_PATH` | 形態共通データセットの上書きパス |

---

## 4. 出力構成

### 単体（`--num`）
```
{OUTPUT_BASE_DIR}/{YYYYMMDD}/{ts}_pipeline_{form}_num{NNN}/
  stage1_prompt/   openai/gemini/base テキスト + stage1_meta.json
  stage2_db/       DB サマリー + キャラスペック（violation_features 等）
  stage3_rough/    Gemini Imagen ラフ5案（regen/ は --correction-mode stage3 時）
  stage4_correct/  analysis_log.json + 修正済み画像
  stage5_final/    Canva 仕上げ3枚（synth/ は合成中間）
  pipeline_summary.json
  prompt.txt / run_meta.json / notes.md   ← 上書き禁止・追記マージ
```

### 合同（`--nums`）
```
{OUTPUT_BASE_DIR}/{YYYYMMDD}/{ts}_pipeline_{form}_nums{AAA}_{BBB}/
  stage1_prompt/char_{AAA}/  stage1_prompt/char_{BBB}/
  char_{AAA}/stage3_rough/  char_{AAA}/stage4_correct/
  char_{BBB}/stage3_rough/  char_{BBB}/stage4_correct/
  stage5_final/synth/  stage5_final/canva/
  pipeline_summary.json
```

---

## 5. 補助ツール

```bash
# 自然文パーサー単体（抽出結果のみ）
python -m src.pipeline.natural_parser "コアフォルダ姿の25(フィズ)がチョコレートを咥えている絵"

# MIME チェック
python -m src.tools.check_image_mime
python -m src.tools.check_image_mime --fix-rename
python -m src.tools.check_image_mime --strict   # CI 用 exit 1

# 旧出力レイアウト移行
python -m src.tools.migrate_output_layout --dry-run
python -m src.tools.migrate_output_layout

# 作風データセットビルダー
python scripts/build_style_dataset.py --dry-run
python scripts/build_style_dataset.py --max-chars 10
```

---

## 6. インストール方法（プロジェクトスキル化）

このスキルをこのリポジトリ専用のプロジェクトスキルとして有効化するには、
`SKILL.md` と `REFERENCE.md` を以下へ配置する:

```
.claude/skills/numbertales-imagegen/
  SKILL.md
  REFERENCE.md
```

正式な「マイスキル」として全プロジェクト共通で使いたい場合は、Claude の
Settings > Capabilities から登録する。
