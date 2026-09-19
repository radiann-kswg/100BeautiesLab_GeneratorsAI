# サブモジュール同期ログ — 2026-09-19 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | f0fcd4b | 090a27a | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 35a41b9 | 35a41b9 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` f0fcd4b..090a27a

```
090a27a chore: sync ai-dataset (creations-db@35a41b9b) 窶・ai_training allowed: 160 [skip ci]
9574b93 chore: sync ai-dataset (creations-db@c2b5744b) 窶・ai_training allowed: 160 [skip ci]
56c7d5d chore: sync ai-dataset (creations-db@0f49abcc) 窶・ai_training allowed: 160 [skip ci]
67480c6 chore: sync ai-dataset (creations-db@832939aa) 窶・ai_training allowed: 160 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |   6 +-
 ai-dataset/image-index.json                       |  36 ++++-
 ai-dataset/index.json                             |   8 +-
 ai-dataset/manifest-training.jsonl                |  32 ++---
 ai-dataset/manifest.jsonl                         | 168 +++++++++++-----------
 ai-dataset/policy.json                            |   2 +-
 ai-dataset/works/Works_CommonReferences.json      |   2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |   2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |   2 +-
 ai-dataset/works/Works_NumberTales.json           |  22 ++-
 ai-dataset/works/Works_PastDivers.json            |   6 +-
 ai-dataset/works/Works_ShauErRiders.json          |   2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |  16 ++-
 ai-dataset/works/Works_UnauthedLogica.json        |   4 +-
 ai-dataset/works/Works_UnibyteLive.json           |   2 +-
 ai-dataset/works/Works_VirtuesUs.json             |   2 +-
 creations-db                                      |   2 +-
 17 files changed, 187 insertions(+), 127 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

