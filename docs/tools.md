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

# 5. パイプラインのステージ配下にネストした日付フォルダもフラット化する
python -m src.tools.migrate_output_layout --flatten-stages --dry-run
python -m src.tools.migrate_output_layout --flatten-stages

# 6. ステージ配下のフラット化のみ (トップレベル整形はスキップ)
python -m src.tools.migrate_output_layout --stages-only --dry-run
```

### ステージ配下再帰フラット化 (`--flatten-stages` / `--stages-only`)

パイプラインは各ステージ (`stage3_rough/` / `stage4_correct/rough_NN_corrected/` /
`stage5_final/` / `stage5_final/synth/` など) 配下の子生成を、日付フォルダを作らない
*フラット* 形式 (`{stage}/{ts}_{provider}_{form}_num{NNN}/`) で置く (`build_run_output_dir(date_group=False)`)。
旧実装ではステージ配下にも日付フォルダを掘っていたため、古い実行には
`.../{stage}/{date}/{date}_{HH}/{run}/` (旧 3 階層) や `.../{stage}/{date}/{run}/` (旧 2 階層) が
残っている。このモードはそれらの run を 1 つ上へ引き上げてフラット化し、空になった中間日付フォルダと
`.DS_Store` 等の不要ファイルを掃除する。トップレベルの `{作業日}/` は温存する。

- `--flatten-stages`: トップレベル整形に加えてステージ配下も処理する (両パスを順に実行)。
- `--stages-only`: トップレベル整形を行わず、ステージ配下のフラット化のみ実行する。

### 注意

- dry-run で **warnings がゼロ** であることを確認してから本実行する。
- 既に新レイアウトに収まっている run は触らない (idempotent)。
- 一度本実行したら、再度走らせても何も移動しない設計 (ステージ配下フラット化も同様)。
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

### キャラクターの同定 — インデックスバッジ命名 (2026-08-02 追従)

上流 creations-db が画像ファイル名の識別子を **インデックスバッジ** 体系へ一括改名した
(NumberTales 574 件。上流ログ `_work_in_progress/2026-08-02_progress_image-rename-index-badge.md`)。

```
{prefix}_{kind}{Works_Code}-{バッジ本体}{接尾辞}

cnsp_img57.png          →  cnsp_imgNTS-57.png
cnsp_img2-alt.png       →  cnsp_imgNTS-2B.png
attr_numberMark10alt.png →  attr_numberMarkNTS-10D.png
art_img56,65-corefolderA.png → art_imgNTS-56,NTS-65-corefolderA.png   (連名)
```

| 要素          | 取得元                                                                       |
| ------------- | ---------------------------------------------------------------------------- |
| `Works_Code`  | `data/db_meta.json` の `CreationWorks.<work_key>.Works_Code` (NumberTales = `NTS`) |
| `バッジ本体`  | 作品別 `db_type.json` の `$IndexDef.$badge`。NumberTales は `Num_Badge` 優先・無ければ `Num` |
| `接尾辞`      | `-humanoid` / `-1` / `RZ` (旧 `-numberize`) / `MP` (旧 `-mp`) など。改名では touch されていない |

**`Num` とバッジ本体は一致しないことがある。** `2-alt` → `2B` / `10-alt` → `10D` /
`67-old` → `67B` / `67` → `67A`（旧ファイル名の A/B とバッジの A/B は逆転していたのがバッジ側を正として解消された）。

そのため `_looks_like_target_character()` は **ファイル名からバッジを読み取ってレコードのバッジと厳密一致** させる。
バッジ本体と接尾辞の間に区切り文字が無いため、切り出しは作品内バッジ語彙との **最長前方一致**
(`_load_badge_vocabulary()` / `_badge_tokens_in_filename()`) で行う。`NTS-2B` を `2` と読むと
2(ツグ) と 2-alt(バイナ) が混ざり、`NTS-57RZ` を `57RZ` と読むと 57 の numberize 版を取りこぼす。

> 逆向き（バッジからファイル名を組み立てる）は実装しない。接尾辞と連名が復元できないため、
> 上流も同じ理由で実装を持たない。DB の `images` に書かれた実名を正とする運用は変わらない。

バッジを解決できないファイル名（`art_numbertalesAniv2nd.png` のようなイベント年月ベース命名）の扱いは呼び出し文脈で分かれる。

| 収集経路                                  | `require_badge` | バッジ不明時の扱い                                     |
| ----------------------------------------- | --------------- | ------------------------------------------------------ |
| レコードの `images` (DB が紐付け済み)     | `False`         | 旧命名の部分一致へフォールバック（後方互換）           |
| `_collect_forced_local_images()` の総当たり | `True`          | **採らない**。同定できないパスは他キャラの混入源になるため |

### URL → ローカル変換

`_collect_work_common_reference_images()` 内で
`https://database.numbertales-radiann.net/` → `_creations-ai/creations-db/` 変換を試み、
ローカルにあれば実バイトで Gemini に渡せるようにしている。
これにより、ネット越し DL を待たずに `Part.from_bytes` で確実に添付できる。

### 回帰テスト

`tests/test_badge_reference_images.py`（`python tests/test_badge_reference_images.py` で単体実行可）。
最長前方一致・接尾辞の除外・連名・`require_badge` の分岐に加え、
全キャラの参照画像に他キャラのバッジが混入しないことを実データで検証する。

---

## 5. 創作 DB パッケージ参照の制御

env `CREATIONS_DB_PACKAGE_ENABLE` で動作切替。

| 値                    | 動作                                                           |
| --------------------- | -------------------------------------------------------------- |
| 未設定 / `1`          | `_creations-ai/creations-db/pkg/` 配下のパッケージレイヤを使う (デフォルト) |
| `0` / `false` / `off` | 無効化。 raw JSON だけを読む                                   |

通常は触らない。デバッグや上流改修時の動作切り分けで使う。

---

## 6. AppearanceDetail 照合レビュー (`verify_appearance_detail`)

創作 DB の `AppearanceDetail` に書かれた各仕様行が、**同じ DB に登録された公式イラスト**と
食い違っていないかを OpenAI Vision で 1 行ずつ照合し、レビュー Markdown を生成する。
`_creations-ai/creations-db/` は read-only 扱いのため、指摘は直接編集ではなく
[100BeautiesLab_CreationsDB](https://github.com/radiann-kswg/100BeautiesLab_CreationsDB) の Issue として送る。

検査は 2 種類あり `--check` で切り替える。

| `--check` | 問い | 出力 |
| --- | --- | --- |
| `match`（既定） | DB の記述は公式イラストと合っているか | `{日付}_appearance_num{NNN}_{form}.md` |
| `coverage` | 配色検知ツールが動くだけの情報が揃っているか | `{日付}_coverage_num{NNN}_{form}.md` |

### コマンド

```bash
# 生成のみ (既定・副作用なし)。_ideas/db-reviews/ に Markdown を書き出す
python -m src.tools.verify_appearance_detail --num 57 --form corefolder

# 両形態を続けて照合 (Formation=null の共通エントリは両方で検査される)
python -m src.tools.verify_appearance_detail --num 57 --form both

# 配色検知ツール向けの充足性検査 (BodyPart / DesignElement の不足を洗い出す)
python -m src.tools.verify_appearance_detail --num 57 --check coverage --form both

# 作品内の AppearanceDetail 保有レコードを一括検査し、1 枚のレビューへまとめる
python -m src.tools.verify_appearance_detail --all --check coverage

# 既存 Issue へ「Attrs 色情報の補完案」をコメント追記する (LLM 不使用)
python -m src.tools.verify_appearance_detail --all --check coverage --comment 20 --submit

# レビューを Issue として送る (form ごとに 1 Issue)
python -m src.tools.verify_appearance_detail --num 57 --form both --submit
```

### フラグ

| フラグ | 既定 | 説明 |
| --- | --- | --- |
| `--num` | — | キャラクター番号。`2-alt` のような特殊 ID も可（`--all` と排他・どちらか必須） |
| `--all` | off | 作品内の `has_appearance_detail` 全レコードを一括検査（`--check coverage` 専用） |
| `--check` | `match` | `match` = 記述と画像の照合 / `coverage` = 配色検知ツール向けの充足検査 |
| `--form` | `corefolder` | `corefolder` / `humanoid` / `both` |
| `--max-images` | `3` | Vision へ渡す公式画像の枚数。枚数が少ないと全身資料が入らず `unclear` が増える |
| `--comment <番号>` | — | 新規 Issue を立てず、既存 Issue へ**色情報の補完案**をコメント追記（`--all` 用） |
| `--workers` | `4` | 一括の画像読み取りの並列数 |
| `--reuse-detections` | off | 同日の `.detections.json` があれば画像読み取りを再利用（レポート手直し用・課金なし） |
| `--before-missing <件数> <キャラ数>` | — | 前回の BodyPart 欠落数。補完の効果を提案コメントへ載せる |
| `--submit` | off | Issue を送る／追記する。**外部投稿を伴うので明示 opt-in** |
| `--repo` | `radiann-kswg/100BeautiesLab_CreationsDB` | 送付先 |
| `--out-dir` | `_ideas/db-reviews/` | Markdown 出力先 |

### 照合に使う公式画像の選び方

作品 typedef（`data/Works_<work>/DataBases/db_type.json`）の `Images` 子要素のうち、
**`$palette: { "source": ... }` が宣言されているフィールドの画像**を使う。配色抽出の入力に選ばれている画像は
キャラの色と造形が正確に描かれた資料（設定原画・設定資料・コアフォルダ画像）で、照合の根拠として最も強い。
creations-db 側の `tools/extract-palette.mjs` の `listImageFields()` と同じ考え方で、
フィールド名をこちらのコードに書かないための入口になっている。

- NumberTales の対象: `concept_PNGName`（設定原画）/ `catalog_PNGName`（設定資料）/ `corefolder_PNGPath`（コアフォルダ画像）
- 他形態専用と判る画像（`corefolder` 照合における `/humanoid` 配下など）だけを除外する。
  設定資料のような形態非依存の資料は両形態の照合に使う。
- `$palette.source` 宣言が無い作品では `collect_reference_images()`（生成側と同じ参照画像）へ自動フォールバックする。
  どちらを使ったかはレビュー冒頭の「画像の選定」行に記録される。

### 判定の読み方

| verdict | 意味 |
| --- | --- |
| `match` | 画像から仕様どおりだと確認できた |
| `mismatch` | 画像が仕様と明らかに異なる（位置・色・数・形状） |
| `unclear` | 画角・遮蔽・解像度・未描画で**確認できない**。「DB が誤り」の意味ではない |

### 充足性検査 (`--check coverage`) が見るもの

配色検知ツール（creations-db `tools/patch-colorpalette.mjs`）は、`AppearanceDetail` の**色語**から
`ColorPalette.AppliesTo`（その色がどの部位か）を転記する。したがって色語を含むエントリに
`BodyPart` が無いと、検出した色を部位へ紐づけられない。この検査はその不足を洗い出す。

判定は上流 `tools/extract-palette.mjs` の `collectColorHints()` / `colorWordMatchesHex()` を
**node 経由でそのまま呼ぶ**（色語表 `COLOR_WORD_RANGES` をこちらへ再実装しない。policy と同じ方針）。

| 節 | 内容 | 意味 |
| --- | --- | --- |
| 1. BodyPart 欠落 | 色語はあるのに `BodyPart` が空のエントリ | **最優先。** `AppliesTo` へ転記できない |
| 2. 根拠なし ColorPalette | 対応する色語が 1 つも無い HEX | その色がどの部位か決められない |
| 3. 色語ヒント 0 のエントリ | 色語表に載る語を含まないエントリ | 形状のみの記述なら正常。`blonde` / `amber` のような未対応色語の発見に使う |

1 と 2 については、公式画像から `$EnumDef_DesignBodyPart` のコードで**部位候補を提案**する（半自動の下書き）。
一覧に無いコードを返してきた場合は捨てるので、そのまま DB へ貼れる形になる。不足が 0 件のときは Vision を呼ばない。
画像が無くても静的検査だけは実行する。

### 一括検査 (`--all`)

作品内の `has_appearance_detail` 全レコード（NumberTales で 111 件）を検査し、**1 枚のレビュー**へまとめる。
各レコードは単体実行と同じ fail-closed ゲートを通る。形態では絞らない（欠落は形態に依らないため）。

- 色語ヒント取得の node 呼び出しは **1 プロセスにまとめる**（レコードごとに起動すると起動コストで数十秒かかる）。
- 節 1 は**色語表に無い色語の頻度表**。色語ヒント 0 の記述からユニーク文字列だけを LLM へ渡して
  色を指す語を抽出する（画像は使わない）。`COLOR_WORD_RANGES` へ何を足すべきかの優先順になる。
- 個別キャラの部位候補（画像からの提案）は一括では出さない。`--num <N> --check coverage` を使う。
- 色語の抽出は実行のたびに結果が揺れる（LLM 判定のため）。`bright`（表情の明るさ）のような
  色ではない語を拾うこともあるので、そのまま色語表へ入れず内容を確認すること。

### `Attrs` 色情報の補完案 (`--comment`)

`--comment <Issue番号>` を付けると、レビュー全文ではなく**補完案だけ**を組み立てて既存 Issue へ追記する。

**色の根拠は公式画像に置く。** `ColorPalette` の HEX は配色検知ツールが画像から起こした出力であり、
いま補完しようとしている対象そのもの。HEX から色語を逆引きすると不完全な値を根拠に記述を書くことになり、
誤りを自己肯定してしまう。したがって色語は typedef `$palette.source` 宣言画像（設定原画・設定資料・
コアフォルダ画像）から Vision で読み取る。

| 節 | 内容 |
| --- | --- |
| 補完案 | 色情報が無いエントリについて、画像から読んだ色語と `#DesignAttr_Color` の追記案 |
| 創作 DB に無い配色（実測 HEX） | 透過イラストから**実測**した色のうち `ColorPalette` に無いもの。**使用部位と `Attrs` 記述案つき** |
| 実測はされたが配色ではない色 | 画像照合で輪郭線・紙面と判定されたもの（参考） |
| ColorPalette に見当たらない色 | 画像から読めたのに `ColorPalette` のどの HEX も該当しない色（色語レベル） |
| 残っている BodyPart 欠落 | 部位が空のまま残っているエントリ |

実測 HEX は上流の `extractSolidColors()` / `colorDistance()` を node 経由で呼んで得る（抽出条件は
`patch-colorpalette.mjs --from-artwork` と同じ・共通造形色は除外）。対象は `$palette.source: artwork` を
宣言した透過イラストのみで、色距離 10 以内を「既存と同じ色」とみなす。

**実測 HEX は画像照合で使用部位まで特定する。** `$EnumDef_DesignBodyPart` のコードと `Attrs` へ書ける
短い英語記述を返させるので、`ColorPalette.AppliesTo` と `AppearanceDetail[].Attrs` の両方へそのまま書ける。
上流の純黒除外は彩度条件付き（濃い有彩色を守るため）で `#010000` のような輪郭線がすり抜けるが、
画像照合が「配色ではない」と判定したものは別表へ回るので、追記候補の表には混ざらない。

色語の読み取りと部位の特定は**同じ 1 コール**にまとめる（同じ画像を 2 回送ると費用が倍になるだけなので）。

「見当たらない色」からは**共通造形色**（`$EnumDef_CommonColor` の肌色・舌色・毛色など）に該当する色語を除外する。
これらは設計上 `ColorPalette` へ載らないため、指摘すると誤検出になる。除外語は上流 `readCommonColors()` から取る。

- モデルには**色語表の語だけ**を選ばせ、一覧外の語は捨てる。「提案どおり書いたのに拾われない」を防ぐため。
- 一括では形態で絞らず `$palette.source` 画像を最大 `--max-images` 枚渡す（設定資料に両形態が載っているため）。
- API 待ちが支配的なので `--workers`（既定 4）でスレッド並列。1 キャラの失敗は警告のみで全体を止めない。
- 色語 key の一覧と日本語ラベルだけはこちらに持つ（`ponytail:` コメント付き）。判定は常に上流。
  上流が語を増やしたら追記が要るが、漏れても提案が出ないだけで誤った提案は出ない。

- 判定は AI の推定。`mismatch` は先輩の目視確認を前提とした指摘候補として扱う。
- モデルが返さなかった行は握り潰さず `unclear` として残る（件数が黙って減らないようにするため）。
- 前提: `OPENAI_API_KEY`（モデルは `GPT_MODEL`、既定 `gpt-4o`）、`--submit` 時は `gh auth login` 済みであること。
- 生成入口と同じ fail-closed オプトアウトゲート（`apply_generation_gate(usage="image")`）を通す。
- 実装: [src/tools/verify_appearance_detail.py](../src/tools/verify_appearance_detail.py) /
  回帰テスト: [tests/test_appearance_detail_review.py](../tests/test_appearance_detail_review.py)

---

## 7. 今後ツールを追加するときの規約

新ツールを `src/tools/` に置く場合:

1. `python -m src.tools.<name>` で実行できるよう `argparse` ベースで書く。
2. デフォルトで **副作用なし** (dry-run 相当) になるようにする。書き換え系は `--fix-*` や明示フラグで opt-in。
3. CI 連携を想定するなら `--strict` (exit 1) と `--json` (機械可読) を揃える。
4. **必ずこの `docs/tools.md` に節を追加する** 。コマンド例 + フラグ表 + 主要オプションの説明を最小セット。
5. **AGENTS.md** のクイックリファレンスにも 1 行載せる（共通仕様の正典はここだけ。薄い設定書には重複させない → [`agent-config.md`](agent-config.md)）。

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
