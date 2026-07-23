# サブモジュール同期ログ — 2026-07-24 07:02

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 809a444 | 7c63c33 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 12982c8 | 12982c8 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 809a444..7c63c33

```
7c63c33 chore: sync ai-dataset (creations-db@12982c8) 窶・ai_training allowed: 154 -> 155 [skip ci]
8dc95fd chore: sync ai-dataset (creations-db@7805c7c) 窶・ai_training allowed: 154 [skip ci]
c9e47c2 refactor: AGENTS.md 繧・SSOT 蛹悶＠ Copilot/Claude/Codex 險ｭ螳壹ｒ邨ｱ蜷・
```

変更ファイル:

```
.codex/hooks.json                                 |  14 +
 .github/copilot-instructions.md                   | 272 ++--------------
 .github/instructions/roleplay.instructions.md     |   5 +-
 AGENTS.md                                         | 374 +++++++++++++++++++---
 CLAUDE.md                                         | 241 ++------------
 README.md                                         |  23 +-
 ai-dataset/build-info.json                        |   8 +-
 ai-dataset/image-index.json                       |   6 +-
 ai-dataset/index.json                             |   8 +-
 ai-dataset/manifest-training.jsonl                |  10 +-
 ai-dataset/manifest.jsonl                         |  18 +-
 ai-dataset/policy.json                            |   2 +-
 ai-dataset/works/Works_CommonReferences.json      |   3 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |   2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |   2 +-
 ai-dataset/works/Works_NumberTales.json           |   2 +-
 ai-dataset/works/Works_PastDivers.json            |   2 +-
 ai-dataset/works/Works_ShouArRiders.json          |   2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |   2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |   2 +-
 ai-dataset/works/Works_UnibyteLive.json           |   2 +-
 ai-dataset/works/Works_VirtuesUs.json             |   2 +-
 creations-db                                      |   2 +-
 {.claude => docs/agents}/roleplay-prompt.md       |   0
 tools/hook-check-submodule.sh                     |   6 +-
 25 files changed, 468 insertions(+), 542 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

