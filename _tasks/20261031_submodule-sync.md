# サブモジュール同期ログ — 2026-10-31 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 8a0797d | bfd918e | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | f74517f | f74517f | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 8a0797d..bfd918e

```
bfd918e Merge pull request #3 from radiann-kswg/radiann-kswg-rp-inference-permissions
6989cd4 Merge master and regenerate dataset to resolve manifest conflict
937ce2f chore: sync ai-dataset (creations-db@f74517fb) 窶・ai_training allowed: 179 [skip ci]
825097e feat: separate text RP inference permission from training
```

変更ファイル:

```
AGENTS.md                                          |   15 +-
 NOTICE.md                                          |   11 +
 README.md                                          |   53 +-
 ai-dataset/build-info.json                         |   11 +-
 ai-dataset/image-index.json                        |    2 +-
 ai-dataset/index.json                              |   15 +-
 ai-dataset/manifest-training.jsonl                 |    2 +-
 ai-dataset/manifest.jsonl                          | 1478 ++---
 ai-dataset/policy.json                             |   59 +-
 ai-dataset/works/Works_CommonReferences.json       |  958 ++-
 ai-dataset/works/Works_DestinyFoxRecords.json      |  274 +-
 ai-dataset/works/Works_FLInvestigator78.json       | 2044 ++++++-
 ai-dataset/works/Works_NumberTales.json            | 6178 +++++++++++++++++++-
 ai-dataset/works/Works_PastDivers.json             |  344 +-
 ai-dataset/works/Works_ShauErRiders.json           |  214 +-
 ai-dataset/works/Works_SinisterChangingGirls.json  |  508 +-
 ai-dataset/works/Works_StardustVsKaleidoscope.json |    3 +-
 ai-dataset/works/Works_UnauthedLogica.json         | 2290 +++++++-
 ai-dataset/works/Works_UnibyteLive.json            |  897 ++-
 ai-dataset/works/Works_VirtuesUs.json              |  148 +-
 creations-db                                       |    2 +-
 docs/usage-gemini-chatgpt-novelai.md               |   46 +-
 scripts/build-dataset.js                           |  121 +-
 scripts/lib/policy.js                              |   29 +-
 scripts/lib/text-rp.js                             |   75 +
 scripts/lib/text-rp.test.js                        |  144 +
 scripts/validate-dataset.js                        |  Bin 14731 -> 18377 bytes
 27 files changed, 15093 insertions(+), 828 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

