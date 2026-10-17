# サブモジュール同期ログ — 2026-10-08 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | add4084 | b4551e0 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 9efb0d0 | 9efb0d0 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` add4084..b4551e0

```
b4551e0 chore: sync ai-dataset (creations-db@9efb0d0b) 窶・ai_training allowed: 164 -> 172 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        |  18 ++--
 ai-dataset/image-index.json                       |  38 ++++++--
 ai-dataset/index.json                             |  18 ++--
 ai-dataset/manifest-training.jsonl                |  47 ++++++----
 ai-dataset/manifest.jsonl                         | 101 ++++++++++++----------
 ai-dataset/policy.json                            |   2 +-
 ai-dataset/works/Works_CommonReferences.json      |  10 +--
 ai-dataset/works/Works_DestinyFoxRecords.json     |   2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |   2 +-
 ai-dataset/works/Works_NumberTales.json           |  16 +++-
 ai-dataset/works/Works_PastDivers.json            |   2 +-
 ai-dataset/works/Works_ShauErRiders.json          |   2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |  34 ++++++--
 ai-dataset/works/Works_UnauthedLogica.json        |   2 +-
 ai-dataset/works/Works_UnibyteLive.json           |   2 +-
 ai-dataset/works/Works_VirtuesUs.json             |   2 +-
 creations-db                                      |   2 +-
 17 files changed, 186 insertions(+), 114 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。


## 差分レビュー結果 — 2026-10-08 (Cowork / 57 イズナ)

- **判定: src/ ・ docs/ への追従最適化は不要。**
- 取り込み差分 `add4084..b4551e0` はデータ内容のリフレッシュのみ (ai_training allowed 164 -> 172 / total_characters 713 -> 718)。
- スキーマ非変更を確認: `manifest-training.jsonl` のヘッダ/キャラクタエントリのキー集合、`Works_*.json` 上位キー、`index.json` キーはいずれも旧→新で完全一致。フィールド名・API・参照パス・`Works_*.json` の version いずれも変更なし。
- よって AGENTS.md「docs と指示書の同期ルール」表のトリガー該当なし。過剰改変を避け編集は行わない。
- リモート状況 (GitHub コネクタ読み取り): CreationsAI `master` HEAD=b4551e0 / CreationsDB `addon-ai-tag` HEAD=9efb0d0 で、ローカルのサブモジュール HEAD と一致。次回同期待ちの未取り込み更新なし。
- 留意点: `build-info.json` の `image_ref_stats.unresolved` が 0 -> 2 に変化。これはデータセット側 (`_creations-ai/ai-dataset/`) のビルド品質シグナルであり、当リポの src/docs スキーマには無影響。直接編集対象外のため本タスクでは記録のみ。
