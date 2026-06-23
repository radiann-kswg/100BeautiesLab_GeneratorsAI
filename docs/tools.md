# tools.md — 補助ツールとデータセット管理

`src/tools/` 配下のメンテツールと、形態共通データセット (`_ideas/form_common_datasets/Works_*.json`) の管理についてまとめたページ。

> 関連: [`docs/README.md`](README.md) / [`AGENTS.md`](../AGENTS.md) / [`output-and-logs.md`](output-and-logs.md)

---

## 1. 画像 MIME チェック (`check_image_mime`)

Anthropic 等の後段 API は、宣言 MIME と実体バイト列が一致しないと
`invalid_request_error (400)` で弾く。
Gemini が JPEG を返しているのに `.png` で保存される事故があったため、定期スキャンを推奨。

### コマンド

```powershell
# output/ を再帰スキャン (デフォルト)
python -m src.tools.check_image_mime

# 別のディレクトリ・ファイルをスキャン
python -m src.tools.check_image_mime path/to/dir path/to/file.png

# JSON 出力
python -m src.tools.check_image_mime --json

# CI 用: ミスマッチや unreadable があれば exit 1
python -m src.tools.check_image_mime --strict
```

### 修正モード (排他)

```powershell
# 拡張子を実体に合わせてリネーム (例: 中身 JPEG の .png → .jpg)
python -m src.tools.check_image_mime --fix-rename

# 実体を拡張子に合わせて Pillow で再エンコード
python -m src.tools.check_image_mime --fix-reencode

# 計画だけ確認 (--fix-* と併用)
python -m src.tools.check_image_mime --fix-rename --dry-run
```

### 保存側の自動補正

`src/utils/image_io.py` の `save_image_bytes()` がバイト列の先頭マジック (PNG/JPEG/GIF/WEBP/BMP/TIFF) を見て拡張子を自動補正する。
`gemini/generate.py` と `openai/generate.py` の保存処理はこのユーティリティ経由なので、新しい run で MIME ミスマッチが発生することは原則無い。

過去の蓄積分 (旧コードで保存された 31 ファイル) は 2026-06-08 に `--fix-rename` で `.jpg` 化済み。

---

## 2. output レイアウト移行 (`migrate_output_layout`)

旧レイアウト (`output/{ts}_..._num.../` の平置き、`output/{date}/{date}_{HH}/{run}/` の旧 3 階層、
`output/{date}/{provider}/...` のような変則) を、現行 2 階層
(`output/{YYYYMMDD}/{ts}_{provider}_{form}_num{NNN}/`) に寄せるためのワンショットツール。
旧 3 階層の時間帯フォルダ `{YYYYMMDD_HH}/` は引き上げ後に空削除される。

### コマンド

```powershell
# 1. 必ず dry-run で計画を確認
python -m src.tools.migrate_output_layout --dry-run

# 2. JSON で計画を出力 (差分レビュー用)
python -m src.tools.migrate_output_layout --dry-run --json

# 3. 問題なければ本実行
python -m src.tools.migrate_output_layout

# 4. ベースを変えたい場合
python -m src.tools.migrate_output_layout --base C:\tmp\old-output
```

### 注意

- dry-run で **warnings がゼロ** であることを確認してから本実行する。
- 既に新レイアウトに収まっている run は触らない (idempotent)。
- 一度本実行したら、再度走らせても何も移動しない設計。
- 詳細は [`src/tools/migrate_output_layout.py`](../src/tools/migrate_output_layout.py) のコメント参照。

---

## 3. 形態共通データセット (`Works_*.json`)

作品ごとの「形態共通のシルエット / 必須形状 / 禁止語」を 1 ファイルにまとめた JSON。
プロンプト生成時に **`[形態共通データセット]`** ブロックとして自動挿入される。

### ファイル配置

```text
_ideas/
└── form_common_datasets/
    └── Works_NumberTales.json    # ナンバーテールズ用
```

新作品を増やすときは `Works_{作品名}.json` を 1 枚追加すればよい。
読込順は `FORM_COMMON_DATASET_PATH` (env) → 作品キーから推定したファイル名。

### スキーマ概要

```jsonc
{
  "version": "2026-06-09.1",
  "work_key": "#Works_NumberTales",
  "forms": {
    "corefolder": {
      "definition_ja": "...",
      "definition_en": "...",
      "surface_description_ja": "...",
      "surface_description_en": "...",
      "silhouette_summary_ja": "...",
      "silhouette_summary_en": "...",
      "common_equipment": ["..."],
      "texture_traits": ["..."],
      "function_traits": ["..."],
      "required_shape_keywords": [
        "the spherical body itself is the character's living form (NOT a costume worn over a humanoid body)",
        "decorations and number markings are applied directly on the sphere surface or harness (NOT as separate worn clothing or printed onto a removable suit)",
        "...",
      ],
      "disallow_cross_form_keywords": [
        "human limbs",
        "shoes",
        "pants",
        "backpack",
        "satchel",
        "chest harness with belts",
        "mascot suit",
        "ball-shaped costume",
        "space helmet",
        "glass dome over the head",
        "...",
      ],
    },
    "humanoid": {
      /* 同じ構造 */
    },
  },
}
```

### よく触るフィールド

| フィールド                       | 目的                                                             | 編集の指針                                                                 |
| -------------------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `required_shape_keywords[]`      | 形態の **絶対要件** (例: corefolder は球体・humanoid は二足歩行) | 観察された崩れ方を「肯定文」で書き足す                                     |
| `disallow_cross_form_keywords[]` | **侵食を防ぐ禁止語** (corefolder に humanoid 衣装語が出る等)     | 実 run で観察された誤要素 (`backpack`, `helmet`, `bondage rope` 等) を追記 |
| `common_equipment[]`             | 全キャラ共通の装備 (例: 番号入りハーネス)                        | 個別キャラ仕様は AI ヒント側に書く                                         |
| `texture_traits[]`               | 全体の質感トーン                                                 | (補助情報)                                                                 |
| `definition_*` / `surface_*`     | 形態の定義文。ja/en 両方                                         | プロンプト本文に直接差し込まれる                                           |

### 更新時のルール

- 編集したら **必ず `version` を上げる** (例: `2026-06-09.1` → `2026-06-09.2`)。
- 変更内容はコミットメッセージまたは `notes.md` に記録する。
- 既存生成への影響範囲が広いので、本番バッチ前に **1 キャラだけ単発生成** して `prompt.txt` の `[形態共通データセット]` 出力を目で確認する。

### 実装参照

- ローダー: `src/utils/dataset.py` の `_load_form_common_dataset()` (`@lru_cache`)
- 差し込み: `src/utils/dataset.py` の `_build_form_common_dataset_block()`

---

## 4. リファレンス参照画像の解決

`src/utils/dataset.py` の `collect_reference_images()` が以下を統合する。

1. `ai_hints.*.reference_images[]` (AI 学習データ由来)
2. レコードの `images` (DB 由来・新形式)
   - `concept[]` / `concept_alt[]`: 文字列パスの配列
   - `arts[]` / `design_alt[]`: `{path, form, characters:[id...]}` オブジェクトの配列
     - `characters` フィールドで対象キャラを明示判定（合同構図にも対応）
     - `form` フィールドがパスに反映されており、`_is_path_compatible_with_form()` で形態互換を確認
3. `work_common.reference_images.{corefolder_reference[], humanoid_reference[]}` (作品共通設計図 `cnsp-fg_NTsCoreFolder.png` 等)

### URL → ローカル変換

`_collect_work_common_reference_images()` 内で
`https://database.numbertales-radiann.net/` → `_creations-ai/creations-db/` 変換を試み、
ローカルにあれば実バイトで Gemini に渡せるようにしている。
これにより、ネット越し DL を待たずに `Part.from_bytes` で確実に添付できる。

---

## 5. 創作 DB パッケージ参照の制御

env `CREATIONS_DB_PACKAGE_ENABLE` で動作切替。

| 値                    | 動作                                                           |
| --------------------- | -------------------------------------------------------------- |
| 未設定 / `1`          | `_creations-ai/creations-db/pkg/` 配下のパッケージレイヤを使う (デフォルト) |
| `0` / `false` / `off` | 無効化。 raw JSON だけを読む                                   |

通常は触らない。デバッグや上流改修時の動作切り分けで使う。

---

## 6. 今後ツールを追加するときの規約

新ツールを `src/tools/` に置く場合:

1. `python -m src.tools.<name>` で実行できるよう `argparse` ベースで書く。
2. デフォルトで **副作用なし** (dry-run 相当) になるようにする。書き換え系は `--fix-*` や明示フラグで opt-in。
3. CI 連携を想定するなら `--strict` (exit 1) と `--json` (機械可読) を揃える。
4. **必ずこの `docs/tools.md` に節を追加する** 。コマンド例 + フラグ表 + 主要オプションの説明を最小セット。
5. AGENTS.md / copilot-instructions.md のクイックリファレンスにも 1 行載せる。

## ステージ分割 CLI (`src.pipeline.stage_cli`)

時間制約のある実行環境(例: Cowork サンドボックスの 1 コマンド 45 秒上限・バックグラウンド
常駐不可)向けに、`image_pipeline` の 5 ステージを「呼び出し単位」で分割実行する CLI。
ステージ間の受け渡しは run-dir 直下の `pipeline_state.json` に永続化される。

```bash
# Stage1: プロンプト生成 + run-dir/state 作成 (最終行に RUN_DIR= を出力)
python -m src.pipeline.stage_cli stage1 --num 57 --form corefolder --scene "図書館で本を読むシーン"
# Stage2: キャラクター DB データ取得
python -m src.pipeline.stage_cli stage2 --run-dir <RUN_DIR>
# Stage3: ラフを 1 枚ずつ生成 (繰り返し呼ぶと state に追記)
python -m src.pipeline.stage_cli stage3 --run-dir <RUN_DIR> --count 1
# Stage4: 違反修正 (--limit/--offset で 1 枚ずつ処理可)
python -m src.pipeline.stage_cli stage4 --run-dir <RUN_DIR> --limit 1
# Stage5: 合成完成画像 (既定 Canva スキップ・1 枚ずつ追記)。--with-canva で Canva 仕上げ
python -m src.pipeline.stage_cli stage5 --run-dir <RUN_DIR> --count 1
# 進捗確認
python -m src.pipeline.stage_cli status --run-dir <RUN_DIR>
```

- 実装: [src/pipeline/stage_cli.py](../src/pipeline/stage_cli.py)
- 状態ファイル: `<run-dir>/pipeline_state.json`(各ステージが冪等に追記)。
- `generate_final_images()` に `count` 引数を追加済み(Stage5 を 1 枚ずつ呼ぶための拡張)。
- 合同(複数キャラ 1 枚合成)も分割実行に対応(`state["mode"]=="combined"`)。
  `stage1 --nums 24,42` で開始し、`stage3`/`stage4` は `--num` でキャラ指定、
  `stage5` で全員のベストを Gemini マルチ参照で 1 枚に合成する。
  ワンショットで回せる環境では従来どおり `image_pipeline --nums` でもよい。
- Canva 仕上げ(Stage5b)は `api.canva.com` 到達環境でのみ `--with-canva` で有効。
  到達不可環境では既定スキップし、接続済み Canva / Adobe Express MCP で代替する。
- Claude パーソナルスキル: `nt-pipeline-split`(分割パイプライン), `nt-gemini-image` /
  `nt-openai-image` / `nt-text`(単体 LLM)として配布。

## 同期チェッカ (`src.tools.check_sync`)

サンドボックス(FUSE マウント)が対象ファイルを完全に反映しているか(=同期済みか)を
判定する汎用ツール。Cowork 等では Windows 側で編集した直後のファイルがマウント上で
旧版/切り詰めとして見えることがある(eventual consistency)。本ツールは対象が
「壊れず完全に読める」ことを確認し、任意で部分文字列・SHA256 と照合する。
CI・予約タスク・オーケストレータから繰り返し呼ぶ用途を想定。

```bash
python -m src.tools.check_sync src/pipeline/stage_cli.py
python -m src.tools.check_sync FILE --expect-substr "main()"
python -m src.tools.check_sync FILE --expect-sha256 <hex>
python -m src.tools.check_sync --manifest sync_manifest.json --strict   # 予約タスク/CI: 未同期で exit 1
python -m src.tools.check_sync FILE --json                              # 機械可読出力
```

| フラグ | 説明 |
|---|---|
| `files...` | 判定対象(複数可) |
| `--expect-substr` | 全対象に共通で要求する部分文字列(機能追加の確認) |
| `--expect-sha256` | 単一対象の期待 SHA256(厳密同期) |
| `--manifest` | `{"files":{path:{expect_substr,sha256}}}` 形式の JSON |
| `--strict` | 未同期(いずれか pending)なら exit 1 |
| `--json` | 機械可読 JSON 出力 |

- 判定: 存在/非空 → `.py` は `ast.parse`(切り詰め検出) → `--expect-substr` → ハッシュ照合。
- 実装: [src/tools/check_sync.py](../src/tools/check_sync.py)
- 活用例: 予約タスク `mount-sync-watch-stagecli`(30分毎)がこれを `--strict` で呼び、
  `stage_cli.py` の合同機能が完全反映されたら通知して自己停止する。

## Canva トークン再取得 (`refresh_canva_token`)

Canva の OAuth2 PKCE フローを Python だけで完結させ、取得したアクセストークンで `.env` を自動更新するツール。
`CANVA_ACCESS_TOKEN` の有効期限は約4時間なので、Stage 5 で `401` が出たら実行する。

初回 PKCE 認証後は `CANVA_REFRESH_TOKEN` も `.env` に保存されるため、
**2回目以降は `--use-refresh-token` でブラウザなし**で更新できる。
MCP サーバ側からは `numbertales_refresh_canva_token` ツールで自動更新可能。

### 前提

`.env` に以下が設定されていること:

```
CANVA_CLIENT_ID=<your_client_id>
CANVA_CLIENT_SECRET=<your_client_secret>
```

### コマンド

```bash
# 【初回】ブラウザで Canva ログイン → CANVA_ACCESS_TOKEN と CANVA_REFRESH_TOKEN を .env に保存
python -m src.tools.refresh_canva_token
# Linux / GCE 環境では python3 を使う
python3 -m src.tools.refresh_canva_token

# 【2回目以降】CANVA_REFRESH_TOKEN を使ってブラウザなしで更新
python -m src.tools.refresh_canva_token --use-refresh-token

# .env を書き換えず取得トークンを表示のみ
python -m src.tools.refresh_canva_token --dry-run

# 別の .env を指定
python -m src.tools.refresh_canva_token --env path/to/.env

# タイムアウトを延長 (デフォルト 120 秒、通常フローのみ)
python -m src.tools.refresh_canva_token --timeout 180
```

### 手順 (初回・通常フロー)

1. スクリプトを実行すると認可 URL が表示される
2. ブラウザでその URL を開き Canva にログイン・「許可」を押す
3. ブラウザに「認証完了 ✅」が表示されたらターミナルに戻る
4. `.env` の `CANVA_ACCESS_TOKEN` と `CANVA_REFRESH_TOKEN` が自動更新される

### MCP サーバからの更新

Cloud Run 上の MCP サーバは `numbertales_refresh_canva_token` ツールを提供する。
このツールは `CANVA_REFRESH_TOKEN` を使って非対話的にトークンを更新し、
プロセスの環境変数と（権限があれば）Secret Manager に反映する。

- トークンエンドポイント: `https://api.canva.com/rest/v1/oauth/token`（PKCE S256 / refresh_token）
- コールバックポート: `3001`（`http://127.0.0.1:3001/oauth/redirect`）— 他プロセスが使用中の場合は解放してから実行
- 実装: [src/tools/refresh_canva_token.py](../src/tools/refresh_canva_token.py)

---

## パーソナルスキル `numbertales-imagegen`

`image_pipeline` / `batch_generate` を自然文依頼から実行するためのスキル一式。
実体は [.claude/skills/numbertales-imagegen/](../.claude/skills/numbertales-imagegen/) にあり、
デスクトップ版 Claude / Claude Code / Cowork のいずれからでも、**任意の cwd から**実行できる。

- ランチャー (パス非依存): `bin/ntimg.ps1`(Windows) / `bin/ntimg.sh`(bash・macOS・Cowork)。
  リポジトリルートを `NUMBERTALES_REPO` → `repo_path.txt` → スクリプト位置 4 階層上 の順で解決し、
  `PROJECT_ROOT` / `PYTHONPATH` を設定して `python -m <module>` を起動する。
  モジュール切替は `-Module`(ps1) / `NT_MODULE`(sh)。
- 実行環境の指針: 実機(鍵あり・ネット可)では直接実行、Cowork サンドボックス等では
  実行せず組み立てたコマンドを提示(時間制約下では `stage_cli` で分割実行)。
- インストール(常に最新): `install-personal-skill.ps1` がリポジトリ内実体への
  ジャンクションを `~/.claude/skills/` に張る。`git pull` で全環境が最新化される。
  `repo_path.txt`(機種固有・`.gitignore` 済み)も自動生成。
- 配布(スナップショット): `build-skill-package.ps1` が `numbertales-imagegen.skill`(zip)を生成。
  `repo_path.txt` は除外され、設置先で `NUMBERTALES_REPO`/配置位置から repo を解決する。
- 詳細: [.claude/skills/numbertales-imagegen/REFERENCE.md](../.claude/skills/numbertales-imagegen/REFERENCE.md)
- 関連 src 変更: `load_manifest` を `PROJECT_ROOT` 基準に変更し cwd 非依存化
  ([src/utils/dataset.py](../src/utils/dataset.py))。
