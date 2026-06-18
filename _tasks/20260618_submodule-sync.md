# サブモジュール同期ログ（Cowork レビュー） — 2026-06-18

> Cowork 自動タスク `daily-submodule-sync-optimize`（Claude=イズナ）による**読み取りレビュー**記録。
> 本ファイルはサンドボックスから作成した未コミットの advisory であり、実機スクリプト
> `scripts/daily-submodule-sync.ps1` による自動生成ログではない。`git add`/`commit`/`fetch` は一切行っていない。

## 実行サマリ

- 実機スクリプト実行: **今日（20260618）の自動生成ログは存在しない**。`_tasks/` 内の同期ログは
  `20260614_submodule-sync.md`（手動先行実行）が直近で、実機 `daily-submodule-sync.ps1` 由来のログは未生成。
  → **Windows タスクスケジューラへの登録がまだ／未稼働の可能性が高い**（`register-submodule-sync-task.ps1` は本日 11:05 更新で、09:00 トリガーより後）。
- 環境制約: 当サンドボックスは GitHub 到達不可（`fetch` 不可）、FUSE マウント上の git ロック削除不可、
  全ファイル CRLF↔LF 差分のため**サンドボックスからの commit は禁止**。git 同期・コミットは実機が担当。

## 読み取りレビュー結果（fetch なし・ローカル ref のみ）

| サブモジュール | 状態 | コミット | 備考 |
|---|---|---|---|
| `_creations-ai` | 親リポにコミット済みの確定状態 | `e86d7e5`（`heads/master`） | 前回ログ 20260614 時点の `51ec673` から前進済み |
| `_creations-db` | **作業ツリーに未チェックアウト** | — | `git submodule status` に現れず、ディレクトリも不在。`.gitmodules` には `develop` 追跡で宣言あり |

### `_creations-ai` `51ec673..e86d7e5` の内容

- 主体は `ai-dataset/` の再生成（`manifest.jsonl` / `manifest-training.jsonl` / `index.json` /
  `image-index.json` / 各 `works/Works_*.json`）と、`scripts/build-dataset.js` のオプトアウト判定強化
  （`isFullyDefaultOptedOut` を `allowed_db_keys` から除外）。
- 併せて submodule 内の `CLAUDE.md` / `AGENTS.md` / `copilot-instructions.md` / CI ワークフロー、
  サブモジュール自動チェック用 `tools/*.sh` の追加。
- 種別: **データ再生成＋ポリシー/ドキュメント更新**。親リポが依存するフィールド契約には変更なし。

### スキーマ整合チェック

- `manifest.jsonl` / `manifest-training.jsonl` のレコードキーは**旧 `51ec673` と新 `e86d7e5` で完全一致**。
  - 例（character レコード）: `_type, ai_hints, ai_training, data, db_source, has_ai_hints,
    has_immutable_constraints, has_negative_keywords, has_silhouette_notes, has_work_common, id, images,
    work_key, work_title_en, work_title_ja`
- `has_ai_hints` フィールド健在。親 `src/utils/dataset.py` の参照（`_type=="character"` かつ `has_ai_hints`）と整合。
- フィールド名・スキーマ・API・参照パス（`_creations-ai/ai-dataset/manifest.jsonl`）いずれも**無変更**。

## 行った最適化

- **不要と判断**。差分はデータ再生成とポリシー/ドキュメント更新に限られ、親リポ `src/` のプロンプト生成ロジックや
  参照スキーマ、`docs/*.md` の記述に影響する仕様変更がないため、`src/`・`docs/` への追従編集は行わない（過剰改変を回避）。
- `_creations-db` / `_creations-ai/ai-dataset/` への直接編集はなし（禁止事項遵守）。

## 更新したドキュメント

- 同期対象の `docs/*.md` 変更なし（CLAUDE.md「docs と指示書の同期ルール」表の該当条件に当てはまる仕様変更なし）。
- 本ログを新規作成（未コミット）。

## 次アクション（実機 = Windows でのみ）

1. タスク登録: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register-submodule-sync-task.ps1`
   （毎朝 09:00。時刻変更は `-Time 08:30` など）。登録後 `schtasks /Query /TN "100BeautiesLab_SubmoduleSync" /V /FO LIST` で確認。
2. 動作確認: まず `scripts\daily-submodule-sync.ps1 -DryRun`、問題なければ本実行。
3. `_creations-db` のチェックアウト要否を確認（`git submodule update --init --recursive`）。`develop` 追跡の枝分かれ有無も判定。
4. `_creations-ai` の `e86d7e5` ポインタを含む状態を、実機で `git add` / `git commit`（push は任意）。
   **本同期・コミットはサンドボックスからは実行しない。**

---

## 追記: 再レビュー（同日 11:17 UTC・イズナ）

- 同日 11:13 の初回レビュー後に再実行。**状態は完全に不変**を確認（重複作業なし）。
  - `_creations-ai` = `e86d7e5`（`heads/master`、親リポにコミット済み）— 前進なし。
  - 入れ子 `_creations-ai/creations-db` = `968f356`（`heads/develop-58-g968f356`）でチェックアウト済み。
    親 `_creations-ai` のバンプ `51ec673..e86d7e5` に内包される差分で、初回レビュー範囲に含まれる。
  - トップレベル `_creations-db`（`.gitmodules` 宣言）は未チェックアウトのまま（status に出現せず）。
- 実機 `daily-submodule-sync.ps1` 由来の自動生成ログは**本日もまだ未生成**。本ファイルは未追跡（`??`）の Cowork advisory。
- 親リポ作業ツリーに本日の新規同期コミットなし（最新は `abbed56`）。
- **最適化: 不要（再確認）**。スキーマ/フィールド/API/参照パスに影響する差分なし。`src/`・`docs/` への追従編集は行わない。
- `git add`/`commit`/`fetch` は不実行（環境制約遵守）。
