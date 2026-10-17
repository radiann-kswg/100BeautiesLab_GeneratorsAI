# サブモジュール同期ログ — 2026-10-03 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | c78afcb | add4084 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | ee179f8 | ee179f8 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` c78afcb..add4084

```
add4084 chore: sync ai-dataset (creations-db@ee179f83) 窶・ai_training allowed: 164 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |  4 ++--
 ai-dataset/image-index.json                       | 14 ++++++++++++--
 ai-dataset/index.json                             |  6 +++---
 ai-dataset/manifest-training.jsonl                |  2 +-
 ai-dataset/manifest.jsonl                         | 22 +++++++++++-----------
 ai-dataset/policy.json                            |  2 +-
 ai-dataset/works/Works_CommonReferences.json      |  2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |  2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |  2 +-
 ai-dataset/works/Works_NumberTales.json           | 12 +++++++++++-
 ai-dataset/works/Works_PastDivers.json            |  2 +-
 ai-dataset/works/Works_ShauErRiders.json          |  2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |  2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |  2 +-
 ai-dataset/works/Works_UnibyteLive.json           |  2 +-
 ai-dataset/works/Works_VirtuesUs.json             |  2 +-
 creations-db                                      |  2 +-
 17 files changed, 51 insertions(+), 31 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

### 追従確認

- **確認対象:** `add4084` の変更一覧（生成済み `manifest*.jsonl`、`image-index.json`、各 `works/*.json`、`policy.json` と creations-db の参照先）および `src/utils/dataset.py` の manifest / 画像参照処理。
- **判定:** `src/` / `docs/` の追従変更は不要。親リポジ側の差分はデータセット生成物とサブモジュール参照先の更新で、スキーマ・API・生成ロジックの変更はない。許可件数などは生成済み manifest から読み、画像参照も manifest / image-index の値を処理するため、同期データがそのまま反映される。
- **根拠:** 同期ログの変更ファイル一覧では `ai-dataset` 配下の生成物と `creations-db` のみが更新されている。現行コードに件数や当日のデータを固定した処理はない。
