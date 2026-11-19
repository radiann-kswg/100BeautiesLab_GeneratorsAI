# サブモジュール同期ログ — 2026-11-18 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 7cd5819 | d4ac56f | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 272d513 | 272d513 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

### `_creations-ai` 7cd5819..d4ac56f

```
d4ac56f chore: sync ai-dataset (creations-db@272d5130) 窶・ai_training allowed: 185 -> 181 [skip ci]
ef5ab0e chore: sync ai-dataset (creations-db@63701e98) 窶・ai_training allowed: 181 -> 185 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                         |  22 +-
 ai-dataset/image-index.json                        |  54 ++-
 ai-dataset/index.json                              |  10 +-
 ai-dataset/manifest-training.jsonl                 |  58 +--
 ai-dataset/manifest.jsonl                          |  94 +++--
 ai-dataset/policy.json                             |   2 +-
 ai-dataset/works/Works_CommonReferences.json       |  50 +--
 ai-dataset/works/Works_DestinyFoxRecords.json      |   2 +-
 ai-dataset/works/Works_FLInvestigator78.json       |   2 +-
 ai-dataset/works/Works_NumberTales.json            | 430 ++++++++-------------
 ai-dataset/works/Works_PastDivers.json             |   2 +-
 ai-dataset/works/Works_ShauErRiders.json           |   2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json  |   2 +-
 ai-dataset/works/Works_StardustVsKaleidoscope.json |   2 +-
 ai-dataset/works/Works_UnauthedLogica.json         |   2 +-
 ai-dataset/works/Works_UnibyteLive.json            |   2 +-
 ai-dataset/works/Works_VirtuesUs.json              |   2 +-
 creations-db                                       |   2 +-
 18 files changed, 334 insertions(+), 406 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

### 11月18日 JST のローカル確認

- `7cd5819` と `d4ac56f` の manifest と画像インデックスを比較した。レコードと画像エントリの項目・型が既存の読み込み形式に収まっており、生成候補は128件から132件、画像の索引パスは758件から762件に増えた。今のデータを読み込むための `src/`・`docs/` の追従修正は不要。
- 追加された Dv3・Dv7・Dv8・Dv22 は、API を使わずにバッジ解決、画像生成の可否判定、出力パスの組み立てを確認した。Dv7・Dv22 はローカル参照画像を解決できた。Dv3・Dv8 は上流に画像と形態別 AIHints の登録がない。生成結果の品質とリモート API は未検証。
- オフラインの回帰テストは88件成功。バッジと参照画像のテスト2件は `10-alt` のローカル検索で失敗し、同期前の manifest と画像インデックスでも再現した。両版の manifest で `10-alt` は `AI_Unready` かつ `allowed=false` のため、許可済みレコードの列挙から外れる。MCP のログ切り替えテスト1件は、この環境の Windows asyncio がループバックソケットの初期化で停止したため、単独で原因を確認して集計から除外した。

