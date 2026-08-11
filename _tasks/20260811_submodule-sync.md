# サブモジュール同期ログ — 2026-08-11 16:52

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 279b14b | 032bdb8 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 6e4f3e2 | 6e4f3e2 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 279b14b..032bdb8

```
032bdb8 chore: sync ai-dataset (creations-db@6e4f3e2) 窶・ai_training allowed: 158 [skip ci]
0a824bd chore: sync ai-dataset (creations-db@801ac6d) 窶・ai_training allowed: 158 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |   4 +-
 ai-dataset/image-index.json                       |   2 +-
 ai-dataset/index.json                             |   4 +-
 ai-dataset/manifest-training.jsonl                | 226 +++++++--------
 ai-dataset/manifest.jsonl                         | 322 +++++++++++-----------
 ai-dataset/policy.json                            |   2 +-
 ai-dataset/works/Works_CommonReferences.json      |   2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |   2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |   2 +-
 ai-dataset/works/Works_NumberTales.json           |   2 +-
 ai-dataset/works/Works_PastDivers.json            |   2 +-
 ai-dataset/works/Works_ShouArRiders.json          |   2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |   2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |   2 +-
 ai-dataset/works/Works_UnibyteLive.json           |   2 +-
 ai-dataset/works/Works_VirtuesUs.json             |   2 +-
 creations-db                                      |   2 +-
 17 files changed, 291 insertions(+), 291 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

### 追従レビュー (2026-08-11, Claude Code)

上流 `creations-db` の大幅な DB 見直し（`0629b5e..6e4f3e2`: 「DB情報推敲(配色周り) その1〜8」
「DB情報推敲(外見情報)」「AIHints 構造的再同期」/ 67 files, +36094 -4123）に対する `src/` 追従判定。

**同期状態**: `_creations-ai` = `032bdb8` / `creations-db` = `6e4f3e2` で追跡ブランチと一致。追加取り込みなし。

**上流の変更の本体**: `AIHints` の構造的再同期と大量充填。

| 観点 | 旧 | 新 |
|---|---|---|
| `AIHints` 保有レコード (`Works_NumberTales/db_Primary`) | 0 | 92 |
| `AIHints` 配下のキーパス | — | 消滅 0 / 追加 74 |

**判定: `src/` の追従は不要。** 根拠:

1. **typedef は明文化のみ。** `db_type.json` の差分は `$Def_AIHints` 系の定義追加だけで、削除行は末尾の `}` のみ。
   構造 (`common` / `forms.{corefolder,humanoid}` / `work_common`) は `src/utils/dataset.py` が既に読んでいるものと一致。
2. **上流ツールの破壊的変更に触れていない。** `tools/extract-palette.mjs` で
   `resolveImageSources(record, imagesRoot)` → `(record, workDir, imagesRoot)` と引数が増えたが、
   `src/tools/verify_appearance_detail.py` が import するのは
   `collectColorHints` / `colorWordMatchesHex` / `readCommonColors` / `decodePng` /
   `extractSolidColors` / `isTransparentArtwork` / `colorDistance` の 7 つで、いずれも export 健在。
3. **API は二系統併存で現行の使い分けが有効。** `/api/v1/*` は `develop` の worker `creationsdb-api` が継続提供、
   `/api/ai/*` は `addon-ai-tag` の新 worker `creationsdb-api-ai`（`wrangler.toml` の routes を分離）。
   `src/utils/dataset.py` は records を `/api/v1`、aihints を `/api/ai` へ振り分けており（1310 行の置換）、そのまま通る。
   新設の `GET /api/ai/:work/:db/aihints` 一覧は現状 src で不要。
4. **新規トップレベルキーは参照不要。** `_meta`（provenance: `structuralSourceHash` 等）と `alt_modes`（将来予約）、
   `concept_contains_forms`（上流 `docs/ai-hints-usage.md` がスキーマ外キーとして保持のみを規定）。
5. **`reference_images` の動的キー追加に自動追従。** `forms.humanoid.reference_images` に `B` / `CastOff` / `OnMask` が
   増えたが、`dataset.py:745` が `.values()` で総なめするため取りこぼさない。
6. **`silhouette_notes` は dict / list の両形式に対応済み**（`dataset.py:1477-1488`）。
   上流が corefolder の装備情報を `attached_items` へ構造化した分も拾える。

**実機検証**:

- `python -m src.batch_generate --nums 57,25 --forms both --provider gemini --dry-run` → 4/4 RUN、
  `hints_forms=['corefolder','humanoid']`、`db_img` 全 True。
- `python -m src.tools.verify_appearance_detail --num 57 --check coverage --form both` → 両形態とも **BodyPart 欠落 0 件**
  （従来の指摘が上流へ反映済み）。残るは根拠なし色 1 色 / 色語ヒント0 2 件。
- 回帰テスト 4 本すべて PASS（`test_ai_optout_gate` 9/9・`test_badge_reference_images` 10/10・
  `test_tails_unit_labels` 3/3・`test_appearance_detail_review` OK）。

**申し送り**:

- `#25 corefolder` の `outfit(1->0)` は `_filter_corefolder_outfit_features()` が humanoid 衣装語を除いた
  意図どおりの挙動。corefolder 側の装備記述は上流が `silhouette_notes.attached_items` に持つ形へ移行しており、
  プロンプトはそちらから供給される。
- 上流の `npm test` はこの環境に `node_modules` 未導入のため未実行（vitest 不在）。DB 側の検証は上流 CI に委ねる。

