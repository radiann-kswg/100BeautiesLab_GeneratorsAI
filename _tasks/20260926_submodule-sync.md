# サブモジュール同期ログ — 2026-09-26 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | ca88db6 | 1f07ee3 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | c2d3602 | c2d3602 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` ca88db6..1f07ee3

```
1f07ee3 chore: sync ai-dataset (creations-db@c2d36020) 窶・ai_training allowed: 161 -> 162 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |   8 +-
 ai-dataset/image-index.json                       |   6 +-
 ai-dataset/index.json                             |   8 +-
 ai-dataset/manifest-training.jsonl                |  21 +++--
 ai-dataset/manifest.jsonl                         | 107 +++++++++++-----------
 ai-dataset/policy.json                            |   2 +-
 ai-dataset/works/Works_CommonReferences.json      |   3 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |   2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |   2 +-
 ai-dataset/works/Works_NumberTales.json           |   2 +-
 ai-dataset/works/Works_PastDivers.json            |   2 +-
 ai-dataset/works/Works_ShauErRiders.json          |   2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |   2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |   2 +-
 ai-dataset/works/Works_UnibyteLive.json           |   2 +-
 ai-dataset/works/Works_VirtuesUs.json             |   2 +-
 creations-db                                      |   2 +-
 17 files changed, 89 insertions(+), 86 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

