# サブモジュール同期ログ — 2026-07-19 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | f4eb76f | 8e9af22 | SKIP | checkout 失敗 (master): git.exe : fatal: Unable to create 'C:/Visual Studio Code UserFile/100BeautiesLab_GeneratorsAI/.git/modules/_creations-a i/index.lock': File exists. 発生場所 C:\Visual Studio Code UserFile\100BeautiesLab_GeneratorsAI\scripts\daily-submodule-sync.ps1:52 文字:17 +         $out = (& git @GitArgs 2>&1 / Out-String) +                 ~~~~~~~~~~~~~~~~~~~     + CategoryInfo          : NotSpecified: (fatal: Unable t...': File exists.:String) [], RemoteException     + FullyQualifiedErrorId : NativeCommandError    Another git process seems to be running in this repository, e.g. an editor opened by 'git commit'. Please make sure all processes are terminated then try again. If it still fails, a git process may have crashed in this repository earlier: remove the file manually to continue. |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 50e7ee1 | 50e7ee1 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

今回取り込んだ更新はありません。

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

---

## 手動追記 — 2026-07-19 (57(イズナ) / creations-db 新機能適応タスク)

### スクリプト実行時の `index.lock` 障害と復旧
- 本実行時、以前クラッシュした git プロセスの残骸ロック（`.git/index.lock` および `.git/modules/_creations-ai/index.lock`、いずれも 0 バイト・08:05:35 生成）が残っており、`_creations-ai` の checkout が失敗し上表で **SKIP** と記録された。
- 稼働中の git プロセスが無いことを確認のうえ両ロックを除去し、`_creations-ai` を **f4eb76f → 8e9af22（master, FF）** へ手動で追従。ネストの `creations-db` は `8e9af22` が固定する **50e7ee1** と一致（`submodule update --init --recursive` 済み）。
- したがって最終状態は `_creations-ai@8e9af22` / `creations-db@50e7ee1`。上表の `_creations-ai` SKIP はロック障害時点の記録であり、実体はFF完了済み。

### 取り込んだ主な差分（8e9af22 / 50e7ee1）
- **ロールプレイプロンプト生成機能（2026-07-19 addon-ai-tag）**: 上流 `tools/build-roleplay-prompts.mjs` が `ConversationPattern` 等からキャラ単位のロールプレイプロンプト Markdown を生成。各レコードに `roleplay_prompt:{path}`（本文非埋め込み・パス参照のみ）＋ `has_roleplay_prompt` フラグを添付。`build-info.json` の `roleplay_prompt_stats.with_roleplay_prompt=49`。**本文の採否は `ai_training` ゲートに従う（`manifest.jsonl` は allowed=false でも path 付き、training は許可レコードのみ）。フォルダ一括読みは漏洩事故のため厳禁**。
- `policy.json` / `build-dataset.js` の AIオプトアウトすり合わせロジック更新（軸判別: 権利軸 `AI_Optout` vs 充填軸 `AI_Unready`）。

### 追従最適化: 着手中（別タスク）
- `src/` 側の適応（新API `?form=` 取り込み・`ai_training.allowed` 軸判別ゲート・生成済み `roleplay_prompt.path` の消費・幽霊フラグ `AI_Output` 記述訂正）を実施中。計画は承認済み。

