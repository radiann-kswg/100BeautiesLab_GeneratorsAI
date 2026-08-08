# サブモジュール同期ログ — 2026-08-08 15:06

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | de701b9 | 39cf109 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 892a91c | 892a91c | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` de701b9..39cf109

```
39cf109 chore: sync ai-dataset (creations-db@892a91c) 窶・ai_training allowed: 157 -> 158 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        | 16 +++++++--------
 ai-dataset/image-index.json                       |  9 ++++----
 ai-dataset/index.json                             | 10 ++++-----
 ai-dataset/manifest-training.jsonl                | 13 ++++++------
 ai-dataset/manifest.jsonl                         | 25 +++++++++++++----------
 ai-dataset/policy.json                            |  2 +-
 ai-dataset/works/Works_CommonReferences.json      |  2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |  2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |  2 +-
 ai-dataset/works/Works_NumberTales.json           | 13 +++++++++++-
 ai-dataset/works/Works_PastDivers.json            |  2 +-
 ai-dataset/works/Works_ShouArRiders.json          |  2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |  2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |  2 +-
 ai-dataset/works/Works_UnibyteLive.json           |  2 +-
 ai-dataset/works/Works_VirtuesUs.json             |  2 +-
 creations-db                                      |  2 +-
 17 files changed, 62 insertions(+), 46 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

### 差分レビュー結果 (2026-08-08 / Claude Code)

上流の変更は `ai-dataset/` の再生成のみ。`scripts/` ・ `lib/policy.js` に変更なし
(`git diff --name-only de701b9 39cf109` で確認)。**追従が必要だったのは 1 点のみ。**

| 差分 | `src/` への影響 | 判定 |
|---|---|---|
| 新キャラ `1000`(チヨ) / `1111`(アイデン) / `1122`(ネコマ) 追加 (SelfSecondary) | `has_ai_hints=False` かつ非 Primary。`get_characters()` にも `natural_parser._build_name_lookup()` (db_Primary.json 限定) にも乗らない | 追従不要 |
| `888` (SemiPrimary) の `ai_training.allowed` false→true (許可 157→158) | 同上。`has_ai_hints=False` で、`find_character()` / `_fetch_record_via_api()` は共に `db_name="Primary"` 固定のため生成経路へ到達しない。上流が SemiPrimary へ `ai_hints` を入れた時点で初めて対応が要る | 追従不要 |
| `AnotherVersions_DBLink` → `VariantModels_DBLink` 改名、`SameMPSeries_DBLink` 新設 | `src/` 全体を grep して参照 0 件 | 追従不要 |
| `888-mp` / `999-mp` の改名 (`量産型 888(ムゲン)` → `888(ヤバヤ)` 等) と `TailsUnit` 付与 | 別名辞書は `Name_JP` から実行時に構築する方式でハードコード無し | 追従不要 |
| レコード `99` (Primary・生成対象) の AppearanceDetail へ `BodyPart: Waist / Leg` 付与 | `_extract_appearance_detail_motif_en()` は `#DesignAttr_Overview.value_EN` のみ読み `BodyPart` を参照しない | 追従不要 |
| **`#TailShapeType_BirdTailOnly` が新登場 (0 → 3 件: 888 / 999 / 1111)** | **`src/utils/dataset.py` の `_TAIL_SHAPE_TYPE_LABELS` に未収録** → `_describe_tails_unit_entry()` が `("", "")` を返し、尾の形状ラベルが黙って消えて本数・節数だけ残る | **要追従 → 対応済み** |

**対応内容**

- `_TAIL_SHAPE_TYPE_LABELS` に `#TailShapeType_BirdTailOnly` を追加
  (ラベルは `creations-db/data/Works_NumberTales/DataBases/db_meta.json` の
  `$EnumDef_TailShapeType` から引き写し)。
- 根本対処として、未知の `TailShapeType` を既存ヘルパー `_hashtag_fallback_label()` で
  可読ラベルへ落とすよう変更。`_BODY_PART_LABELS` / `_COLOR_ROLE_LABELS` が既に採っている
  方針に揃え、今後の上流の列挙値追加でデータが黙って消えないようにした
  (実例: `#BodyPart_Halo` も未収録だが同ヘルパー経由で "halo" と出ており破綻していない)。
- 回帰テスト `tests/test_tails_unit_labels.py` を追加。
- `Laterality` / `ColorRole` の使用値は manifest 実データと突き合わせて欠落ゼロを確認済み。
- `docs/` は更新なし (AGENTS.md「更新対応表」のどの行にも該当せず。CLI フラグ・出力階層・
  環境変数・プロンプトブロック構造・スキーマのいずれも変更していない)。

