# サブモジュール同期ログ — 2026-07-31 06:44

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 7c665a3 | eea3725 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 6d422bd | 6d422bd | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 7c665a3..eea3725

```
eea3725 chore: sync ai-dataset (creations-db@6d422bd) 窶・ai_training allowed: 155 [skip ci]
8efe07a chore: sync ai-dataset (creations-db@2f4cfc3) 窶・ai_training allowed: 155 [skip ci]
1c371fa chore: sync ai-dataset (creations-db@e17df30) 窶・ai_training allowed: 155 [skip ci]
977a8e3 chore: sync ai-dataset (creations-db@6cdccdf) 窶・ai_training allowed: 155 [skip ci]
132375b chore: sync ai-dataset (creations-db@de816fd) 窶・ai_training allowed: 155 [skip ci]
5b3b07a chore: sync ai-dataset (creations-db@ca899c6) 窶・ai_training allowed: 155 [skip ci]
3784c3e chore: sync ai-dataset (creations-db@a2b6db2) 窶・ai_training allowed: 155 [skip ci]
325889d chore: sync ai-dataset (creations-db@237b194) 窶・ai_training allowed: 155 [skip ci]
1cfd42d chore: sync ai-dataset (creations-db@79cafd1) 窶・ai_training allowed: 155 [skip ci]
b37a32f chore: sync ai-dataset (creations-db@8f5cf12) 窶・ai_training allowed: 155 [skip ci]
62e7983 chore: sync ai-dataset (creations-db@54798c9) 窶・ai_training allowed: 155 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |   8 +-
 ai-dataset/image-index.json                       |  70 +-
 ai-dataset/index.json                             |  14 +-
 ai-dataset/manifest-training.jsonl                | 225 +++---
 ai-dataset/manifest.jsonl                         | 808 +++++++++++-----------
 ai-dataset/policy.json                            |   2 +-
 ai-dataset/works/Works_CommonReferences.json      |   2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |  37 +-
 ai-dataset/works/Works_FLInvestigator78.json      |   4 +-
 ai-dataset/works/Works_NumberTales.json           |  10 +-
 ai-dataset/works/Works_PastDivers.json            |   8 +-
 ai-dataset/works/Works_ShouArRiders.json          |  17 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |   3 +-
 ai-dataset/works/Works_UnauthedLogica.json        |   2 +-
 ai-dataset/works/Works_UnibyteLive.json           |   2 +-
 ai-dataset/works/Works_VirtuesUs.json             |   7 +-
 creations-db                                      |   2 +-
 17 files changed, 629 insertions(+), 592 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

