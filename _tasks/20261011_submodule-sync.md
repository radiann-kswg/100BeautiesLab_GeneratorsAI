# サブモジュール同期ログ — 2026-10-11 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 73776a7 | ea4768c | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | ab2b784 | ab2b784 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 73776a7..ea4768c

```
ea4768c chore: sync ai-dataset (creations-db@ab2b7844) 窶・ai_training allowed: 172 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |   8 +-
 ai-dataset/image-index.json                       | 126 +++++++++++++---------
 ai-dataset/index.json                             |  10 +-
 ai-dataset/manifest-training.jsonl                |  18 ++--
 ai-dataset/manifest.jsonl                         |  53 +++++----
 ai-dataset/policy.json                            |   2 +-
 ai-dataset/works/Works_CommonReferences.json      |   4 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |   2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |   2 +-
 ai-dataset/works/Works_NumberTales.json           | 118 +++++++++++---------
 ai-dataset/works/Works_PastDivers.json            |   2 +-
 ai-dataset/works/Works_ShauErRiders.json          |   2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |  11 +-
 ai-dataset/works/Works_UnauthedLogica.json        |   2 +-
 ai-dataset/works/Works_UnibyteLive.json           |   6 +-
 ai-dataset/works/Works_VirtuesUs.json             |   2 +-
 creations-db                                      |   2 +-
 17 files changed, 212 insertions(+), 158 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

