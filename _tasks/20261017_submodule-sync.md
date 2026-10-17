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

