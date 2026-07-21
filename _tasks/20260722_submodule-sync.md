# サブモジュール同期ログ — 2026-07-22 08:25

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | dc25100 | 0c94954 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 8392433 | 8392433 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` dc25100..0c94954

```
0c94954 chore: sync ai-dataset (creations-db@8392433) — ai_training allowed: 154 [skip ci]
4e8fb1e chore: sync ai-dataset (creations-db@027a8ec) — ai_training allowed: 153 -> 154 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        | 10 +++----
 ai-dataset/image-index.json                       | 11 ++++----
 ai-dataset/index.json                             | 12 ++++-----
 ai-dataset/manifest-training.jsonl                |  9 ++++---
 ai-dataset/manifest.jsonl                         | 32 ++++++++++++-----------
 ai-dataset/policy.json                            |  2 +-
 ai-dataset/works/Works_CommonReferences.json      |  3 ++-
 ai-dataset/works/Works_DestinyFoxRecords.json     |  2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |  4 ++-
 ai-dataset/works/Works_NumberTales.json           |  2 +-
 ai-dataset/works/Works_PastDivers.json            |  2 +-
 ai-dataset/works/Works_ShouArRiders.json          |  2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |  2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |  2 +-
 ai-dataset/works/Works_UnibyteLive.json           |  2 +-
 ai-dataset/works/Works_VirtuesUs.json             |  2 +-
 creations-db                                      |  2 +-
 17 files changed, 54 insertions(+), 47 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

### 差分レビュー結果 (2026-07-22 / Claude Code)

**判定: `src/` ・ `docs/` の追従は不要。**

| 観点 | 確認結果 |
|---|---|
| manifest スキーマ | `manifest.jsonl` の追加行・削除行のキー集合が完全一致。フィールド追加/削除なし |
| 軸判別ゲートの意味論 | `ai_training.allowed` / `reason` の文言・粒度に変更なし（`AI_Optout` / `DB_Hidden` / `Works_Hidden` 判定のまま） |
| `policy.json` | 差分は `_generated_at` のみ。ポリシー構造の変更なし |
| データ増分 | `total_characters` 532 → 534、`allowed_characters` 153 → 154。共通資料に種族タグ `人狼惹き` が追加され、対応キャラが allowed で 1 件増、opt-out DB 側で 1 件増 |
| `_creations-ai/creations-db` | `8392433` へ既に追従済み（`_creations-ai` の再帰更新で取り込み済み・NO-CHANGE） |

**回帰テスト:** `python tests/test_ai_optout_gate.py` → **9/9 passed**
（`test_ai_training_axis` / `test_apply_generation_gate_meta` / `test_load_roleplay_*` を含むゲート系がすべて通過）

判定根拠: 変更はいずれもデータ再生成に伴う値の更新であり、`src/utils/dataset.py` の
`generation_permitted` / `apply_generation_gate` が参照するフィールド名・判定軸に影響しないため。

### 補足: 実行時に発生した事象

初回の本実行は、サブモジュールの git ディレクトリに残っていた **stale な `index.lock`**
（`.git/modules/_creations-ai/index.lock` ほか 1 件、0 バイト・保持プロセスなし）により
両サブモジュールが `SKIP` となった（コミット `a569929`）。
ロックを排他オープンで無保持と確認したうえで除去し、再実行して `UPDATED` を取得（コミット `a8a4760`）。
ルート側 `.git/index.lock` にも同様の残骸があり、同じ手順で除去済み。

