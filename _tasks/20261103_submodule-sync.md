# サブモジュール同期ログ — 2026-11-03 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | bfd918e | ba7e8cb | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | a1051a7 | a1051a7 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` bfd918e..ba7e8cb

```
ba7e8cb chore: sync ai-dataset (creations-db@a1051a73) 窶・ai_training allowed: 180 [skip ci]
6943278 chore: sync ai-dataset (creations-db@1f4a1af9) 窶・ai_training allowed: 180 [skip ci]
eaafaf0 chore: sync ai-dataset (creations-db@22cff1da) 窶・ai_training allowed: 180 [skip ci]
15247b4 chore: sync ai-dataset (creations-db@1a17ba2b) 窶・ai_training allowed: 180 [skip ci]
8d4bd7a chore: sync ai-dataset (creations-db@7647661d) 窶・ai_training allowed: 180 [skip ci]
a03ebbb chore: sync ai-dataset (creations-db@738bdf3b) 窶・ai_training allowed: 180 [skip ci]
004435d chore: sync ai-dataset (creations-db@4f476765) 窶・ai_training allowed: 179 -> 180 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                         | 10 +++++-----
 ai-dataset/image-index.json                        | 16 +++++++++++++---
 ai-dataset/index.json                              |  6 +++---
 ai-dataset/manifest-training.jsonl                 |  3 ++-
 ai-dataset/manifest.jsonl                          |  4 ++--
 ai-dataset/policy.json                             |  2 +-
 ai-dataset/works/Works_CommonReferences.json       |  2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json      |  2 +-
 ai-dataset/works/Works_FLInvestigator78.json       |  2 +-
 ai-dataset/works/Works_NumberTales.json            |  2 +-
 ai-dataset/works/Works_PastDivers.json             |  2 +-
 ai-dataset/works/Works_ShauErRiders.json           |  2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json  | 12 +++++++++++-
 ai-dataset/works/Works_StardustVsKaleidoscope.json |  2 +-
 ai-dataset/works/Works_UnauthedLogica.json         |  2 +-
 ai-dataset/works/Works_UnibyteLive.json            |  2 +-
 ai-dataset/works/Works_VirtuesUs.json              |  2 +-
 creations-db                                       |  2 +-
 18 files changed, 48 insertions(+), 27 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

