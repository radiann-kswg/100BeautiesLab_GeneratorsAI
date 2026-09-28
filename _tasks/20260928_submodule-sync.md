# サブモジュール同期ログ — 2026-09-28 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 1f07ee3 | 8a47bfe | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 2274eb1 | 2274eb1 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 1f07ee3..8a47bfe

```
8a47bfe chore: sync ai-dataset (creations-db@2274eb19) 窶・ai_training allowed: 164 [skip ci]
dffa25a chore: sync ai-dataset (creations-db@98706dec) 窶・ai_training allowed: 164 [skip ci]
01d038d chore: sync ai-dataset (creations-db@d6a471ad) 窶・ai_training allowed: 162 -> 164 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        | 18 ++++-----
 ai-dataset/image-index.json                       | 28 +++++++++++--
 ai-dataset/index.json                             |  6 +--
 ai-dataset/manifest-training.jsonl                | 12 +++---
 ai-dataset/manifest.jsonl                         | 48 +++++++++++------------
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
 17 files changed, 105 insertions(+), 57 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

