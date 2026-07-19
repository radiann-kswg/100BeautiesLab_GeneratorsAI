# 上流提案 advisory — `_creations-ai/AGENTS.md` の `AI_Output` 誤記訂正

- 起票: 2026-07-19（57(イズナ) / creations-db 新機能適応タスク）
- 種別: 上流リポジトリ（`100BeautiesLab_CreationsAI`）への提案。**本リポジトリからは直接編集しない**
  （`_creations-ai` は別リポジトリのサブモジュールのため）。

## 事実

- `_creations-ai/AGENTS.md` L20 付近に「サブモジュールが `AI_Optout` / `AI_Output` を管理」という趣旨の記述がある。
- **`AI_Output` というフィールドは全 DB / manifest / policy.js に実在しない**（本リポジトリでも `grep -r AI_Output` で
  ヒットするのは散文の言及のみ、コード参照はゼロ）。実際に管理・畳み込みされているのは `AI_Optout`（権利軸）と
  `AI_Unready`（充填軸）で、`ai_training.{allowed, reason}` に反映される。

## 提案

- `_creations-ai/AGENTS.md` L20 の `AI_Output` の記述を削除し、実機構（`AI_Optout` 権利軸 / `AI_Unready` 充填軸 →
  `ai_training.allowed`）ベースへ訂正する。CreationsAI リポジトリ側で Issue / PR として対応してほしい。
- 併せて `_creations-ai/README.md` の旧記述（サブモジュールを「develop / addon-ai-tag」と併記、収録作品 8 件・
  旧 `#Works_Proxies` を含む等）も、最新（`addon-ai-tag` 追跡・10 作品・`#Works_DestinyFoxRecords` 統合済み）へ
  追従すると齟齬が減る（正確な最新は `CLAUDE.md` と `ai-dataset/index.json`）。

## 本リポジトリ側での対応（実施済み）

- 親リポジトリ `AGENTS.md` L279 と `src/utils/dataset.py` の docstring から `AI_Output` を除去し、実機構
  （`has_ai_hints` 列挙 + `ai_training.allowed` 軸判別 fail-closed ゲート）へ訂正済み。
- 生成入口の軸判別ゲート（`apply_generation_gate` / `generation_permitted`）を実装し、判定は上流 `policy.js` の
  `ai_training.{allowed, reason}` を「読むだけ」で再実装しない方針を明記した。

## 状態

- [ ] CreationsAI リポジトリで `_creations-ai/AGENTS.md` L20 の訂正を反映（上流作業）。
- [ ] （任意）`_creations-ai/README.md` の旧記述追従。
