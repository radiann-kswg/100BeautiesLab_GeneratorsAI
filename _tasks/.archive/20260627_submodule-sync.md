# サブモジュール同期ログ（Cowork レビュー） — 2026-06-27

> Cowork 自動タスク `daily-submodule-sync-optimize`（Claude=イズナ）による**読み取りレビュー＋src追従**記録。
> 本ファイルはサンドボックスから作成した未コミットの advisory。`git add`/`commit`/`fetch`・ロック削除は一切行っていない。
> git 同期・コミットは実機 `scripts/daily-submodule-sync.ps1`（Windows タスクスケジューラ）が担当。

## 実行サマリ

- **実機の日次 submodule 追従コミットが本日出ている**（＝実機スクリプト稼働を確認）:
  - 親リポ HEAD: `4b7d379`（前回ログ 0626）→ `53d9bc2`（**0627 の追従コミット**）。
  - `53d9bc2 chore(submodule): _creations-ai を master(40fc2f9) に追従、creations-db を 53d1c0b に更新`
  - 間に実機自開発の mcp-server コミット 3 件（`81d54e5` list_gcs_logs / `d826360` get_gcs_image / `bd79e08` doc 削除）も入っている。
- **サブモジュール両方 UPDATED**:
  - `_creations-ai`（親の記録ポインタ）: `d2763fa` → `40fc2f9`（heads/master）
  - 入れ子 `creations-db`（_creations-ai の記録）: `6df9d27` → `53d1c0b`（origin/addon-ai-tag）
  - `_creations-ai/ai-dataset/build-info.json`: `generated_at = 2026-06-27T12:06:28+09:00` / `submodule_commit = 53d1c0b`（**再生成済み・DRIFT なし**）
  - 作業ツリー submodule status はプレフィックスなし＝記録ポインタと一致・クリーン。

---

## 読み取りレビュー結果

| 対象 | 前回(0626) | 現状(0627) | 状態 |
|---|---|---|---|
| 親リポ HEAD | `4b7d379` | `53d9bc2` | UPDATED（submodule 追従1件＋実機自開発 mcp-server 3件） |
| `_creations-ai`（記録ポインタ） | `d2763fa` | `40fc2f9` | **UPDATED** |
| 入れ子 `creations-db` | `6df9d27` | `53d1c0b` | **UPDATED** |
| ai-dataset 再生成 | 0625 17:12 | **0627 12:06** | 再生成済み（DRIFT なし） |

### 取り込まれた差分の内容

**creations-db `6df9d27..53d1c0b`（36 ファイル / +1787 -523）** — 主な内容:
- DB 内部再構成: `data/db_type.json` 削除 → `data/db_meta.json` 新設（リネーム/再構成）。
- Cloudflare worker 整備（`pkg/cloudflare/worker.js` 新規 +472、`wrangler.toml`）、`pages/characters.js`、テスト追加。
- 語彙・参照データ更新（`ref_Vocabulary.json` 各作品、`ref_Region8.json` 等）。
- 進捗doc `2026-06-27_progress_design-part-schema.md`（**「機能提案（未実装）」**— `designParts`/`AppearanceDetail` 統合スキーマの将来構想。現行スキーマ未変更）。
- AGENTS.md / CLAUDE.md / roleplay 設定の整備。

**_creations-ai `d2763fa..40fc2f9`** — 上記 creations-db へのポインタ追従＋ai-dataset 再生成（works/manifest/policy/training の**値**更新）、submodule 内の指示書類（copilot-instructions / CLAUDE.md / roleplay）整備。

### 消費契約への影響判定（src が読む ai-dataset スキーマ）

読み取り専用で旧↔新のキーパス集合を比較し、**全て構造不変**を確認:
- `ai-dataset/manifest.jsonl`: 行数 455→455、トップレベル＆全キーパス集合**差分ゼロ**（値更新のみ）。
- `ai-dataset/works/Works_*.json`（9作品）: 全キーパス集合**差分ゼロ**。
- `ai-dataset/policy.json` / `manifest-training.jsonl`: キーパス**差分ゼロ**。
- src は `ai-dataset/`（`manifest.jsonl` 経由、`utils/dataset.py` / `pipeline/db_collector.py` / `natural_parser.py`）のみを消費し、**creations-db 内部ファイル（db_type/db_meta 等）には非依存**。`db_type.json→db_meta.json` リネームは ai-dataset に伝播していない。
- docs 内の creations-db パス言及は `docs/output-and-logs.md:90` / `docs/setup.md:225` の 2 箇所のみ（`creations-db/data/.../Images/...` の画像パス例とサブモジュール初期化ガイド）。今回のリネーム（`db_type.json`）は data ルート直下の型定義であり、これら画像/初期化パスの記述には影響なし。

---

## 行った最適化（src / docs 追従）

- **最適化不要と判断（編集なし）。**
  - サブモジュールは UPDATED だが、**ai-dataset の消費スキーマ（フィールド名・キーパス・参照パス契約）は完全不変**。値の更新のみで src の解釈に変更を要しない。
  - creations-db の `db_type.json→db_meta.json` 再構成・Cloudflare worker 整備は **DB/配信側の内部事情**であり、親リポ src の消費面に契約変更を生じない。
  - design-part-schema は**未実装の機能提案**。現行 ai-dataset に新フィールドを足していないため src 追従は時期尚早（実装着手時に再評価）。
  - CLAUDE.md「docs と指示書の同期ルール」表に該当する追従先なし → `docs/*.md` も無編集。
  - 禁止事項遵守: `_creations-ai/creations-db` / `_creations-ai/ai-dataset/` への直接編集なし。過剰改変回避。

---

## 残課題 / 要・実機対応（コミットは実機で）

1. **実機 daily-submodule-sync は本日稼働を確認**（追従コミット `53d9bc2` を観測）。継続観察のみで追加対応不要。
2. **design-part-schema（未実装提案）を監視対象に追加**: 将来 `designParts`/`AppearanceDetail` が DB→ai-dataset に実装・伝播した時点で、`src/utils/dataset.py`（`silhouette_notes`/`immutable_constraints` 抽出系）と `docs/usage-generation.md` のプロンプト構造節へ追従が必要になる可能性。実装着手の合図が来たら再レビュー。
3. `has_concept_forms_metadata` フラグは依然 src 未消費（非ブロッキング・継続）。build-info の `with_concept_forms_metadata = 91`。
4. **本 advisory は読み取りのみ。** サンドボックスからの `git add`/`commit`/`fetch`・ロック削除は絶対に行わない（CRLF↔LF 全行差分・index.lock 削除不可で全リポ破壊リスク）。push 状況は実機で確認。

---

## 環境メモ

- サンドボックス git は `GIT_OPTIONAL_LOCKS=0` を付与した読み取り専用操作（`log` / `show` / `diff --stat` / `submodule status` / jq キーパス比較）のみで実施。**ロック削除は厳禁**。
- minified JSONL の生 diff は巨大化するため、構造判定は `jq '[paths|join(".")]'` のキーパス集合比較で実施（値差分はノイズとして除外）。
