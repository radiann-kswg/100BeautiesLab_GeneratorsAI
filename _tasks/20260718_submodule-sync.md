# サブモジュール同期ログ — 2026-07-18 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 2c26366 | f4eb76f | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 9041a66 | 9041a66 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 2c26366..f4eb76f

```
f4eb76f chore: sync ai-dataset (creations-db@9041a66) 窶・ai_training allowed: 153 [skip ci]
caef24d chore: sync ai-dataset (creations-db@68e8dc2) 窶・ai_training allowed: 153 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |   4 +-
 ai-dataset/image-index.json                       |   2 +-
 ai-dataset/index.json                             |   4 +-
 ai-dataset/manifest-training.jsonl                | 220 ++++-----
 ai-dataset/manifest.jsonl                         | 520 +++++++++++-----------
 ai-dataset/policy.json                            |   2 +-
 ai-dataset/works/Works_CommonReferences.json      |   2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |   2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |  16 +-
 ai-dataset/works/Works_NumberTales.json           |  14 +-
 ai-dataset/works/Works_PastDivers.json            |  13 +-
 ai-dataset/works/Works_ShouArRiders.json          |   4 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |   2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |  10 +-
 ai-dataset/works/Works_UnibyteLive.json           |   7 +-
 ai-dataset/works/Works_VirtuesUs.json             |   2 +-
 creations-db                                      |   2 +-
 17 files changed, 422 insertions(+), 404 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。


---

## Cowork レビュー追記 — 2026-07-18 19:07 (57(イズナ) / daily-submodule-sync-optimize)

### 実機スクリプト実行
- `scripts/daily-submodule-sync.ps1` は 09:00 に実行済み。`_creations-ai` を 2c26366 → f4eb76f に FF 取り込み、`creations-db` は 9041a66 で NO-CHANGE。

### 取り込み差分レビュー (2c26366..f4eb76f)
- 内容: ai-dataset の定常同期 (build-info/index/policy の generated_at・submodule_commit 更新 + 各 works JSON のフィールドキー追加・並び替え)。
- `manifest-training.jsonl` の**トップレベルキー集合は不変** (追加0・削除0)。schema 変更なし。
- works JSON 側で `FirstPersonCalling` / `SecondPersonCalling` / `ThirdPersonCalling` / `ForMasterCalling` / `For79thDealerCalling` / `For80thDealerCalling` / `ArcanamspecAbout` 等の呼称・章立てフィールドが DB ソース由来で追加。ただしこれらは `data` 内のフィールド一覧値であり、`src/` が消費する `ai_hints` / `immutable_traits` / `identity_tags` 等のトップレベルキーには影響なし。

### 最適化判断: **不要**
- `src/` (batch_generate.py / pipeline/*.py) と `docs/*.md` の参照キー・API・パス規則に影響する変更なし。過剰改変を避けるため `src/` `docs/` `README.md` `AGENTS.md` は編集せず。

### リモート先行の傍証 (GitHub コネクタ, 読み取りのみ)
- CreationsAI/master リモート HEAD = e28b64d (2026-07-18T07:09Z ≒ 16:09 JST, creations-db@50e7ee1 同期) → ローカル f4eb76f より**先行**。
- CreationsDB/addon-ai-tag リモート HEAD = 50e7ee1 (Merge develop, 「フィールドキー順並び替え 続き」含む) → ローカル submodule 9041a66 より**先行**。
- いずれも 09:00 同期の**後**(本日午後)に push されたもの。次回の実機 sync で取り込み予定。取り込み後も上記と同種のフィールド並び替えが中心の見込みで、schema 影響は低いと推測。

### 先輩へのお願い
- コミットはこのサンドボックスからは行っていない (bash git・コネクタ書き込み共に不可)。実機で `scripts/daily-submodule-sync.ps1` を再実行、または `git add`/`git commit` して午後のリモート先行分を取り込んでほしい。
