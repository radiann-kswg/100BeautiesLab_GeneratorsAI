# サブモジュール同期ログ — 2026-08-21 09:52

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | fd8c59d | 5a7e1a3 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 37c353d | 37c353d | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` fd8c59d..5a7e1a3

```
5a7e1a3 chore: sync ai-dataset (creations-db@37c353d) 窶・ai_training allowed: 158 [skip ci]
9c45cc1 chore: sync ai-dataset (creations-db@376baa0) 窶・ai_training allowed: 158 [skip ci]
3bcb40c chore: sync ai-dataset (creations-db@31b7497) 窶・ai_training allowed: 158 [skip ci]
1753676 chore: sync ai-dataset (creations-db@2e97494) 窶・ai_training allowed: 158 [skip ci]
104bfa4 chore: sync ai-dataset (creations-db@5660016) 窶・ai_training allowed: 158 [skip ci]
68694e9 chore: sync ai-dataset (creations-db@b43c9f8) 窶・ai_training allowed: 158 [skip ci]
f999bcc chore: sync ai-dataset (creations-db@326e251) 窶・ai_training allowed: 158 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |  10 +-
 ai-dataset/image-index.json                       |   6 +-
 ai-dataset/index.json                             |   8 +-
 ai-dataset/manifest-training.jsonl                | 228 ++++-----
 ai-dataset/manifest.jsonl                         | 548 +++++++++++-----------
 ai-dataset/policy.json                            |   2 +-
 ai-dataset/works/Works_CommonReferences.json      |   2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |   3 +-
 ai-dataset/works/Works_FLInvestigator78.json      |   3 +-
 ai-dataset/works/Works_NumberTales.json           |  18 +-
 ai-dataset/works/Works_PastDivers.json            |   4 +-
 ai-dataset/works/Works_ShouArRiders.json          |   3 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |   2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |   4 +-
 ai-dataset/works/Works_UnibyteLive.json           |   6 +-
 ai-dataset/works/Works_VirtuesUs.json             |   2 +-
 creations-db                                      |   2 +-
 17 files changed, 438 insertions(+), 413 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

