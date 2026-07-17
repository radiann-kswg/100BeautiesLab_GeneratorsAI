# サブモジュール同期ログ — 2026-07-17 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | 4d6f08b | 88e9cc3 | SKIP | checkout 失敗 (master): git.exe : fatal: Unable to create 'C:/Visual Studio Code UserFile/100BeautiesLab_GeneratorsAI/.git/modules/_creations-a i/index.lock': File exists. 発生場所 C:\Visual Studio Code UserFile\100BeautiesLab_GeneratorsAI\scripts\daily-submodule-sync.ps1:52 文字:17 +         $out = (& git @GitArgs 2>&1 / Out-String) +                 ~~~~~~~~~~~~~~~~~~~     + CategoryInfo          : NotSpecified: (fatal: Unable t...': File exists.:String) [], RemoteException     + FullyQualifiedErrorId : NativeCommandError    Another git process seems to be running in this repository, e.g. an editor opened by 'git commit'. Please make sure all processes are terminated then try again. If it still fails, a git process may have crashed in this repository earlier: remove the file manually to continue. |
| `_creations-ai/creations-db` | origin/addon-ai-tag | d1e600d | d1e600d | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

今回取り込んだ更新はありません。

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

---

## 手動リカバリ + 差分レビュー — 2026-07-17 13:20 (Claude Code / イズナ)

### 1. SKIP 原因: 古い index.lock（解消済み）

上表の checkout 失敗は、`.git/modules/_creations-ai/index.lock`（0 byte・07-17 08:07 生成）が
残留していたことが原因。確認時点で git プロセスは 1 つも稼働しておらず、親リポの作業ツリーも
clean だったため、**クラッシュした git が置き去りにしたゴミロックと判断して削除**した。

放置すると毎朝の `daily-submodule-sync.ps1` が checkout 失敗 → SKIP を繰り返すため、
**同一症状が再発した場合も「git プロセス不在 + 作業ツリー clean」を確認のうえ削除してよい。**

### 2. 手動で取り込んだ更新

| サブモジュール | 旧 | 新 | 判定 |
|---|---|---|---|
| `_creations-ai` | 4d6f08b | **2c26366** | FF 取り込み（16 コミット） |
| `_creations-ai/creations-db` | d1e600d | **e3acfc4** | FF 取り込み（`addon-ai-tag` HEAD） |

主要コミット:

- `e4ab8da` fix: AI 学習ポリシーの同意伝達を是正し、退行を検知するガードを入れる
- `e3acfc4` / `455cc8b` / `cdb76e5` `AI_Unready` フラグ・タグ実装（DB 側）
- `d1e600d` (既取込) AIHints 構造的再同期 — 実体は 27 番の文言修正のみ

### 3. 判定: `src/` の追従は不要（コード変更なし）

**結論: 生成パスへの影響はゼロ。実測で確認済み。**

`src/` が読むのは `manifest.jsonl` のみで、`_type=="character"` かつ `has_ai_hints` で絞る
（[`src/utils/dataset.py`](../src/utils/dataset.py) の `get_characters()` / `find_character()`）。
新旧 `manifest.jsonl` を突き合わせた実測値:

| 指標 | 旧 (4d6f08b) | 新 (2c26366) |
|---|---|---|
| character レコード総数 | 532 | 532 |
| **`has_ai_hints`（＝生成対象）** | **92** | **92** |
| レコードのキーセット | \- | 完全一致（新規キー・リネームなし） |
| 生成対象の `ai_hints` 変化 | \- | **0 件** |
| 生成対象の `images` 変化 | \- | **0 件** |
| 生成対象の `data` 変化 | \- | **0 件** |
| `ai_training.allowed` | 211 | 153 |

- 生成対象 92 件の増減は **なし**（LOST 0 / GAINED 0）。57・25・27・15・22・49・2-alt はすべて
  `has_ai_hints=True` を維持し、`ai_hints` / `images` / `data` がバイト等価。
- 減ったのは**学習用**の `manifest-training.jsonl`（236 → 178 行）のみ。`src/` はこのファイルを読まない
  （`dataset.py` の docstring に「生成では使用しない」と明記あり）。
- `ai_training` フィールドは `collect_record_capabilities()` が `run_meta.json` へ記録するだけで、
  フィルタ・分岐には一切使われていない（`src/` 全体で参照は 1 箇所のみ）。
- 取り込み後の実コードでの動作確認: `find_character()` で 57/25/27/15/49/2-alt/10-alt がすべて解決し、
  両形態の `ai_hints` と参照画像（ローカル実体）が取得できることを確認済み。

**→ 追従すべき差分が存在しないため `src/` は編集しない（過剰改変の回避）。**

### 4. 新軸 `AI_Unready` の登場と 10-alt の扱い

上流は `AI_Optout`（権利軸）から「未着手」の除外を切り離し、`Progress` / `AI_Unready`（充填軸）へ
移譲した。`ai-dataset/policy.json` の `ai_training_policy.axis_semantics` に定義がある:

- `ai_optout`: 「権利上 AI 学習・生成へ供してはならない」という原著作者の表明
- `ai_unready`: 「制作が進んでおらず供する内容が無い」という状態のみを表し、権利上の可否とは**無関係**。
  `AI_Unready: false` は許諾を意味しない

これにより **`10-alt` が初めて「`has_ai_hints=True` かつ `ai_training.allowed=False`」になった**（旧 0 件 → 新 1 件）。
理由は `Progress: "stillTentative"`（＝設定が暫定）であり、reason 文に
`This is NOT a rights-based opt-out` と明記されている。

**先輩の判断（2026-07-17）: 現状維持＝生成対象として通す。** 暫定キャラを作画して設定を固めるのは
正規の使い方であり、充填軸は権利軸ではないため。`src/` は `has_ai_hints` のみで絞るので追加実装は不要。
`run_meta.json` に `manifest_ai_training_allowed=False` が記録として残るだけ。

**権利軸の実害チェック（実測）: 生成対象 92 件のうち、権利軸（`AI_Optout` / `DB_Hidden` / `isPrivate`）で
不許可のレコードは 0 件。** 権利上の問題は発生していない。

### 5. 先輩へのTODO（未対応・要判断）

- **AGENTS.md「エージェント実務ルール」の記述が上流の正式見解と食い違っている。**
  - AGENTS.md: 「`AI_Optout` は学習制限フラグであり画像生成用途には適用しない（生成可否は `AI_Output` フラグが将来的に担う）」
  - 上流 `policy.json`: 「`AI_Optout: true` は『権利上 AI 学習・**生成**へ供してはならない』という原著作者の表明」
  - 現状は `AI_Optout=true` のレコードがすべて `has_ai_hints=false` のため**実害なし**だが、
    データセット側が将来オプトアウトレコードに `ai_hints` を出力すると、`has_ai_hints` 単独フィルタでは
    権利上の不許可レコードが生成対象へ流入する。文言のすり合わせを推奨（本コミットでは未変更）。

