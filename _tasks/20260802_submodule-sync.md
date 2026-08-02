# サブモジュール同期ログ — 2026-08-02 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。
> **自動実行は stale な `index.lock` により全 SKIP。同日中に手動で同期を完了させた（下記「手動リカバリ」）。**

## フェッチ・判定結果（自動実行 09:00 — 失敗）

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 189ce38 | e5fb2b3 | SKIP | checkout 失敗 (master): `fatal: Unable to create '.git/modules/_creations-ai/index.lock': File exists.` |
| `_creations-ai/creations-db` | origin/addon-ai-tag | e1248de | 63ad492 | SKIP | checkout 失敗 (addon-ai-tag): `fatal: Unable to create '.git/modules/_creations-ai/modules/creations-db/index.lock': File exists.` |

`index.lock` は既に終了した git プロセスの残骸で、実行中プロセスは存在しなかった。
**全 SKIP でもスクリプトは成功したように見える**点に注意（判定列を必ず確認すること）。

## 手動リカバリ（同日）

`index.lock` の消失を確認したうえで `git submodule update --remote --recursive --merge` を実行。
取り込み作業中に上流がさらに前進したため、**再フェッチして最新まで追従**した（下表は最終到達点）。

| サブモジュール | 追跡先 | 旧 | 新 | 判定 |
|---|---|---|---|---|
| `_creations-ai` | origin/master | 189ce38 | 531785f | UPDATED |
| `_creations-ai/creations-db` | origin/addon-ai-tag | e1248de | 66a6563 | UPDATED |

## 取り込んだ更新の内容

### `_creations-ai/creations-db` e1248de..66a6563

```
66a6563 Merge branch 'develop' into addon-ai-tag
f7a803a DB構造大幅整理 bugfixその3-2
a0ce865 DB構造大幅整理 bugfixその3-1
a1316e3 Merge pull request #18 from radiann-kswg/auto/aihints-structural-resync
3746ae2 AIHints: 構造的再同期（自動生成）
660d550 Merge branch 'develop' into addon-ai-tag
4299486 DB構造大幅整理 refactor その２
5b7e931 DB構造大幅整理 refactor その1-3
0e9a723 DB構造大幅整理 refactor その１続き
c80bc85 DB構造大幅整備 refactor その１
778003e UI大幅拡張 その５＆DB構造整備 その３
```

**画像ファイル名の一括改名（本同期の主変更）**

上流ログ: `_work_in_progress/2026-08-02_progress_image-rename-index-badge.md`

- 画像ファイルの `git mv` **640 件**（NumberTales 574 / DFR 28 / FLI 12 / SAR 12 / SCG 10 / PDV 2 / UBL 2）
- JSON の画像参照の張り替え **733 箇所 / 12 ファイル**
- 識別子部分を**インデックスバッジの `full` 表記**（`Works_Code` + `-` + バッジ本体）へ統一

```
cnsp_img57.png           →  cnsp_imgNTS-57.png
cnsp_img2-alt.png        →  cnsp_imgNTS-2B.png
attr_numberMark10alt.png →  attr_numberMarkNTS-10D.png
cnsp_img67-A.png         →  cnsp_imgNTS-67B.png   ← 旧 A/B とバッジの A/B が逆転していた
art_img56,65-corefolderA.png → art_imgNTS-56,NTS-65-corefolderA.png  (連名)
```

その他: 相関図ページ（`pages/relations.*` / `lib/graph/*`）新設、`data/db_meta.json` に `Works_Code`、
`db_type.json` に `$IndexDef.$badge` / `$display.facet` 宣言追加。

**追加取り込み分（a1316e3..66a6563 / bugfix その3-1・3-2）**

- 拡張子 `.PNG` → `.png` の正規化 9 件、`attr_numberMarkNTs-223-lot` → `NTS-` のタイポ修正 1 件
- `cnsp_imgNTS-115RZ-image.png` を `DB_SelfSecondary` → `DB_Secondary` へ移動
- `tests/data.image-links.test.js` 新設（画像リンク切れの回帰テスト）
- **`data/Works_NumberTales/DataBases/db_Primary.json` は無変更** ＝ Primary の `Num_Badge` は不変

### `_creations-ai` 189ce38..531785f

`ai-dataset/` の再生成（`manifest.jsonl` / `image-index.json` / `works/*.json` の画像パスが新命名へ追従）。

`994a3a4 Update AI dataset for addon-ai-tag changes: 画像ファイル名の一斉リネーム追従と画像フィールド解決の修正`
で上流側の画像パス解決も整理された（`build-dataset.js` の `IMAGE_FIELDS` を唯一の正典化。
`conceptAlt_PNGName` の格納先取り違えで 22 件が静かに落ちていた不具合を解消）。
結果 `build-info.json` の `image_ref_stats` は **resolved 631 / unresolved 0**。

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

**判定: 追従必要（実施済み）。** 参照画像のキャラクター同定が番号の部分一致だったため、新命名で破綻していた。

修正前の実測（NumberTales 92 キャラ × 2 形態）:

| 指標 | 修正前 | 修正後 |
|---|---:|---:|
| 参照画像 合計 | 471 件 | 445 件 |
| **他キャラの画像の混入** | **32 件** | **0 件** |
| 参照画像 0 件の形態スロット | 2 件 | 0 件 |

破綻の内訳:

- `Num:"2-alt"`（バッジ `2B`）がファイル名に `2-alt` を含まなくなり、humanoid の参照画像を全て喪失
- `Num:2` の部分一致が `NTS-2B`（2-alt）と接尾辞 `-2`（`NTS-000-2` / `NTS-1-2` / `NTS-10-2` / `NTS-12-2`）を拾い他キャラが混入
- `Num:67` と `Num:"67-old"` がバッジ `67A` / `67B` に分かれ、互いの画像を取り違え
- `Num:"67-old"` / `Num:"10-alt"` も同様に参照画像を喪失

対応:

- `src/utils/dataset.py` — ファイル名からバッジを読み取りレコードのバッジと厳密一致させる方式へ変更。
  バッジ切り出しは作品内バッジ語彙との**最長前方一致**（`NTS-2B` → `2B`、`NTS-57RZ` → `57`）。
  DB 由来のパスは旧命名の部分一致へフォールバック、ディレクトリ総当たり収集はバッジ必須（`require_badge`）。
  `collect_record_capabilities()` に `character_badge` を追加（`run_meta.json` から追える）。
- `src/pipeline/db_collector.py` — `db_summary.json` に `num_badge` を追加。
- `tests/test_badge_reference_images.py` — 新規。最長前方一致・接尾辞除外・連名・`require_badge` の分岐、
  および全キャラで他キャラ混入 0 件を実データ検証。
- `docs/tools.md` / `docs/output-and-logs.md` / `AGENTS.md` — 命名規則と追従方針を記載。

補足: `RoleplayPrompts/` のファイル名は改名対象外のため `src/roleplay/` 側の追従は不要（差分なしを確認）。
