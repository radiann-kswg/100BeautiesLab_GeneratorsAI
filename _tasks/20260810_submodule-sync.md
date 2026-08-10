# サブモジュール同期ログ — 2026-08-10 12:58

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 39cf109 | 425cbde | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | db63018 | db63018 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 39cf109..425cbde

```
425cbde chore: sync ai-dataset (creations-db@db63018) 窶・ai_training allowed: 158 [skip ci]
8a10113 chore: sync ai-dataset (creations-db@5ccf04c) 窶・ai_training allowed: 158 [skip ci]
40b57d3 chore: sync ai-dataset (creations-db@13a189f) 窶・ai_training allowed: 158 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |  10 +-
 ai-dataset/image-index.json                       |   4 +-
 ai-dataset/index.json                             |   8 +-
 ai-dataset/manifest-training.jsonl                |  16 +--
 ai-dataset/manifest.jsonl                         | 152 +++++++++++-----------
 ai-dataset/policy.json                            |   2 +-
 ai-dataset/works/Works_CommonReferences.json      |   2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |   2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |   2 +-
 ai-dataset/works/Works_NumberTales.json           |   9 +-
 ai-dataset/works/Works_PastDivers.json            |   2 +-
 ai-dataset/works/Works_ShouArRiders.json          |   2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |   2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |   2 +-
 ai-dataset/works/Works_UnibyteLive.json           |   2 +-
 ai-dataset/works/Works_VirtuesUs.json             |   2 +-
 creations-db                                      |   2 +-
 17 files changed, 115 insertions(+), 106 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

