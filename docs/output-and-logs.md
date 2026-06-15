# output-and-logs.md — 出力レイアウト・実行ログ仕様

`output/` 配下の物理レイアウトと、各実行ディレクトリに残るログファイル
(`prompt.txt` / `run_meta.json` / `notes.md`) の役割と書式をまとめたページ。

> 関連: [`docs/README.md`](README.md) / [`AGENTS.md`](../AGENTS.md) / [`tools.md`](tools.md)

---

## 1. 物理レイアウト (2 階層 = 日付フォルダ + 1 実行フォルダ)

```text
output/
└── {YYYYMMDD}/                            # 作業日 (例: 20260616)
    └── {YYYYMMDD_HHMMSS}_{provider}_{form}_num{NNN}[_suffix]/   # 1 実行 = 1 フォルダ
        ├── num057_corefolder_01.png       # 生成画像
        ├── prompt.txt                     # 渡したプロンプト本文
        ├── run_meta.json                  # 構造化メタ
        └── notes.md                       # 手書きレビュー
```

> **旧 3 階層 (`{YYYYMMDD}/{YYYYMMDD_HH}/{run}/`) からの変更点**: 「1 回の実行ごとに
> フォルダを分けて見やすく」という方針に合わせ、時間帯フォルダ `{YYYYMMDD_HH}/` を
> 廃止し **日付フォルダ + 実行フォルダの 2 階層** にした。パイプライン各ステージ配下の
> 子生成は日付フォルダ自体を作らずフラットに置く (§6 参照)。

### 命名要素

| 要素             | 例                          | 備考                                                               |
| ---------------- | --------------------------- | ------------------------------------------------------------------ |
| `{YYYYMMDD}`     | `20260616`                  | 作業日 (この日の実行をすべて束ねる)                               |
| `{ts}`           | `20260616_140532`           | 個別実行のタイムスタンプ (= 実行フォルダ名の先頭)                 |
| `{provider}`     | `gemini` / `openai`         | 使用プロバイダ                                                     |
| `{form}`         | `corefolder` / `humanoid`   | 形態                                                               |
| `{NNN}`          | `057`                       | キャラクター番号 (3 桁ゼロパディング)                              |
| `_suffix` (任意) | `_iter1` / `_prompt-assist` | i2i 改稿時の `iterN`、`prompt-assist` モード時の専用フォルダ識別子 |

### ベースディレクトリの上書き

| 優先順位 | ソース                | 例                                  |
| -------- | --------------------- | ----------------------------------- |
| 1        | CLI `--out <dir>`     | `--out C:\tmp\gen-test`             |
| 2        | env `OUTPUT_BASE_DIR` | `.env` に `OUTPUT_BASE_DIR=output2` |
| 3        | env `OUTPUT_DIR`      | 互換のため残してある旧名            |
| 4        | デフォルト            | `output`                            |

> 標準 (`--out` 省略時) は **配下に `{YYYYMMDD}/{run}/` の 2 階層を切る** ため、過去 run を上書きする事故は起きない。
> `--out <dir>` を明示した単体生成では、その dir 直下に run フォルダを直に置く (日付フォルダは作らない)。

### 実装

ロジックは [`src/utils/paths.py`](../src/utils/paths.py) の `build_run_output_dir()` に集約。
旧フォーマットを新階層へ寄せる移行ツールは [`tools.md`](tools.md#output-レイアウト移行-migrate_output_layout) を参照。

---

## 2. `prompt.txt`

- モデルに渡したプロンプト本文を **そのまま** 保存。
- Gemini multimodal の場合も、テキスト部分だけがこのファイルに入る (添付画像は `run_meta.json` の `reference_local_paths` で追跡)。
- 失敗時も保存される。
- **上書き禁止**。何か追記したくなったら隣の `notes.md` 側に書く。

主要ブロックの構造は [`usage-generation.md`](usage-generation.md#5-プロンプトの内部構造) を参照。

---

## 3. `run_meta.json`

実行ごとの構造化メタ。形式例:

```json
{
  "provider": "gemini",
  "model": "imagen-4.0-generate-001",
  "reference_model": "models/gemini-3.1-flash-image",
  "use_reference_input": true,
  "num": 57,
  "form": "corefolder",
  "work_key": "#Works_NumberTales",
  "character_name": "イズナ",
  "count": 1,
  "scene": "縁側で日向ぼっこ",
  "style": "watercolor",
  "composition": "bust shot",
  "background": "wooden veranda with persimmon trees",
  "iteration": null,
  "reference_urls": ["https://database.numbertales-radiann.net/..."],
  "reference_local_paths": [
    "_creations-ai/creations-db/data/Works_NumberTales/Images/.../emstk_corefolder57-1.png"
  ],
  "record_capabilities": {
    "current_form_hints_present": true,
    "form_hints_available": ["corefolder", "humanoid"],
    "outfit_features_count": 4,
    "outfit_features_after_filter": 4,
    "db_image_present": true
  },
  "status": "ok",
  "results": [
    { "file": "num057_corefolder_01.png", "status": "ok", "mime": "image/jpeg" }
  ],
  "errors": []
}
```

### 主なフィールド

| フィールド              | 説明                                                                                   |
| ----------------------- | -------------------------------------------------------------------------------------- |
| `provider` / `model`    | 使用プロバイダ/モデル                                                                  |
| `reference_model`       | Gemini multimodal モデル (i2i に使う方)                                                |
| `use_reference_input`   | 参照画像経路を通ったかどうか                                                           |
| `iteration`             | i2i 時のチェーン情報 (詳細は [`usage-iterate.md`](usage-iterate.md))                   |
| `reference_urls`        | プロンプトに含めた参照画像 URL リスト                                                  |
| `reference_local_paths` | 実バイトを添付したローカル画像パスリスト (Gemini Part.from_bytes / OpenAI images.edit) |
| `record_capabilities`   | キャラ/形態の AI ヒント有無、衣装語フィルタ前後件数、DB 画像存在チェック等             |
| `status`                | `"ok"` / `"failed"` / `"partial"`                                                      |
| `results[]`             | 各生成ファイルの結果。失敗時は `status: "failed"` + 簡易メッセージ                     |
| `errors[]`              | 失敗時のエラー要旨 (型名 + メッセージ)                                                 |

### 実装

書き出しは [`src/utils/run_log.py`](../src/utils/run_log.py) の
`initialize_run_logs()` (実行開始時) / `finalize_run_logs()` (終了時に status/results/errors を書き戻し) に集約。

---

## 4. `notes.md`

手書きレビュー用テンプレ。生成完了直後にエージェントが空のテンプレを生成しておく。

### テンプレ例

```markdown
# Run Notes: {ts}_{provider}_{form}\_num{NNN}

- prompt: prompt.txt
- meta: run_meta.json
- 生成画像: num057_corefolder_01.png

## 観察

(出力画像で実際にどう描かれていたかを書く)

## 気になった点

(意図と違う部分・崩れた部分・原典逸脱を書く)

## 改善案

(次回プロンプトでどう詰めるか、--iterate-from で当てるなら何を直すかを書く)
```

### 書く時のヒント

- **観察 → 気になった点 → 改善案** の順で 1 セット書くと、後で diff を取りやすい。
- `--iterate-from` で改稿した場合は **起点 run の相対パス** を冒頭に追記しておくと、チェーンが追える。
- 大量に書く必要はない。1〜3 行ずつでも十分後追いになる。
- **追記マージのみ。 上書きはしない** (失敗 run のメモも残す)。

---

## 5. ログを後から串刺しで読む

```powershell
# 直近の run_meta.json を一覧
Get-ChildItem -Recurse -Filter run_meta.json output | Sort-Object LastWriteTime -Descending | Select-Object -First 10

# 失敗した run だけ抽出
Get-ChildItem -Recurse -Filter run_meta.json output | ForEach-Object {
  $m = Get-Content $_.FullName -Raw | ConvertFrom-Json
  if ($m.status -eq 'failed') { [pscustomobject]@{ path=$_.Directory; err=$m.errors -join '; ' } }
}

# 特定キャラの全 run の prompt 末尾だけ眺める
Get-ChildItem -Recurse -Filter prompt.txt output | Where-Object { $_.Directory.Name -match 'num057' } |
  ForEach-Object { "=== $($_.Directory.Name) ==="; Get-Content $_.FullName -Tail 30 }
```

---

## 6. パイプライン固有のディレクトリ構造

`src.pipeline.image_pipeline` を使って生成した場合は、日付フォルダ直下の
パイプライン実行フォルダ (1 実行 = 1 フォルダ) の中に各ステージのサブディレクトリが作られる。
各ステージ配下の子生成 (Gemini/Canva) は **日付フォルダを作らずフラットに** 置かれる。

### 単体キャラクター (`--num`)

```text
output/{YYYYMMDD}/{ts}_pipeline_{form}_num{NNN}/      # ← 1 実行 = 1 フォルダ
├── stage1_prompt/
│   ├── prompt_openai.txt
│   └── prompt_gemini.txt
├── stage3_rough/          # ラフ5案 (Gemini) + Adobe 構図ガイド
│   └── {ts}_gemini_{form}_num{NNN}/      # 子生成はフラット 1 段
│       ├── num{NNN}_{form}_01.jpg
│       └── ...
├── stage4_correct/        # 違反修正 (i2i, キャラ別)
│   ├── rough_01_corrected/
│   │   └── {ts}_gemini_{form}_num{NNN}_iter1/
│   └── ...
├── stage5_final/
│   ├── synth/             # Gemini 合成 3 枚
│   └── canva/             # Canva 仕上げ (--skip-canva 省略時)
└── pipeline_summary.json  # 全 Stage の結果パスとメタ
```

### 合同キャラクター (`--nums`)

```text
output/{YYYYMMDD}/{ts}_pipeline_{form}_nums{AAA}_{BBB}/
├── stage1_prompt/
│   ├── char_{AAA}/
│   │   ├── prompt_openai.txt
│   │   └── prompt_gemini.txt
│   └── char_{BBB}/
│       └── ...
├── char_{AAA}/
│   ├── stage3_rough/      # ラフ3枚/キャラ (Gemini)
│   └── stage4_correct/    # 違反修正 (i2i, キャラ別)
├── char_{BBB}/
│   ├── stage3_rough/
│   └── stage4_correct/
├── stage5_final/
│   ├── synth/             # 全キャラ画像を参照して合成 3 枚
│   └── canva/
└── pipeline_summary.json
```

### `pipeline_summary.json` の主要フィールド

| フィールド         | 説明                                                                                        |
| ------------------ | ------------------------------------------------------------------------------------------- |
| `nums`             | 対象キャラ番号リスト                                                                        |
| `form`             | 形態 (`corefolder` / `humanoid`)                                                            |
| `stage3_paths`     | Stage 3 生成パス。単体は配列、合同は `char_{NNN}` キーごとの dict + `"all"` キー            |
| `stage4_paths`     | Stage 4 補正パス。合同は `char_{NNN}` キーと `"best_per_char"` (Stage 5 参照用) を含む      |
| `stage5_paths`     | `synth` / `canva` / `all` の3キー                                                           |
| `stage1_prompts`   | シーン / キャラ名 / `iterate_from` + `revisions` (i2i 時)                                   |
| `status`           | `"ok"` / `"failed"` / `"partial"`                                                           |
| `errors`           | 各 Stage のエラー要旨                                                                        |
| `elapsed_seconds`  | パイプライン全体の所要秒数                                                                  |

---

## 7. 関連規約

- **絶対に上書きしない**: 既存 run の `prompt.txt` / `run_meta.json` / `notes.md` は失敗時でも残す。新しい試行は必ず新フォルダ。
- **MIME 整合性**: Gemini が JPEG を返しているのに `.png` で保存されると後段の Anthropic API などに弾かれる。
  - 保存側は [`src/utils/image_io.py`](../src/utils/image_io.py) の `save_image_bytes()` がバイト列マジックで自動補正する。
  - 既存ファイルの一括検証/修正は [`tools.md`](tools.md#画像-mime-チェック-check_image_mime) を参照。
- **不要なフォルダの削除**: レビュー済みで残しておく価値のない run は手動削除でよい。ただし notes.md に教訓を残してからにする。
