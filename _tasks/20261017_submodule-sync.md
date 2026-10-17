# サブモジュール同期ログ — 2026-10-17 14:58

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | cbf75e5 | 8bef358 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | e396583 | e396583 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` cbf75e5..8bef358

```
8bef358 chore: sync ai-dataset (creations-db@e396583d) — ai_training allowed: 175 [skip ci]
9b8971a chore: sync ai-dataset (creations-db@544d327c) — ai_training allowed: 174 -> 175 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        | 10 +--
 ai-dataset/image-index.json                       | 11 +++-
 ai-dataset/index.json                             | 10 +--
 ai-dataset/manifest-training.jsonl                | 24 ++++---
 ai-dataset/manifest.jsonl                         | 78 +++++++++++++----------
 ai-dataset/policy.json                            |  2 +-
 ai-dataset/works/Works_CommonReferences.json      |  3 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |  2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |  2 +-
 ai-dataset/works/Works_NumberTales.json           |  2 +-
 ai-dataset/works/Works_PastDivers.json            |  2 +-
 ai-dataset/works/Works_ShauErRiders.json          |  2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json | 21 +++++-
 ai-dataset/works/Works_UnauthedLogica.json        |  2 +-
 ai-dataset/works/Works_UnibyteLive.json           |  2 +-
 ai-dataset/works/Works_VirtuesUs.json             |  2 +-
 creations-db                                      |  2 +-
 17 files changed, 107 insertions(+), 70 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。


### 追従確認 (2026-10-17 15:00 手動・Claude Code)

**判定: `src/` / `docs/` の追従変更は不要。** 根拠:

- NumberTales 側の差分は `db_SemiPrimary.json` のクロスリンク `_DB: SemiPrimary → PrimaryStabilities`（`%` / `∞` の NNE・SSW 参照）のみ。`src/` は `_DB` クロスリンクを解決しないため影響なし。
- `data/db_type.json`（ルート）の `Height_cm` / `Weight_kg` の `hashTag_JP/EN` ラベル変更は、`src/` が `hashTag_JP/EN` を参照しない（作品別 `db_type.json` の Images 順・`$IndexDef` のみ使用）ため影響なし。`Works_NumberTales/DataBases/db_type.json` は無変更。
- 豹変系女子の新 DB `#DB_PrimaryStabilities` 等の新規レコードは `Num` も `images` も無く、`natural_parser._get_chars_with_images()` の名前辞書・`get_characters()` の列挙には載らない（後者は `ai_training.allowed` でも除外）。新設の References レコード「憤怒を鎮めるイ列」は `data/References/` 由来なので `get_characters()` から外れる。
- `python -m pytest -q`: 90 passed。単独実行時の `test_badge_reference_images` の失敗は**既存のフレーク**: `10-alt` は今回の更新前から `allowed:false`（stillTentative）で、テストは実 API フォールバックに依存している。今回の差分が原因ではない。
