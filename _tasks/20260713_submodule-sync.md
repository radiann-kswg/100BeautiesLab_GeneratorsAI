# サブモジュール同期ログ — 2026-07-13 16:02

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 736fd57 | 9186681 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 53e4c12 | 53e4c12 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 736fd57..9186681

```
9186681 Merge branch 'master' of https://github.com/radiann-kswg/100BeautiesLab_CreationsAI
b1265cb chore: sync creations-db submodule to latest commit 53e4c12 chore: add GitHub triage logs for unresolved issues on 2026-06-24, 2026-06-25, and 2026-07-13
d615afd chore: sync ai-dataset (creations-db@53e4c12) [skip ci]
a253f98 chore: sync ai-dataset (creations-db@adeb7ff) [skip ci]
f9911a4 chore: sync ai-dataset (creations-db@2a9315b) [skip ci]
94bd8e9 chore: sync ai-dataset (creations-db@4dd7eb3) [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |  10 +-
 ai-dataset/image-index.json                       |  33 +--
 ai-dataset/index.json                             |   8 +-
 ai-dataset/manifest-training.jsonl                |  87 ++++++--
 ai-dataset/manifest.jsonl                         | 240 +++++++++++-----------
 ai-dataset/policy.json                            |   2 +-
 ai-dataset/works/Works_CommonReferences.json      |   2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |   5 +-
 ai-dataset/works/Works_FLInvestigator78.json      |   2 +-
 ai-dataset/works/Works_NumberTales.json           |  49 +++--
 ai-dataset/works/Works_PastDivers.json            |   2 +-
 ai-dataset/works/Works_ShouArRiders.json          |   2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |   2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |   2 +-
 ai-dataset/works/Works_UnibyteLive.json           |   2 +-
 ai-dataset/works/Works_VirtuesUs.json             |   2 +-
 creations-db                                      |   2 +-
 17 files changed, 266 insertions(+), 186 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

---

## 差分レビュー結果 (2026-07-13 / Claude Code)

`creations-db` a5683c5..53e4c12 と、それを取り込んだ `ai-dataset` 再生成分をレビューした。
結論: **`src/` 側の追従修正は不要**。

| 変更 | 内容 | `src/` への影響 | 判定 |
|---|---|---|---|
| `VRMs` フィールド新設 | `db_type.json` に `VRMs.corefolder_VRMPath` (`#VRMFilePath[]`) を追加。キャラ 4 / 16 / 20 / 25 に `.vrm` + プレビュー `.png` | プロンプト本文は `build_gemini_prompt()` / `build_dalle_prompt()` の**明示列挙 (ホワイトリスト) 方式**のため、新フィールドは自動では乗らない。実資産は `data/{work}/VRMs/` 配下で、参照画像収集 `_collect_forced_local_images()` が走査する `data/{work}/Images/` の外。`record["images"]` にも VRM は載らない | 影響なし |
| AI 学習許可 DB の入替 | `allowed_db_keys` が `#DB_SelfSecondary` → `#DB_SemiPrimary`。`AI_Optout` の false 化に伴い許可キャラが 149 → 211 | src/ の生成フィルタは `_type == "character"` かつ `has_ai_hints` のみ (`AI_Optout` / `AI_Output` はコード参照ゼロ)。manifest 再生成で新キャラ (100 / 111 / 222 / 444 / 666 / 777 / 3x11 系) が自動的に対象入り | 追従不要 (自動反映) |
| 画像パスの改名・移動 | `attr_numbertMark666-lot` → `attr_numberMark666-lot` (typo 修正)、`cnsp_img222` / `cnsp_img777` の A/B 分割、`attr_emblem3x11-doubleBrooch` の `attr/emblem/` への移動 ほか | src/ に画像パスのハードコードは無く、参照画像はすべて DB レコード経由 | 追従不要 (自動追従) |
| `AppearanceDetail` 推敲 | `DesignElement` の付け替え (`#Element_Motif` → `#Element_BodyType` / `#Element_CostumeItem`)、`Formation` の `corefolder` → `null` (両形態共通化)。`with_appearance_detail` 97 → 111 | 構造・列挙値の変更ではなくデータ推敲。`Formation: null` は既に「両形態共通」として扱う実装 (`_extract_appearance_detail_motif_en()` ほか) | 追従不要 |
| `#Dict_Costume` の辞書登録 | `Dictionaries/db_meta.json` に `#Dict_Costume` (keyField: `Costume`) を追加。辞書実体 `dict_Costume.json` 自体は既存 | src/ の `--costume` は DB フィールド非依存のフリーテキストで、Stage 1 の LLM リファイン時にのみ注入される (`prompt_refiner.py::_user_message()`)。DB の `Costume` を読む処理は無い | 影響なし (将来の連携余地) |
| `dict_Class` のラベル変更 | 「マスタートリプル(量産販売型)」→「量産型マスタートリプル」 | src/ に当該文字列のハードコードは無い | 影響なし |

### 動作確認

`find_character()` → `collect_reference_images()` をキャラ 25 / 16 / 57 の両形態で実行し、
参照画像 (`local_paths`) に `.vrm` および VRM プレビュー PNG が 1 件も混入しないことを確認した (課金なし・関数呼び出しのみ)。

### 申し送り (今回は未対応)

- `collect_reference_images()` の `record["images"]` 経由には拡張子フィルタが無い (拡張子ガードは `_collect_forced_local_images()` の `allowed_suffixes` のみ)。現状は DB 側が `Images/` と `VRMs/` を分離しているため実害ゼロだが、将来 `image-index.json` や `images` に非画像アセットが載ると `mimetypes.guess_type()` が `image/png` へフォールバックして API 400 を招く。上流が分離を崩した場合は `_allow_path()` に拡張子ホワイトリストを追加すること。
- `natural_parser.py` の名前→番号辞書は `db_Primary.json` の直読みのため、今回 AI 許可対象へ入った SemiPrimary 系キャラ (111 / 222 / 444 / 666 / 777 / 3x11 等) は自然文 (`--natural`) では名前解決できない。番号指定 (`--num` / `--nums`) は manifest 経由で解決可能。

## Cowork レビュー結果 (2026-07-13 / Claude Cowork・イズナ)

GitHub コネクタ (読み取り) でリモート HEAD を確認し、ローカルのサブモジュール HEAD と照合した。

| 対象 | ローカル HEAD | リモート HEAD | 判定 |
|---|---|---|---|
| `_creations-ai` (origin/master) | `9186681` | `9186681` | 完全一致・遅れなし |
| `_creations-ai/creations-db` (origin/addon-ai-tag) | `53e4c12` | `53e4c12` | 完全一致・遅れなし |

実機スクリプトが取り込んだ後にリモートがさらに進んだ形跡はなく、次回同期待ちの更新も無い。

### 独立検証 (課金なし・grep のみ)

同日 16:12 の Claude Code 差分レビュー結論「`src/` 追従修正は不要」を、Cowork 側でも独立に確認した。

- 今回 87 行変わった `manifest-training.jsonl` は、`src/utils/dataset.py:762` で「学習許可済みサブセット。生成では使用しない」と明記されており、生成パイプラインからの参照はコメント 1 箇所のみ。→ 影響なし。
- 生成用途が読むのは `manifest.jsonl` (全レコード) と `has_ai_hints` / `Formation`。`Formation: null` を「両形態共通」として扱う実装 (`dataset.py:1215` / `1256` ほか) は既存で、今回の `corefolder`→`null` 推敲と整合。→ 影響なし。
- `AI_Optout` / `AI_Output` はコード参照ゼロ (コメントのみ)。許可キャラ 149→211 の増加は manifest 再生成で自動反映。→ 追従不要。

**結論: `src/` ・ `docs/` の追従最適化は不要。過剰改変を避け編集は行わない。** リモート完全同期のため実機での追加 `git` 操作も不要 (本ログ追記のみ Cowork 実施)。

### 申し送り (継続監視)

Claude Code ログ記載の 2 点 (`collect_reference_images()` の拡張子ガード不在 / `natural_parser.py` の SemiPrimary 系名前解決) は今回も未対応のまま。上流が `Images/` と `VRMs/` の分離を崩した時点で `_allow_path()` に拡張子ホワイトリスト追加が必要。現状は実害ゼロ。

---

# 追加同期 — 2026-07-13 (第2回 / `ColorPalette` 新設への追従)

上記レビュー完了後、上流がさらに進んだ。**今回は「追従不要」ではなく `src/` 側の実装追従が必要**だったため、
そのまま適応まで実施した。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 9186681 | 81a6ee9 | UPDATED | ai-dataset 再生成 2 コミット |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 53e4c12 | b8c989b | **UPDATED (構造変更)** | 10 コミット。`db_Primary.json` が +13663 行 |

## 取り込んだ更新の内容

`creations-db` は **配色情報 (`ColorPalette`) の新設** が本丸。

| 変更 | 内容 |
|---|---|
| **`ColorPalette` スキーマ新設** | `db_type.json` に `ColorPalette` (`$Def_ColorPalette[]\|#Null`, `$display.section: profile`)、`db_meta.json` に `$Def_ColorPalette` (`Role`/`Hex`/`ColorName_JP`/`ColorName_EN`/`AppliesTo[]`/`Formation`/`Note_JP`/`Note_EN`) と `$EnumDef_ColorRole` (`#ColorRole_Primary`/`Secondary`/`Accent`/`Sub`) を追加 |
| **実データ投入** | 設定画 (concept/catalog) に作者が描き込んだ**カラーチップの実測値**を NumberTales/Primary の **94 件**へ投入。全件 5 色以上 (Primary/Secondary/Accent 各 94 + Sub 259 エントリ)。`AppliesTo` は既存の `$EnumDef_DesignBodyPart` を再利用 |
| **`palette_priority` の機械導出** | AIHints の `common.palette_priority` を `ColorPalette` から導出 (`--apply-colorpalette`)。従来 **92 件すべて `null`** → **91 件で 3 色確定** |
| **AIHints に `_meta` (provenance)** | `structuralSourceHash` / `structuralEntries` / `lastStructuralResync`。`--resync-structural` と `--force` の破壊防止用 |
| ツール群 | `tools/extract-palette.mjs` / `tools/patch-colorpalette.mjs` / `.github/workflows/aihints-structural-resync.yml` (いずれも DB 側の資産。本リポジトリからは使わない) |

## 最適化メモ — **追従実施 (差分レビュー結果 / 2026-07-13 Claude Code)**

**結論: `src/` の追従が必要だった。** 配色が「画像を目視しないと決まらない値」から「DB から再生成できる構造由来の値」へ
格上げされたのに、生成側の受け皿が古いままで**実測配色がプロンプトにほぼ届いていなかった**。

### 検出したギャップ

| # | ギャップ | 実害 |
|---|---|---|
| 1 | `build_dalle_prompt()` に配色ブロックが**一切存在しない** | OpenAI 経路 (`src.openai.generate` / Stage 1 リファインのベース) が**配色情報ゼロ**で生成していた |
| 2 | `build_gemini_prompt()` の `[パレット参考]` が `palette_priority` の 3 スロット (裸 HEX) のみ | **Sub 色 259 エントリ**と、**`AppliesTo` (どの色がどの部位か)** を丸ごと捨てていた。プロンプト末尾配置で重みも弱い |
| 3 | Stage 2 の `character_spec` に配色が無い | Stage 4 の違反分析が色を知らず、**「配色が違う」を違反として検出・修正できなかった** |

### 実施した追従

- **`src/utils/dataset.py`**: `extract_color_palette(record, form)` / `_format_color_palette_lines()` / `_build_color_palette_block()` を新設。
  `Formation` が対象 form または `null` (両形態共通) のエントリのみを採り、Role を 主色 → 補助色 → 差し色 → 副色 の順に整列 (副色は最大 4 件)。
  `Hex` は DB の `#Hexcode_Color` 型 (`#RRGGBB` / `#RRGGBBAA`) で検証し不正値を捨てる。列挙値ラベル (`_COLOR_ROLE_LABELS` / `_BODY_PART_LABELS`) は
  既存の `_APPEARANCE_DETAIL_*` 系と同じハードコードマップ方式に揃え、**未知の列挙値はハッシュタグから機械的にラベル化**して欠落させない
  (上流が `#BodyPart_*` を増やしても壊れない)。
- **`[配色仕様 (DB実測値・遵守すること)]` ブロックを Gemini / DALL-E の両ビルダーへ注入**し、`[識別記号]` の直後へ配置。
  旧 `[パレット参考]` は本ブロックへ統合・置換 (削除)。`ColorPalette` 不在時は `palette_priority` の 3 スロットへフォールバックし、
  いずれも無ければブロックごと省略する (他作品・未整備レコードでの非破壊性を担保)。
- **`src/pipeline/db_collector.py`** (Stage 2): `character_spec.color_palette` を追加 (`db_summary.json` に自動記録)。
- **`src/pipeline/correction_generator.py`** (Stage 4): 違反分析へ配色照合を追加。**明らかな色相ズレのみ違反**とし、
  陰影・ハイライト・照明差は違反としない (正常な絵を誤検出させないため)。i2i 修正プロンプトの「維持すること」にも配色を明記。
- **`src/pipeline/prompt_refiner.py`** (Stage 1): リファイン時に HEX と適用部位を**逐語で保持**するようシステム指示を強化。
- **`docs/usage-generation.md`**: プロンプト構造表にブロック 6.8 を追加 + 追従メモを記載。

### 動作確認 (課金なし・関数レベル)

`extract_color_palette()` → `build_gemini_prompt()` / `build_dalle_prompt()` → `collect_character_data()` を
キャラ 57 (両形態) / 25 で実行し、次を確認した。

- 両ビルダーに `[配色仕様]` が出力される (57 corefolder: 主色 `#E8F152` : arm, foot / 補助色 `#FFEE62` / 差し色 `#F7FFB9` / 副色 2 件)。
- 旧 `[パレット参考]` が消えている。
- `ColorPalette` を落とすと `palette_priority` へフォールバックし、両方無ければブロックが空になる (プロンプト崩れなし)。
- Stage 2 の `db_summary.json` に `character_spec.color_palette` が記録される。
- `py_compile` / import 循環チェックとも通過。

### 申し送り

- `ColorName_JP` / `ColorName_EN` / `Note_*` は**創作内容にあたるため上流ツールも Claude も埋めない** (先輩が手入力する領域)。
  値が入れば `- 主色 #E8F152 (Izuna Yellow) : arm, foot — 補足` の形で自動的にプロンプトへ載る (実装済み・追加作業不要)。
- `Formation` は現状 **全エントリ `null`** (両形態共通)。将来 form 別配色が入っても `extract_color_palette()` が form で絞る。
- テキスト生成 (`src.pipeline.text_pipeline`) は散文・キャプション用途のため **HEX は意図的に注入しない**。
- AIHints の `_meta` (provenance) は `hints.get()` 方式の読み出しにより**素通し**。src 側の追従は不要。
- 前回からの継続監視 2 点 (`collect_reference_images()` の拡張子ガード不在 / `natural_parser.py` の SemiPrimary 系名前解決) は**今回も未対応**。
