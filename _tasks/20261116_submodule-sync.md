# サブモジュール同期ログ — 2026-11-16 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 6379b94 | 318c8f4 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 117e6cb | 9b9bbab | UPDATED | FF 取り込み完了 |

## 取り込んだ更新の内容

### `_creations-ai` 6379b94..318c8f4

```
318c8f4 chore: sync ai-dataset (creations-db@117e6cb3) 窶・ai_training allowed: 181 [skip ci]
4f594ed chore: sync ai-dataset (creations-db@15ac820a) 窶・ai_training allowed: 181 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                         |  6 +-
 ai-dataset/image-index.json                        | 14 +++-
 ai-dataset/index.json                              |  6 +-
 ai-dataset/manifest-training.jsonl                 | 26 ++------
 ai-dataset/manifest.jsonl                          | 74 +++++++++-------------
 ai-dataset/policy.json                             |  2 +-
 ai-dataset/works/Works_CommonReferences.json       | 10 +--
 ai-dataset/works/Works_DestinyFoxRecords.json      |  2 +-
 ai-dataset/works/Works_FLInvestigator78.json       |  2 +-
 ai-dataset/works/Works_NumberTales.json            | 16 ++++-
 ai-dataset/works/Works_PastDivers.json             |  2 +-
 ai-dataset/works/Works_ShauErRiders.json           |  2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json  |  2 +-
 ai-dataset/works/Works_StardustVsKaleidoscope.json |  2 +-
 ai-dataset/works/Works_UnauthedLogica.json         |  2 +-
 ai-dataset/works/Works_UnibyteLive.json            |  2 +-
 ai-dataset/works/Works_VirtuesUs.json              |  2 +-
 creations-db                                       |  2 +-
 18 files changed, 85 insertions(+), 89 deletions(-)
```

### `_creations-ai/creations-db` 117e6cb..9b9bbab

```
9b9bbabb Merge pull request #57 from radiann-kswg/auto/aihints-structural-resync
a2f7ee2c AIHints: 讒矩逧・・蜷梧悄・郁・蜍慕函謌撰ｼ・
```

変更ファイル:

```
.../DataBases/db_SelfSecondary.json                  | 20 ++++++++++----------
 data/Works_NumberTales/DataBases/db_SemiPrimary.json | 14 ++++----------
 2 files changed, 14 insertions(+), 20 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

