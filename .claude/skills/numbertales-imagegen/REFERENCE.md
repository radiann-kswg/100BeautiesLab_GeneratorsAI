# REFERENCE — numbertales-imagegen

`src.pipeline.image_pipeline` / `src.batch_generate` の詳細リファレンス。
正本は `docs/usage-generation.md` / `docs/usage-iterate.md` / `docs/output-and-logs.md`。

---

## 0. ランチャー（パス非依存実行）

任意の cwd から実行するためのラッパー。リポジトリルートを自動解決し、
`PROJECT_ROOT` / `PYTHONPATH` を設定して目的のモジュールを起動する。

| ランチャー | 環境 | モジュール切替 |
|---|---|---|
| `bin/ntimg.ps1` | Windows / 実機 Claude Code | `-Module <name>`（既定 `src.pipeline.image_pipeline`） |
| `bin/ntimg.sh` | bash / macOS / Cowork サンドボックス | 環境変数 `NT_MODULE=<name>` |

リポジトリルート解決順（両ランチャー共通）:
1. 環境変数 `NUMBERTALES_REPO`
2. スキル直下 `repo_path.txt`
3. スクリプト位置から 4 階層上（`bin` → skill → `skills` → `.claude` → repo）
4. いずれも `src/pipeline/image_pipeline.py` の存在で検証。全滅ならエラー終了（exit 2）。

例:
```bash
./bin/ntimg.sh --num 57 --form corefolder --skip-canva
NT_MODULE=src.batch_generate ./bin/ntimg.sh --nums 15,57 --forms both --dry-run
NT_MODULE=src.pipeline.natural_parser ./bin/ntimg.sh "コアフォルダ姿の25(フィズ)の絵"
```
```powershell
./bin/ntimg.ps1 --num 57 --form corefolder --skip-canva
./bin/ntimg.ps1 -Module src.batch_generate --nums 15,57 --forms both --dry-run
```

ランチャーを使わない手動実行（フォールバック）:
```bash
cd <repo> && python -m src.pipeline.image_pipeline --num 57 --form corefolder
# もしくは任意 cwd から:
PROJECT_ROOT=<repo> PYTHONPATH=<repo> python -m src.pipeline.image_pipeline --num 57
```

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
NT_MODULE=src.gemini.generate ./bin/ntimg.sh --num 57 --form corefolder
NT_MODULE=src.openai.generate ./bin/ntimg.sh --num 57 --form corefolder
NT_MODULE=src.openai.generate ./bin/ntimg.sh --num 57 --mode prompt-assist --scene "図書館で本を読んでいるシーン"
```

---

## 3. 環境変数（.env / 実行時）

### 3.1 パス・実行系（このスキルが追加で参照）

| 変数 | 用途 |
|---|---|
| `NUMBERTALES_REPO` | ランチャーのリポジトリルート明示指定（最優先） |
| `PROJECT_ROOT` | src 側の基準ルート。manifest / creations-db / 形態共通データの解決に使用。ランチャーが自動設定 |
| `MANIFEST_PATH` | `manifest.jsonl` の上書きパス（未設定時は `PROJECT_ROOT/_creations-ai/ai-dataset/manifest.jsonl`） |
| `PYTHONPATH` | `src` パッケージ解決用。ランチャーが repo を前置 |

> 補足: `load_manifest` は cwd ではなく `PROJECT_ROOT`（既定はモジュール位置から解決）基準で
> manifest を探すため、ランチャー無しでも `PROJECT_ROOT` を渡せば任意 cwd から動く。

### 3.2 生成プロバイダ系

| 変数 | 用途 |
|---|---|
| `GEMINI_API_KEY` | Gemini / Imagen（必須級） |
| `OPENAI_API_KEY` | GPT-4o（Stage1/4。必須級） |
| `IMAGEN_MODEL` / `GEMINI_REFERENCE_MODEL` / `GEMINI_TEXT_MODEL` | Gemini 系モデル指定 |
| `DALLE_MODEL` / `OPENAI_IMAGE_QUALITY` / `GPT_MODEL` | OpenAI 系モデル指定 |
| `FIREFLY_CLIENT_ID` / `FIREFLY_CLIENT_SECRET` / `FIREFLY_SIZE` / `FIREFLY_MODEL` | Adobe IMS 認証 |
| `ADOBE_STORAGE_TYPE` | `local`（既定 PIL fallback）/ `dropbox` / `s3` |
| `CANVA_CLIENT_ID` / `CANVA_CLIENT_SECRET` | Canva OAuth2 クライアント資格情報（トークン再取得スクリプトが参照） |
| `CANVA_ACCESS_TOKEN` / `CANVA_EXPORT_FORMAT` | Canva 仕上げ（`--skip-canva` で不要）。期限切れは `python -m src.tools.refresh_canva_token` で再取得 |
| `OPENAI_CORRECTION_MODEL` | Stage 4 軽度違反の外科的 i2i 修正に使う gpt-image-1 モデル（例: `gpt-image-1`）。未設定時は Gemini i2i にフォールバック |
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
NT_MODULE=src.pipeline.natural_parser ./bin/ntimg.sh "コアフォルダ姿の25(フィズ)がチョコレートを咥えている絵"

# Canva アクセストークン再取得（期限切れ時）
NT_MODULE=src.tools.refresh_canva_token ./bin/ntimg.sh   # ブラウザで OAuth 認証 → .env 自動更新
NT_MODULE=src.tools.refresh_canva_token ./bin/ntimg.sh --dry-run   # .env を書き換えず表示のみ

# MIME チェック
NT_MODULE=src.tools.check_image_mime ./bin/ntimg.sh
NT_MODULE=src.tools.check_image_mime ./bin/ntimg.sh --fix-rename
NT_MODULE=src.tools.check_image_mime ./bin/ntimg.sh --strict   # CI 用 exit 1

# 旧出力レイアウト移行
NT_MODULE=src.tools.migrate_output_layout ./bin/ntimg.sh --dry-run
NT_MODULE=src.tools.migrate_output_layout ./bin/ntimg.sh
```

---

## 6. インストール / 配布

### 6.1 ジャンクション方式（推奨・常に最新）

```powershell
# .claude/skills/numbertales-imagegen/ から実行
./install-personal-skill.ps1
```
- リポジトリ内 `.claude/skills/numbertales-imagegen/` を実体とし、
  `~/.claude/skills/numbertales-imagegen` からジャンクションを張る。
- `repo_path.txt`（= ライブリポジトリの絶対パス）を自動生成。`.gitignore` 済み（機種固有）。
- `git pull` でスキル本体・ランチャーが自動更新される。
- 有効化: Settings > Capabilities で Code execution を ON にし、スキル一覧で本スキルを ON。

### 6.2 .skill パッケージ方式（スナップショット配布）

```powershell
./build-skill-package.ps1                 # リポジトリ直下に numbertales-imagegen.skill を出力
./build-skill-package.ps1 -OutDir C:\tmp  # 出力先指定
```
- `repo_path.txt` は除外される。設置先では `NUMBERTALES_REPO` か配置位置から repo を解決。
- デスクトップ版 Claude で `.skill` を開き "Save skill"、または `~/.claude/skills/` に展開。
- 最新追従はしないため、機能更新時は再ビルド/再インストールが必要。

### 6.3 ディレクトリ構成

```
.claude/skills/numbertales-imagegen/
  SKILL.md
  REFERENCE.md
  install-personal-skill.ps1
  build-skill-package.ps1
  bin/
    ntimg.ps1
    ntimg.sh
  repo_path.txt        ← install 時に生成（gitignore / 配布から除外）
```
