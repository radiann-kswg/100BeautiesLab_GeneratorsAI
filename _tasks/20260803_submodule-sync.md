# サブモジュール同期ログ — 2026-08-03 18:08

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 531785f | 531785f | NO-CHANGE | 最新 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 66a6563 | b3218ba | UPDATED | FF 取り込み完了 |

## 取り込んだ更新の内容

### `_creations-ai/creations-db` 66a6563..b3218ba

```
b3218ba Merge branch 'develop' into addon-ai-tag
ab26667 DB騾ｲ謐玲峩譁ｰ・・ｧ矩謨ｴ蛯・繝上Φ繧ｫ繧ｯ繝ｩ繧､繝・
6b56724 騾ｲ謐励Ο繧ｰ譖ｴ譁ｰ
85d26f4 UI螟ｧ蟷・僑蠑ｵ 縺昴・・・299d1b9 DB讒矩謨ｴ蛯・UI螟ｧ蟷・僑蠑ｵ蜷代￠) 縺昴・・・c303b72 UI螟ｧ蟷・僑蠑ｵ 縺昴・6-2
ab2efd8 UI螟ｧ蟷・僑蠑ｵ 縺昴・6-1
```

変更ファイル:

```
CHANGELOG.md                                       |  21 +
 _work_in_progress/2026-07-25_remaining-task.md     |   7 +-
 .../2026-08-02_progress_relations-graph.md         | 209 +++++-
 ...2026-08-03_progress_relation-composite-index.md |  74 ++
 data/Works_PastDivers/DataBases/db_type.json       |   9 +-
 data/Works_UnibyteLive/DataBases/db_Primary.json   | 524 +++++++++++--
 .../DataBases/db_PrimaryPerformer.json             | 282 ++++++-
 data/Works_UnibyteLive/DataBases/db_meta.json      |  28 +-
 data/Works_UnibyteLive/DataBases/db_type.json      |  53 +-
 .../Works_UnibyteLive/Dictionaries/dict_Class.json |  56 +-
 data/db_meta.json                                  |  10 +-
 lib/graph/graph-crossing.js                        | 318 ++++++++
 lib/graph/graph-edge-route.js                      | 550 ++++++++++++++
 lib/graph/graph-facets.js                          | Bin 20300 -> 21343 bytes
 lib/graph/graph-hexfill.js                         | 644 ++++++++++++++++
 lib/graph/graph-layout.js                          |  62 +-
 lib/graph/graph-palette.js                         | 325 ++++++++
 lib/section-renders/relation.js                    |  93 ++-
 pages/characters.js                                |  13 +
 pages/relations.css                                |  99 ++-
 pages/relations.css.map                            |   1 +
 pages/relations.html                               |  27 +-
 pages/relations.js                                 | 815 ++++++++++++++++++---
 pages/relations.sass                               | 133 +++-
 tests/graph.crossing.test.js                       | 302 ++++++++
 tests/graph.edge-route.test.js                     | 376 ++++++++++
 tests/graph.facets.test.js                         | 111 ++-
 tests/graph.hexfill.test.js                        | 288 ++++++++
 tests/graph.palette.test.js                        | 247 +++++++
 tests/pages.characters.ui-output.test.js           |  73 +-
 tests/pages.relations.syntax.test.js               | 135 ++++
 tests/section-renders.relation.test.js             | 282 +++++++
 32 files changed, 5861 insertions(+), 306 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

