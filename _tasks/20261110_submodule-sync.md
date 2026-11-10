# サブモジュール同期ログ — 2026-11-10 16:58

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | bbf785b | 2a518ce | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 65084c6 | 65084c6 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` bbf785b..2a518ce

```
2a518ce chore: sync ai-dataset (creations-db@65084c65) 窶・ai_training allowed: 181 [skip ci]
2f4012f chore: sync ai-dataset (creations-db@a98ddfef) 窶・ai_training allowed: 181 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                         | 10 +--
 ai-dataset/image-index.json                        |  4 +-
 ai-dataset/index.json                              |  8 +-
 ai-dataset/manifest-training.jsonl                 | 36 ++++----
 ai-dataset/manifest.jsonl                          | 98 +++++++++++-----------
 ai-dataset/policy.json                             |  2 +-
 ai-dataset/works/Works_CommonReferences.json       |  2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json      |  2 +-
 ai-dataset/works/Works_FLInvestigator78.json       |  2 +-
 ai-dataset/works/Works_NumberTales.json            | 56 +++++++++++--
 ai-dataset/works/Works_PastDivers.json             |  2 +-
 ai-dataset/works/Works_ShauErRiders.json           |  2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json  |  2 +-
 ai-dataset/works/Works_StardustVsKaleidoscope.json |  2 +-
 ai-dataset/works/Works_UnauthedLogica.json         |  2 +-
 ai-dataset/works/Works_UnibyteLive.json            |  2 +-
 ai-dataset/works/Works_VirtuesUs.json              |  2 +-
 creations-db                                       |  2 +-
 18 files changed, 138 insertions(+), 98 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

