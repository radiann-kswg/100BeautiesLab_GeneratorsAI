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

