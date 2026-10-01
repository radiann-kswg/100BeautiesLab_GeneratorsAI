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


## 最適化レビュー結果 — 2026-09-28 (Cowork / Claude「57(イズナ)」追記)

- レビュー実施: Cowork スケジュールタスク（実機スクリプト取り込み後の追従レビュー）。
- 取り込み内容: `_creations-ai` 1f07ee3 → 8a47bfe（FF）。`_creations-ai/creations-db` は 2274eb1 のまま NO-CHANGE。
- リモート HEAD 照合（GitHub コネクタ・読み取りのみ / 認証OK）:
  - CreationsAI `master` remote = 8a47bfe … ローカルと一致（次回同期待ちの未取り込み更新なし）。
  - CreationsDB `addon-ai-tag` remote = 2274eb1 … ローカルと一致（未取り込み更新なし）。
- 差分の性質: `ai-dataset/` 配下のデータ・件数・タイムスタンプ更新のみ。
  - `manifest-training.jsonl`: 190 → 192 行。トップレベルキー集合は旧新で完全一致（スキーマ変更なし）。
  - `manifest.jsonl`: 757 行のまま。キー集合一致。
  - `build-info.json`: allowed_characters 162 → 164 / disallowed 551 → 549 / with_ai_hints 114 → 116 等の統計更新のみ。
  - `index.json` / `policy.json`: `_generated_at`・`_submodule_commit`・image_count 635 → 637 のみ。
  - `works/Works_NumberTales.json`: トップレベルキー集合一致（スキーマ変更なし。データ追記のみ）。
- スキーマ / `manifest-training.jsonl` 前提 / フィールド名 / API / 参照パスへの影響: **なし**。
  - AGENTS.md「docs と指示書の同期ルール」表のデータ関連トリガ（`Works_*.json` のスキーマ変更）は非該当。
- 判定: **src/・docs/・README.md・AGENTS.md の追従最適化は不要**（過剰改変回避のため編集せず）。
- コミット: 本追記は Cowork サンドボックスからはコミットしない（CRLF 差分による破壊回避）。実機で `git add _tasks/20260928_submodule-sync.md && git commit`（または `scripts/daily-submodule-sync.ps1`）を実施のこと。
- 備考: この Linux VM 側 git は working-tree を CRLF↔LF 差分（numstat 50/50）として表示。実機の autocrlf 環境では正常。`.git/index.lock` は FUSE マウント上で削除不可（既知制約）。
