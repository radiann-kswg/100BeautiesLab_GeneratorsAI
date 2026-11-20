# サブモジュール同期ログ — 2026-11-20 16:50

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | b7ccb20 | 6f5b37d | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | f2d10b1 | f2d10b1 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` b7ccb20..6f5b37d

```
6f5b37d chore: sync ai-dataset (creations-db@f2d10b1f) 窶・ai_training allowed: 187 [skip ci]
4e9a69a chore: sync ai-dataset (creations-db@a4b1a43d) 窶・ai_training allowed: 187 [skip ci]
d8eb504 chore: sync ai-dataset (creations-db@fa10a498) 窶・ai_training allowed: 187 [skip ci]
f037968 fix: enforce AI opt-outs in dataset exports
fa26d38 chore: sync ai-dataset (creations-db@7849c017) 窶・ai_training allowed: 191 [skip ci]
b92e3a8 chore: sync ai-dataset (creations-db@211bff56) 窶・ai_training allowed: 191 [skip ci]
```

変更ファイル:

```
AGENTS.md                                          |   12 +
 ai-dataset/build-info.json                         |   18 +-
 ai-dataset/image-index.json                        | 7015 ++++++--------------
 ai-dataset/index.json                              |   20 +-
 ai-dataset/manifest-training.jsonl                 |  208 +-
 ai-dataset/manifest.jsonl                          | 1304 ++--
 ai-dataset/policy.json                             |   13 +-
 ai-dataset/works/Works_CommonReferences.json       |    2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json      |  425 +-
 ai-dataset/works/Works_FLInvestigator78.json       |  145 +-
 ai-dataset/works/Works_NumberTales.json            | 5058 ++++----------
 ai-dataset/works/Works_PastDivers.json             |   25 +-
 ai-dataset/works/Works_ShauErRiders.json           |   12 +-
 ai-dataset/works/Works_SinisterChangingGirls.json  |   32 +-
 ai-dataset/works/Works_StardustVsKaleidoscope.json |    2 +-
 ai-dataset/works/Works_UnauthedLogica.json         |   15 +-
 ai-dataset/works/Works_UnibyteLive.json            |   85 +-
 ai-dataset/works/Works_VirtuesUs.json              |    2 +-
 creations-db                                       |    2 +-
 scripts/build-dataset.js                           |  185 +-
 scripts/lib/dataset-helpers.js                     |    5 +-
 scripts/lib/dataset-helpers.test.js                |    8 +
 scripts/lib/image-policy.test.js                   |  140 +
 scripts/lib/policy.js                              |   38 +-
 scripts/lib/policy.test.js                         |   18 +
 scripts/validate-dataset.js                        |  Bin 19493 -> 23100 bytes
 26 files changed, 4745 insertions(+), 10044 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

