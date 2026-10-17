# サブモジュール同期ログ — 2026-10-13 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | ea4768c | 1a0c7d4 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | ad03409 | ad03409 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` ea4768c..1a0c7d4

```
1a0c7d4 chore: sync ai-dataset (creations-db@ad03409d) 窶・ai_training allowed: 172 [skip ci]
ed491a5 chore: sync ai-dataset (creations-db@8ab0fc97) 窶・ai_training allowed: 172 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                        | 10 +++---
 ai-dataset/image-index.json                       | 38 +++++++++++++++++++---
 ai-dataset/index.json                             | 12 +++----
 ai-dataset/manifest-training.jsonl                | 30 ++++++++---------
 ai-dataset/manifest.jsonl                         | 39 ++++++++++++-----------
 ai-dataset/policy.json                            |  2 +-
 ai-dataset/works/Works_CommonReferences.json      |  2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json     |  2 +-
 ai-dataset/works/Works_FLInvestigator78.json      |  2 +-
 ai-dataset/works/Works_NumberTales.json           | 23 ++++++++++++-
 ai-dataset/works/Works_PastDivers.json            |  2 +-
 ai-dataset/works/Works_ShauErRiders.json          |  2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json |  2 +-
 ai-dataset/works/Works_UnauthedLogica.json        |  2 +-
 ai-dataset/works/Works_UnibyteLive.json           | 12 ++++++-
 ai-dataset/works/Works_VirtuesUs.json             |  2 +-
 creations-db                                      |  2 +-
 17 files changed, 123 insertions(+), 61 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

### 追従確認 — 2026-10-17

- **確認対象:** creations-db `8ab0fc97` の合同画像 `AI_Optout` OR 判定、および生成同期コミット `ed491a5` の manifest / image-index 反映。上流では、DB または `_Secondaries` カテゴリの opt-out レコードが `Images.*`（`_DBCrossLinkPath` を含む）で参照する画像を、opt-in 側の AIHints 参照画像からも除外する。
- **確認結果:** Stage 2 は `apply_generation_gate()` を参照画像収集より先に実行し、判定は manifest の `ai_training.allowed/reason` を読む。`collect_reference_images()` は AIHints の `common/forms.*.reference_images` を収集するため、上流で除外された AIHints 参照はこの経路へ渡らない。生成ゲート自体はキャラクターレコード単位の既存判定で、今回 src 側に判定ロジックを追加する変更は不要。
- **確認範囲と留意点:** `collect_reference_images()` は AIHints だけでなく manifest の `images`、image-index 由来の候補も別経路で収集する。今回の上流変更は AIHints 参照の除外として確認したもので、これら別経路の合同画像まで同じ OR 判定で除外されることは、この差分と src の確認だけでは確認できない。したがって、本追記は実装不具合の断定ではなく、確認済みの適用範囲を記録するもの。
- **追従要否:** manifest の policy 判定や AIHints 参照の読み込みにスキーマ/API 変更はなく、これらの処理に対する `src/` / `docs/` の追従変更は不要。別経路の候補まで同じ除外を要求する場合は、意図とデータ経路を別途確認する。
