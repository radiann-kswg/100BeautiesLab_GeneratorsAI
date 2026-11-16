# サブモジュール同期ログ — 2026-11-16 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 6379b94 | 318c8f4 | UPDATED | FF 取り込み完了 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 117e6cb | 9b9bbab | UPDATED | FF 取り込み完了 |

## 取り込んだ更新の内容

### `_creations-ai` 6379b94..318c8f4

```
318c8f4 chore: sync ai-dataset (creations-db@117e6cb3) 窶・ai_training allowed: 181 [skip ci]
4f594ed chore: sync ai-dataset (creations-db@15ac820a) 窶・ai_training allowed: 181 [skip ci]
```

変更ファイル:

```
ai-dataset/build-info.json                         |  6 +-
 ai-dataset/image-index.json                        | 14 +++-
 ai-dataset/index.json                              |  6 +-
 ai-dataset/manifest-training.jsonl                 | 26 ++------
 ai-dataset/manifest.jsonl                          | 74 +++++++++-------------
 ai-dataset/policy.json                             |  2 +-
 ai-dataset/works/Works_CommonReferences.json       | 10 +--
 ai-dataset/works/Works_DestinyFoxRecords.json      |  2 +-
 ai-dataset/works/Works_FLInvestigator78.json       |  2 +-
 ai-dataset/works/Works_NumberTales.json            | 16 ++++-
 ai-dataset/works/Works_PastDivers.json             |  2 +-
 ai-dataset/works/Works_ShauErRiders.json           |  2 +-
 ai-dataset/works/Works_SinisterChangingGirls.json  |  2 +-
 ai-dataset/works/Works_StardustVsKaleidoscope.json |  2 +-
 ai-dataset/works/Works_UnauthedLogica.json         |  2 +-
 ai-dataset/works/Works_UnibyteLive.json            |  2 +-
 ai-dataset/works/Works_VirtuesUs.json              |  2 +-
 creations-db                                       |  2 +-
 18 files changed, 85 insertions(+), 89 deletions(-)
```

### `_creations-ai/creations-db` 117e6cb..9b9bbab

```
9b9bbabb Merge pull request #57 from radiann-kswg/auto/aihints-structural-resync
a2f7ee2c AIHints: 讒矩逧・・蜷梧悄・郁・蜍慕函謌撰ｼ・
```

変更ファイル:

```
.../DataBases/db_SelfSecondary.json                  | 20 ++++++++++----------
 data/Works_NumberTales/DataBases/db_SemiPrimary.json | 14 ++++----------
 2 files changed, 14 insertions(+), 20 deletions(-)
```

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

## 追従最適化レビュー — 2026-11-16 (Claude Code / 57 イズナ)

### 追加の手動同期

- 朝の自動同期後に `CreationsAI@master` が `ebc5cde`（`sync ai-dataset (creations-db@9b9bbabb)`）へ進んでいたため、`_creations-ai` を `318c8f4 → ebc5cde` へ FF で取り込み。
- これで `_creations-ai` の記録 gitlink（旧 `117e6cb`）と `creations-db` 作業ツリー（`9b9bbab`）のずれ（親リポの ` m _creations-ai`）が解消。

### レビュー範囲

前回レビュー（2026-11-10）以降の未レビュー分をまとめて確認: `_creations-ai` `2a518ce..ebc5cde` / `creations-db` `65084c6..9b9bbab`（11-11 / 11-13 / 11-14 / 11-15 / 11-16 のログ分）。

### 上流の仕様変更と判定

| 上流の変更 | `src/` への影響 | 対応 |
|---|---|---|
| `$Def_TailsUnit.Count` が `#Number` → `#Number\|#Null`（888 / 999 は `Count: null`、111-mp は `Count: 1` + `Segment: 3`） | あり。`_describe_tails_unit_entry()` は null で落ちないが、EN 文だけ「本数があるときしか節数・分岐を出さない」構造で、null 許容化により情報が黙って消える経路になっていた | **修正**: `src/utils/dataset.py` で EN の本数・節数・分岐を独立に組み立てる。`tests/test_tails_unit_labels.py` を実データ形状（`Count: null`）へ更新し、節数独立のケースを追加 |
| グローバル `Class` 辞書 12 本を `data/Dictionaries/Class/` へ移動（`dictFile` 宣言） | なし。`src/` は `Dictionaries/` を直接読まない。`pkg/python` クライアントは上流側で `dictFile` 対応済み（サブモジュール内） | 不要 |
| `scopeField` の構造化形式（`{ "Belonging": { "Faction": … } }`）許容 | なし。`src/` は `scopeField` を解釈しない | 不要 |
| `管理主` → `『管理主』` 改名（`dict_Faction` / `ref_Vocabulary` / 関連レコードの `Belonging`） | なし。`src/` に該当文字列の参照なし。参照資料レコードの `id` が変わるのみ | 不要 |
| 729-sxp / 1000 の `FormalName_*` が複数行に、`ModelName_*` 文言変更 | なし。複数行 `FormalName` は既存（2-alt / 100 / 369）と同形 | 不要 |
| 558-numberize に連名画像 `art_NTS-558ZE-corefolder,DFR-G3-weakening.png` 追加 | なし。バッジ判定は `558ZE` のみに厳密一致（`558` / `558MP` / `3` へ混入しないことを実測）。レコード自体は権利軸 `AI_Optout` で生成拒否 | 不要 |
| `SOUL.md` 追加（両リポ）、他作品の辞書・DB 推敲 | なし（ドキュメント / 生成対象外の作品） | 不要 |

- manifest スキーマ: キー集合は旧新で完全一致（深さ 3 まで比較）。`character` レコードは 740 件で増減なし（`管理主` の `id` 改名 1 件のみ）。
- 検証: `python -m pytest tests/` 91 件通過。実 manifest で 888 / 999 / 111-mp / 22 / 57 の尾の構造文を確認。

### 上流への申し送り（未対応・要判断）

- **manifest の `dictionary` レコードが 22 → 10 本に減少。** `_creations-ai/scripts/build-dataset.js`（「3. GeneralImages / Dictionaries / References」節）が `data/Dictionaries/` 直下の `*.json` しか読まず、`Class/` サブフォルダへ移った 12 本を拾えていない。`manifest-training.jsonl` からも同じ 12 本が落ちている。
- `src/` は `_type == "character"` しか使わないため GeneratorsAI の生成には影響なし。ただし manifest を直接読む他の消費者からは Class 辞書（`Class` ↔ `Class_EN` 対訳）が見えなくなる。
- 修正は CreationsAI 側（`db_meta.json` の `dictFile` を辿る、またはサブフォルダを再帰）で行う必要があり、本リポジトリからは `ai-dataset/` を手編集しない。


### 追記: `dictionary` レコード欠落の解消（`_creations-ai` `ebc5cde → 7cd5819`）

- 上記の申し送りは CreationsAI 側で修正・push 済み（`7cd5819` `fix: Dictionaries/ のサブフォルダ配下の辞書を manifest へ出力する`）。`build-dataset.js` が `data/Dictionaries/` を再帰で拾うようになり、`validate-dataset.js` に「`dictionary` レコードが `Dictionaries/` 配下の全 JSON と一致するか」の回帰チェックが入った。
- manifest の差分は `manifest.jsonl` / `manifest-training.jsonl` への `dictionary` 12 行追加のみ（10 → 22 本）。`character` 740 件（許可 181）とその他の出力は不変。内部の `creations-db` は `9b9bbab` のまま。
- `src/` への影響: なし（追従不要）。`src/utils/dataset.py` は `_type == "character"` のレコードだけを使い、`dictionary` レコードを読まない。
- 検証: CreationsAI 側 `npm test` 36 件通過・`node scripts/validate-dataset.js` OK。本リポジトリ `python -m pytest tests/` 91 件通過。
