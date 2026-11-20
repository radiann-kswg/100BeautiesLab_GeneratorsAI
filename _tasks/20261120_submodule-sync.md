# サブモジュール同期ログ — 2026-11-20 16:50

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | b7ccb20 | 6f5b37d | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | f2d10b1 | f2d10b1 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` b7ccb20..6f5b37d

```
6f5b37d chore: sync ai-dataset (creations-db@f2d10b1f) 窶・ai_training allowed: 187 [skip ci]
4e9a69a chore: sync ai-dataset (creations-db@a4b1a43d) 窶・ai_training allowed: 187 [skip ci]
d8eb504 chore: sync ai-dataset (creations-db@fa10a498) 窶・ai_training allowed: 187 [skip ci]
f037968 fix: enforce AI opt-outs in dataset exports
fa26d38 chore: sync ai-dataset (creations-db@7849c017) 窶・ai_training allowed: 191 [skip ci]
b92e3a8 chore: sync ai-dataset (creations-db@211bff56) 窶・ai_training allowed: 191 [skip ci]
```

変更ファイル:

```
AGENTS.md                                          |   12 +
 ai-dataset/build-info.json                         |   18 +-
 ai-dataset/image-index.json                        | 7015 ++++++--------------
 ai-dataset/index.json                              |   20 +-
 ai-dataset/manifest-training.jsonl                 |  208 +-
 ai-dataset/manifest.jsonl                          | 1304 ++--
 ai-dataset/policy.json                             |   13 +-
 ai-dataset/works/Works_CommonReferences.json       |    2 +-
 ai-dataset/works/Works_DestinyFoxRecords.json      |  425 +-
 ai-dataset/works/Works_FLInvestigator78.json       |  145 +-
 ai-dataset/works/Works_NumberTales.json            | 5058 ++++----------
 ai-dataset/works/Works_PastDivers.json             |   25 +-
 ai-dataset/works/Works_ShauErRiders.json           |   12 +-
 ai-dataset/works/Works_SinisterChangingGirls.json  |   32 +-
 ai-dataset/works/Works_StardustVsKaleidoscope.json |    2 +-
 ai-dataset/works/Works_UnauthedLogica.json         |   15 +-
 ai-dataset/works/Works_UnibyteLive.json            |   85 +-
 ai-dataset/works/Works_VirtuesUs.json              |    2 +-
 creations-db                                       |    2 +-
 scripts/build-dataset.js                           |  185 +-
 scripts/lib/dataset-helpers.js                     |    5 +-
 scripts/lib/dataset-helpers.test.js                |    8 +
 scripts/lib/image-policy.test.js                   |  140 +
 scripts/lib/policy.js                              |   38 +-
 scripts/lib/policy.test.js                         |   18 +
 scripts/validate-dataset.js                        |  Bin 19493 -> 23100 bytes
 26 files changed, 4745 insertions(+), 10044 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

### 最適化メモ（2026-11-20、手動同期のあと。追従は未完了）

- 差分把握: `_creations-ai` `b7ccb20..6f5b37d`（creations-db `688a349..f2d10b1`）。manifest に `AppearanceDetail[].Detachable`、`Formation` の `afterChanged`・`normal`・`beasted`、`Costume` の `onBusiness`・`private`・`jacketless` が届いた。D-Vines の 4 件は不許可になり、61 のアイドル衣装の項目と画像は無くなった（許可 191→187 件）。
- **未解決の影響: 部位図（`AppearanceDetail[].img_PNGName`）が参照に入らなくなった。** CreationsAI `f037968`（AI オプトアウトの適用）から、`ai-dataset/image-index.json` が 763 件から 481 件に減り、`attr/` 配下は 144 件から 11 件になった。`attr_numberMarkNTS-93.png` などの部位図は、ファイルは `creations-db` にあるが索引に無い。`_collect_appearance_detail_images()` は索引に載った実名だけを通すので、空を返す。
- テスト結果: `tests/test_detail_references.py` の 15 件が失敗、ほかの 104 件は成功（Windows 実機、`PYTHONUTF8=1`、API キーは空）。
- 上流へ依頼済み: 意図しない除外だった（2026-11-20 ラジアン確認）。`attr` 画像を AI オプトアウトの対象にしないよう、[CreationsAI #4](https://github.com/radiann-kswg/100BeautiesLab_CreationsAI/issues/4) を立てた。原因は、許可の一覧が `Images.*` と `TailsUnit` の宣言だけから作られ、`img_PNGName` が宣言に数えられていないこと。上流の修正と再生成のあとに同期し直す。それまで、下流で `creations-db` のパスを直接たどる回避はしない（索引は AI に渡してよい画像の正典）。テストも書き換えていない。
- `state`・`Costume`・`Detachable` の追従（実装の順番の 2 番）は、ShapeChangerAI だけ済んだ。このリポジトリは未着手。

### 再同期（2026-11-20 17:40、CreationsAI #4 の修正の取り込み）

- 差分把握: `_creations-ai` `6f5b37d..64e951c`（creations-db は `f2d10b1` のまま）。`5177c6a` で `AppearanceDetail[].img_PNGName` が画像の宣言として許可の一覧に入り、`ai-dataset/image-index.json` は 481 件から 600 件、`attr/` 配下は 11 件から 130 件になった。manifest のレコード本文と許可件数（187 件）は変わらない。
- 影響判定: このリポジトリのコード変更は要らない。`_collect_appearance_detail_images()` は索引に載った実名を通すので、再生成された索引だけで部位図が戻る。`collect_reference_images()` で、93 の `attr_numberMarkNTS-93.png` と 57・61 の番号図が参照の先頭 3 枚に入ることを確かめた。
- 61 の扱い: 索引に戻った 61 の部位図は、通常衣装の項目が宣言する番号図・紋章と、尻尾ユニット。アイドル衣装の項目と画像 3 枚は、manifest にも索引にも無いまま。
- テスト結果: `tests/` の 128 件がすべて成功（Windows 実機、`PYTHONUTF8=1`、API キーは空、`OUTPUT_SINK=local`）。上の「未解決の影響」に書いた `tests/test_detail_references.py` の 15 件の失敗は解消した。
- 残ること: どのレコードも実名で宣言していない 10 件（`tailsUnit` の 7 件、28 の `earingBack`、SelfSecondary の `223-lot`・`753-lot`）は索引に載らない。使うには上流で宣言を足す（[CreationsAI #4](https://github.com/radiann-kswg/100BeautiesLab_CreationsAI/issues/4) のコメント）。
