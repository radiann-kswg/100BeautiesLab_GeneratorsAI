# サブモジュール同期ログ — 2026-07-10 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 373f0ee | 1be022a | SKIP | 取り込み失敗: Already on 'master' |

## 取り込んだ更新の内容

今回取り込んだ更新はありません。

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。


---

## Cowork レビュー追記 — 2026-07-10（daily-submodule-sync-optimize / 57 イズナ）

- **実機スクリプト**: 09:00 に実行済み（本ログ生成を確認）。判定は `_creations-ai` = SKIP（新規取り込みなし）。
- **ローカル実態 vs リモート（GitHubコネクタ照合）**:
  - `_creations-ai` ローカル HEAD `fea04af` = リモート `origin/master` `fea04af`（2026-07-10 08:30, github-actions[bot]）→ **一致・同期済み**。
  - `_creations-ai/creations-db` ローカル HEAD `5cba462` = リモート `addon-ai-tag` `5cba462`（2026-07-10 08:19）→ **一致・同期済み**。
  - ログ表の「旧 373f0ee → 新 1be022a」は履歴上いずれも `fea04af` より前の古いコミット。実作業ツリーは既に `fea04af` まで前進しており、**次回同期待ちのリモート更新は無し**。ログ表の旧/新値は実態より古い表示（実害なし）。
- **本日リモートに着地した実質更新** `34f49bd`（TailsUnit 参考画像 + VirtuesUs オプトアウト修正、creations-db `fb17d0f`→`5cba462`）はスキーマ影響あり（`attr/tailsUnit` サブフォルダ属性 / `TailsUnit_PNGName` 参考画像 / `build-dataset.js` の `has_tails_unit`・`tails_unit_stats` 等）。
- **親リポ追従の要否判定**: `src/utils/dataset.py`・`docs/usage-generation.md` に既に **2026-07-10 付の TailsUnit 追従実装/記述が存在**（`tails_unit` パス解決・`_extract_tails_unit_texts`・`has_tails_unit`・humanoid 限定除外・images.tails_unit 収集）。データ側 `manifest.jsonl` も `has_tails_unit`(500)/`tails_unit`(11)/`attr/tailsUnit`(11) を保持し、`dataset.py` は構文パスOK。→ **コード/データ整合済み。追加の最適化は不要**（過剰改変回避のため編集せず）。
- **先輩へ**: 本サンドボックスからは commit 不可。ローカルは既にリモートと一致しているため、実機側で追加の `git add`/`commit` が必要な差分は現状なし（`scripts/daily-submodule-sync.ps1` の定常運用継続でOK）。ログ表の旧/新値のズレが気になる場合のみ実機スクリプトの表示ロジックを確認推奨。
