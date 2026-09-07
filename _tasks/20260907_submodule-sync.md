# サブモジュール同期ログ — 2026-09-07 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 4ab3b15 | 5cbcf34 | SKIP | checkout 失敗 (master): git.exe : fatal: Unable to create 'C:/Visual Studio Code UserFile/100BeautiesLab_GeneratorsAI/.git/modules/_creations-a i/index.lock': File exists. 発生場所 C:\Visual Studio Code UserFile\100BeautiesLab_GeneratorsAI\scripts\daily-submodule-sync.ps1:52 文字:17 +         $out = (& git @GitArgs 2>&1 / Out-String) +                 ~~~~~~~~~~~~~~~~~~~     + CategoryInfo          : NotSpecified: (fatal: Unable t...': File exists.:String) [], RemoteException     + FullyQualifiedErrorId : NativeCommandError    Another git process seems to be running in this repository, e.g. an editor opened by 'git commit'. Please make sure all processes are terminated then try again. If it still fails, a git process may have crashed in this repository earlier: remove the file manually to continue. |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 7967612 | b7acebb | SKIP | checkout 失敗 (addon-ai-tag): git.exe : fatal: Unable to create 'C:/Visual Studio Code UserFile/100BeautiesLab_GeneratorsAI/.git/modules/_creations-a i/modules/creations-db/index.lock': File exists. 発生場所 C:\Visual Studio Code UserFile\100BeautiesLab_GeneratorsAI\scripts\daily-submodule-sync.ps1:52 文字:17 +         $out = (& git @GitArgs 2>&1 / Out-String) +                 ~~~~~~~~~~~~~~~~~~~     + CategoryInfo          : NotSpecified: (fatal: Unable t...': File exists.:String) [], RemoteException     + FullyQualifiedErrorId : NativeCommandError    Another git process seems to be running in this repository, e.g. an editor opened by 'git commit'. Please make sure all processes are terminated then try again. If it still fails, a git process may have crashed in this repository earlier: remove the file manually to continue. |

## 取り込んだ更新の内容

自動同期は `index.lock` の残骸で SKIP したが、手動で取り込み直した（既知の停止パターン）。

| サブモジュール | 旧 | 新 |
|---|---|---|
| `_creations-ai` | 4ab3b15 | b80aba2 |
| `_creations-ai/creations-db` | 7967612 | 12ae350 |

CreationsAI [Issue #1](https://github.com/radiann-kswg/100BeautiesLab_CreationsAI/issues/1) の
データセット側 3 依頼が完了した断面。実測での変化:

| 項目 | 変化 |
|---|---|
| `corefolder` の長辺中央値 | 479px → **1554px**（196 枚すべて 1024px 以上・最小 1235px） |
| 原寸相当（長辺 1024px 以上） | 355/728 → **482/631**（NT 作品分） |
| NumberTales の許可レコードの `ai_hints` 保持 | 91/113 → **113/113** |
| `image-index.json` の配列要素 | 文字列 → オブジェクト（**破壊的変更**） |
| レコード追加フィールド | `preferred_reference_images` / `ai_hints_source` |

## 最適化メモ

[GeneratorsAI#20](https://github.com/radiann-kswg/100BeautiesLab_GeneratorsAI/issues/20) として追従済み。

### 依頼1: `get_characters()` の References 除外 — 対応不要（既済）

2026-08-29 の変更（`db_source` が `data/References/` 始まりのレコードを型で除外 + `ai_training.allowed`）で
すでに満たしている。実測でも NumberTales の許可レコード 113 件は **113/113 が `ai_hints` を保持**し、
References の混入は 0 件。回帰は `tests/test_style_reference_fixes.py::test_get_characters_excludes_references_but_keeps_semiprimary` が保持。
ただし `AGENTS.md` と `numbertales-imagegen` スキルに旧 `has_ai_hints` フィルタの記述が残っていたので訂正した。

### 依頼2: `image-index.json` のオブジェクト化 — 追従済み（**実害あり**）

`get_local_image_paths()` が `WindowsPath / dict` で `TypeError` 落ちしていた（唯一の image-index 消費者）。
`_index_entry_path()` を挟んで新旧どちらの形式でも読めるようにした。
`collect_reference_images()` 系はレコードの `images` 経由なので影響なし。

### 依頼3: `_infer_image_category` のヒューリスティック撤去 — 追従済み（挙動差分ゼロ）

種別・解像度の正典を上流 `category` / `is_large_original_candidate` へ移した（`_image_category` / `_image_meta`）。
パス名推定は**索引外のパス専用のフォールバック**へ後退（`Ref_Glossary/` の作品共通図・`NT_ORIGIN_REFS_DIR` の作者指名画像は索引に載らない）。

- 現データでは推定と `category` の不一致は **631 件中 0 件**。全 113 キャラ × 2 形態で参照選択の差分も **0/226**。
  つまり今回の価値は挙動改善ではなく、上流が種別を増やしたとき（`card_design` / `new_year` / `weakening` / `keycapper`）の**追従漏れ防止**。
- 種別名の表記を上流へ統一（`designalt` → `design_alt` / `conceptalt` → `concept_alt`）。
  `db_type.json` 由来のサムネ順も `_normalize_category_name()` で同じ表記に揃えないと突き合わせが壊れる（罠）。
- `emstk_` 接頭辞による corefolder キャップを `category` 判定へ置換。
  **キャップの根拠が変わった**: 「低解像度に枠を食われる」は原寸化で解消したので、
  残る理由は「同一種別で `ref_limit` を埋め切らない（catalog / arts を必ず 1 枚残す）」。
- `preferred_reference_images` を `_sort_paths_for_form()` の**同種別内タイブレーク**に採用（種別順は動かさない）。
  90 グループで判別が効く。現状は上流の指定と既存の並び順が一致しているため出力は不変だが、
  上流が代表画像を差し替えたら自動追従する。
- `is_large_original_candidate` を DB 格（Primary = 正典）の**後ろ**のタイブレークに追加。解像度より原典性を優先する。
- `ai_hints_source`（`source` = 上流整備 / `derived` = 最小 scaffold）を `collect_record_capabilities()` に載せ、
  `run_meta.json` から作画品質のばらつきを切り分けられるようにした。NT 許可レコードは `source` 109 / `derived` 4。

### 依頼4: LoRA v2 の再学習 — **未実施（コード側の準備のみ）**

学習ジョブは GCE の `lora-l4-trial` 上で走るもので、本リポジトリに学習スクリプトは無い（`scripts/sdxl_vm/` は推論のみ）。
素材選別の口として `get_local_image_paths(large_only=True)` を追加した（631 → 482 枚。
`arts/chattingArt/` ・ `attr/tailsUnit` ・960px の `design` 等、1024px 未満を落とす）。
**実際の再学習は VM 側の作業として別途必要。**

### 回帰テスト

`tests/test_image_index_metadata.py` を新規追加（7 ケース）。スイート全体 60 件 green。

