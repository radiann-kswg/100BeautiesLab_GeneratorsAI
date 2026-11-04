# サブモジュール同期ログ — 2026-11-04 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | ba7e8cb | e41934b | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | ccaa5d2 | ccaa5d2 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` ba7e8cb..e41934b

```
e41934b chore: sync ai-dataset (creations-db@ccaa5d2e) 窶・ai_training allowed: 181 [skip ci]
f00c882 chore: sync ai-dataset (creations-db@d4e37b9f) 窶・ai_training allowed: 180 -> 181 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                         | 20 ++++++++++----------
 ai-dataset/image-index.json                        | 16 +++++++++++++---
 ai-dataset/index.json                              |  6 +++---
 ai-dataset/manifest-training.jsonl                 |  5 +++--
 ai-dataset/manifest.jsonl                          |  6 +++---
 ai-dataset/policy.json                             |  2 +-
 ai-dataset/works/Works_CommonReferences.json       |  2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json      |  2 +-
 ai-dataset/works/Works_FLInvestigator78.json       |  2 +-
 ai-dataset/works/Works_NumberTales.json            | 16 +++++++++++++++-
 ai-dataset/works/Works_PastDivers.json             |  2 +-
 ai-dataset/works/Works_ShauErRiders.json           |  2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json  |  2 +-
 ai-dataset/works/Works_StardustVsKaleidoscope.json |  2 +-
 ai-dataset/works/Works_UnauthedLogica.json         |  2 +-
 ai-dataset/works/Works_UnibyteLive.json            |  2 +-
 ai-dataset/works/Works_VirtuesUs.json              |  2 +-
 creations-db                                       |  2 +-
 18 files changed, 59 insertions(+), 34 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

