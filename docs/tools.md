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

旧レイアウト (`output/{ts}_..._num.../` などの平置き、`output/{date}/{provider}/...` のような変則) を、
現行 3 階層 (`output/{YYYYMMDD}/{YYYYMMDD_HH}/{ts}_{provider}_{form}_num{NNN}/`) に寄せるためのワンショットツール。

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
- リポジトリメモリ ([`/memories/repo/conventions.md`](../#)) に変更要旨を 1 行追記する。
- 既存生成への影響範囲が広いので、本番バッチ前に **1 キャラだけ単発生成** して `prompt.txt` の `[形態共通データセット]` 出力を目で確認する。

### 実装参照

- ローダー: `src/utils/dataset.py` の `_load_form_common_dataset()` (`@lru_cache`)
- 差し込み: `src/utils/dataset.py` の `_build_form_common_dataset_block()`

---

## 4. リファレンス参照画像の解決

`src/utils/dataset.py` の `collect_reference_images()` が以下を統合する。

1. `ai_hints.*.reference_images[]` (AI 学習データ由来)
2. レコードの `images[]` (DB 由来)
3. `work_common.reference_images.{corefolder_reference[], humanoid_reference[]}` (作品共通設計図 `cnsp-fg_NTsCoreFolder.png` 等)

### URL → ローカル変換

`_collect_work_common_reference_images()` 内で
`https://database.numbertales-radiann.net/` → `_creations-db/` 変換を試み、
ローカルにあれば実バイトで Gemini に渡せるようにしている。
これにより、ネット越し DL を待たずに `Part.from_bytes` で確実に添付できる。

---

## 5. 創作 DB パッケージ参照の制御

env `CREATIONS_DB_PACKAGE_ENABLE` で動作切替。

| 値                    | 動作                                                           |
| --------------------- | -------------------------------------------------------------- |
| 未設定 / `1`          | `_creations-db/pkg/` 配下のパッケージレイヤを使う (デフォルト) |
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
