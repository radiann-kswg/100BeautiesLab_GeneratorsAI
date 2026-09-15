# サブモジュール同期ログ — 2026-09-15 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 49a48cc | f0fcd4b | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 3479329 | 3479329 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 49a48cc..f0fcd4b

```
f0fcd4b chore: sync ai-dataset (creations-db@34793298) 窶・ai_training allowed: 160 [skip ci]
328cf08 chore: sync ai-dataset (creations-db@d787bbd2) 窶・ai_training allowed: 160 [skip ci]
739fca0 chore: sync ai-dataset (creations-db@59b150f4) 窶・ai_training allowed: 160 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |  8 ++--
 ai-dataset/image-index.json                       | 28 +++++++++++--
 ai-dataset/index.json                             | 10 ++---
 ai-dataset/manifest-training.jsonl                |  2 +-
 ai-dataset/manifest.jsonl                         | 48 +++++++++++++----------
 ai-dataset/policy.json                            |  2 +-
 ai-dataset/works/Works_CommonReferences.json      |  2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |  2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |  2 +-
 ai-dataset/works/Works_NumberTales.json           | 28 ++++++++++++-
 ai-dataset/works/Works_PastDivers.json            |  2 +-
 ai-dataset/works/Works_ShauErRiders.json          |  2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |  2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |  2 +-
 ai-dataset/works/Works_UnibyteLive.json           |  2 +-
 ai-dataset/works/Works_VirtuesUs.json             |  2 +-
 creations-db                                      |  2 +-
 17 files changed, 99 insertions(+), 47 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

