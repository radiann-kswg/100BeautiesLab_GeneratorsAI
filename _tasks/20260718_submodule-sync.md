# サブモジュール同期ログ — 2026-07-18 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 2c26366 | f4eb76f | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 9041a66 | 9041a66 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 2c26366..f4eb76f

```
f4eb76f chore: sync ai-dataset (creations-db@9041a66) 窶・ai_training allowed: 153 [skip ci]
caef24d chore: sync ai-dataset (creations-db@68e8dc2) 窶・ai_training allowed: 153 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |   4 +-
 ai-dataset/image-index.json                       |   2 +-
 ai-dataset/index.json                             |   4 +-
 ai-dataset/manifest-training.jsonl                | 220 ++++-----
 ai-dataset/manifest.jsonl                         | 520 +++++++++++-----------
 ai-dataset/policy.json                            |   2 +-
 ai-dataset/works/Works_CommonReferences.json      |   2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |   2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |  16 +-
 ai-dataset/works/Works_NumberTales.json           |  14 +-
 ai-dataset/works/Works_PastDivers.json            |  13 +-
 ai-dataset/works/Works_ShouArRiders.json          |   4 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |   2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |  10 +-
 ai-dataset/works/Works_UnibyteLive.json           |   7 +-
 ai-dataset/works/Works_VirtuesUs.json             |   2 +-
 creations-db                                      |   2 +-
 17 files changed, 422 insertions(+), 404 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

