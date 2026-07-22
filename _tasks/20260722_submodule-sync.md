# サブモジュール同期ログ — 2026-07-22 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 0c94954 | 809a444 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | acd1d8f | acd1d8f | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 0c94954..809a444

```
809a444 chore: sync ai-dataset (creations-db@acd1d8f) 窶・ai_training allowed: 154 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        | 4 ++--
 ai-dataset/image-index.json                       | 2 +-
 ai-dataset/index.json                             | 4 ++--
 ai-dataset/manifest-training.jsonl                | 4 ++--
 ai-dataset/manifest.jsonl                         | 6 +++---
 ai-dataset/policy.json                            | 2 +-
 ai-dataset/works/Works_CommonReferences.json      | 2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     | 2 +-
 ai-dataset/works/Works_FLInvestigator78.json      | 2 +-
 ai-dataset/works/Works_NumberTales.json           | 2 +-
 ai-dataset/works/Works_PastDivers.json            | 2 +-
 ai-dataset/works/Works_ShouArRiders.json          | 2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json | 2 +-
 ai-dataset/works/Works_UnauthedLogica.json        | 2 +-
 ai-dataset/works/Works_UnibyteLive.json           | 2 +-
 ai-dataset/works/Works_VirtuesUs.json             | 2 +-
 creations-db                                      | 2 +-
 17 files changed, 22 insertions(+), 22 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

