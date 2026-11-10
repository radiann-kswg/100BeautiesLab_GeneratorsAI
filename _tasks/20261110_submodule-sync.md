# サブモジュール同期ログ — 2026-11-10 16:58

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 2a518ce | 2a518ce | NO-CHANGE | 最新 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 65084c6 | 65084c6 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

今回取り込んだ更新はありません。

## 最終参照先までの影響確認

- `_creations-ai` `c0462ce..2a518ce` は 5 件のデータセット同期。参照先の CreationsDB は `649c670` から `65084c6` へ進み、PR #55 / #56 で構造由来 AIHints を再同期している。再同期対象は DB 構造タグで、手動編集のタグや視覚由来フィールドは対象外。
- `manifest-training.jsonl` は 215 行（許可キャラクター 181 件）で件数・レコード外形スキーマに変更なし。`manifest.jsonl` はキャラクター 738→740 件（789→791 行）となったが、レコード外形スキーマに変更なし。`build-info.json` の項目構造と AIHints 件数（118）も不変。
- 確認した差分は DB / データセット内容の更新で、親リポの manifest/API スキーマ変更はない。`src/`・`docs/` の追従変更は不要と判断。

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。
