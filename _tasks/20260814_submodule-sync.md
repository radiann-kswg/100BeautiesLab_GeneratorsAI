# サブモジュール同期ログ — 2026-08-14 08:39

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 032bdb8 | 38c09a1 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | e404522 | e404522 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 032bdb8..38c09a1

```
38c09a1 chore: sync ai-dataset (creations-db@e404522) 窶・ai_training allowed: 158 [skip ci]
969dbbf chore: sync ai-dataset (creations-db@8418fa9) 窶・ai_training allowed: 158 [skip ci]
af56f2a chore: sync ai-dataset (creations-db@629129f) 窶・ai_training allowed: 158 [skip ci]
8e42f68 chore: sync ai-dataset (creations-db@c09c1c5) 窶・ai_training allowed: 158 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |  12 +--
 ai-dataset/image-index.json                       |  11 ++-
 ai-dataset/index.json                             |  10 +-
 ai-dataset/manifest-training.jsonl                |  18 ++--
 ai-dataset/manifest.jsonl                         | 115 ++++++++++++----------
 ai-dataset/policy.json                            |   2 +-
 ai-dataset/works/Works_CommonReferences.json      |   2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |   2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |   2 +-
 ai-dataset/works/Works_NumberTales.json           |  19 +++-
 ai-dataset/works/Works_PastDivers.json            |   2 +-
 ai-dataset/works/Works_ShouArRiders.json          |   2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |   2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |   2 +-
 ai-dataset/works/Works_UnibyteLive.json           |   2 +-
 ai-dataset/works/Works_VirtuesUs.json             |   2 +-
 creations-db                                      |   2 +-
 17 files changed, 120 insertions(+), 87 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

