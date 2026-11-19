# サブモジュール同期ログ — 2026-11-19 09:00

> 実機 PowerShell スクリプト `scripts/daily-submodule-sync.ps1` による自動実行。

## フェッチ・判定結果

| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |
|---|---|---|---|---|---|
| `_creations-ai` | origin/master | d4ac56f | d4ac56f | NO-CHANGE | 最新 |
| `_creations-ai/creations-db` | origin/addon-ai-tag | 272d513 | 272d513 | NO-CHANGE | 最新 |

## 取り込んだ更新の内容

今回取り込んだ更新はありません。

## 最適化メモ

> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、
> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、
> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。

## 手動同期の追補 — 2026-11-19

先輩の CreationsDB/AI 更新取り込み依頼に基づき、上記の朝の判定後に fetch・FF 更新を実施。

| 対象 | 更新前 | 更新後 | 確認 |
|---|---|---|---|
| `_creations-ai` / `origin/master` | `d4ac56f2b0c0e38ee4417a618994dd136edf0686` | `60ecce3efdb4751564c1aa5840362048a4b42424` | FF・ローカル変更なし |
| `_creations-ai/creations-db` / `origin/addon-ai-tag` | `272d5130a5f11da135a8c2ca3c66c431a04c37d5` | `51244fc580a71aa3c78361e486010cd115ec548c` | CreationsAI の固定 gitlink・build-info と一致 |

### 最適化メモ（追補）

- 上流実装の変更はなく、AIHints の構造再同期、AppearanceDetail の部位・左右・番号位置・配色、DB ごとの利用許可設定が更新された。上流の許可レコードは181→187件。参考資料を除いた許可キャラクターは138件（NumberTales 121 / ShauErRiders 6 / SinisterChangingGirls 11）。
- 新 `ai_tags` に対して、旧 `outfit_features` / `silhouette_notes` / 自然文の衣装・瞳色が残ることを確認。`generation_ai_hints()` で生成用文面のみを新タグ優先にし、正タグと一致する負指定および未充填の TODO を除外した。原典・manifest・ログの AIHints 原文は保持する。
- Gemini / DALL-E / NovelAI、Stage 1 のシーン情報、Stage 2 の観察、Stage 3/4 の遵守文面、テキスト要約へ共通の生成用文面を渡す。全キャラに尾7本を強制していた固定文も除去し、個別の AIHints / TailsUnit に従わせる。
- `find_character()` / バッジ明示検索は全件 manifest を参照する。権利軸拒否を外部補完前に保持し、制作途中 `10D` は警告対象としてローカル解決する。提案用列挙 `get_characters()` は許可済みキャラクター限定を維持。
- Stage 2 の原文と生成用文面のログ仕様を `docs/output-and-logs.md` / `AGENTS.md`、プロンプト優先順と検索の扱いを `docs/usage-generation.md` に同期。
- 上流の再生成済み dataset をそのまま採用したため、サブモジュール内のソース・生成物の手動編集や再ビルドは不要。

### 検証（追補）

- `node scripts/validate-dataset.js`：成功。11作品 / 732キャラクター / 許可187・不許可545 / 解決済み画像参照699件。上流未解決画像参照2件は既存の記録として維持。
- `image_pipeline --help` / `stage_cli --help`：成功。スキル同期 `-Check`：差分なし。
- `batch_generate --nums 1,57,10D --forms both --provider both --dry-run`：成功。10D は制作途中の警告を保持し、未定義の humanoid 2件だけをスキップ。課金 API 未実行。
- `tests/test_manifest_lookup.py` / バッジ検索・参照画像テスト：15件成功。
- 最新ソースで `pytest tests -q`：100件成功（依存SDK由来の非推奨警告1件）。課金キーをプロセス内で外し、dotenv 読込を無効化して実施。サンドボックスでは既存MCP非同期テストが Windows `socketpair()` の `accept()` で待ち続けることをスタックで確認し、通常権限の実行で全件完走した。
- 許可済み NumberTales 121キャラクター / 242形態について、Gemini・DALL-E・NovelAI本文への全有効タグ伝達、原文非破壊、TODO非混入、正負タグ一致の除外、Stage 4スペックへの伝達をAPIなしで照合し成功。
- `git diff --check`：成功。両サブモジュール内部の作業ツリーは未変更。

課金を伴う画像・文章生成、実 Vision 観察、公開サーバー反映、コミット・push は実施していない。

## 手動同期の追補 その2 — 2026-11-19（獣爾騎兵・豹変系女子の外見・配色拡張）

先輩の「サブモジュールのデータ拡張を GeneratorsAI と ShapeChangerAI へ適応」依頼に基づき、同日 12:17 に fetch・FF 更新を実施。

| 対象 | 更新前 | 更新後 | 確認 |
|---|---|---|---|
| `_creations-ai` / `origin/master` | `60ecce3efdb4751564c1aa5840362048a4b42424` | `bc8609926a08b5b8494402adc698a2bc1d985590` | FF・ローカル変更なし |
| `_creations-ai/creations-db` / `origin/addon-ai-tag` | `51244fc580a71aa3c78361e486010cd115ec548c` | `8484bb11fafd31b0836915546dcaa74621435c4a` | CreationsAI の固定 gitlink・build-info と一致 |

### 取り込んだ更新の内容（追補その2）

- CreationsDB 6 コミット（「DB情報追加(獣爾騎兵＆豹変系女子) その１〜３＆UI改善」「進捗ログ整備」）。38 ファイル +4,189 / −2,915 行、うち `data/` は 6 ファイル +3,756 / −62 行（削除の大半は `_work_in_progress/` の旧ログ整理）。
- manifest はキャラクター 732 件・許可 187 件のまま増減なし。変わったのは 19 レコード（獣爾騎兵 7・豹変系女子 12）の `AppearanceDetail` / `ColorPalette` だけで、NumberTales のレコードは無変更。
- 新しい書き方: 耳・尾の形状を作品別の辞書コード（`vdict_EarShapeType` / `vdict_TailShapeType`）と補足（`about_*`）で、尾や翼の本数を `value_Num` で、豹変前後を `Formation: beforeChange / afterChanged` で持つ。獣爾騎兵の制服共通 7 色は作品メタ `$EnumDef_CommonColor` へ移り、個別パレットには差し替え色だけが `#ColorRole_CommonOverride` で残る。豹変系女子 N / USE は外見本文を持たず、`AnotherRegions_DBLink` で NumberTales 0 / 00 から継承する。

### 最適化メモ（追補その2）

- **生成経路への影響なし（判定根拠）**: `find_character()` は `Num` / `Num_Badge` で引くため、`BeastType.Beast`（獣爾騎兵）や `Drc`（豹変系女子）で索引されるレコードを解決できない（`find_character("Mouse", "#Works_ShauErRiders")` と `("E", "#Works_SinisterChangingGirls")` が `None` になることを実機確認）。今回変わった 19 レコードは生成パイプラインへ届かない。
- **`[DB部位別仕様]` の読み落としを修正**: `_format_appearance_detail_entry()` が、辞書コードに添えた補足（`about_*`）と本数（`value_Num`）を落としていた。補足は NumberTales の耳で既に使われており（許可 121 件 × 2 形態で 73 行。例: `Fox (left ear droops)`）、本数は今回の拡張で初めて登場した書き方。両方を出力へ足し、`docs/usage-generation.md` に追記した。
- **追従しなかったもの**:
  - 豹変前後の `Formation`: `appearance_details_for_form()` は対象形態と null だけを通すため落ちるが、該当レコードが検索に届かないので未対応のまま。ShapeChangerAI 側は対応済み（同リポジトリの `_tasks/20261119_submodule-sync.md`）。
  - 制服共通色と `#ColorRole_CommonOverride`: 共通色は manifest に無く、キャラクターごとの使用有無の記録も無い（巳は黄を使わない、子と寅は別配色）ため、一律に足すと使っていない色を指定する。`extract_color_palette()` は従来どおり個別パレットだけを読み、上書き行は未知ロールのフォールバック表示（`common override`）で残る。
  - N / USE の外見継承: manifest に展開されない。
- `verify_appearance_detail --all --work-key` は `has_appearance_detail` で対象を選ぶため、今回から獣爾騎兵・豹変系女子のレコードも拾う。この経路は未実行（`_attr_text()` は本数を値なしのラベルとして出す）。

### 検証（追補その2）

- `pytest tests -q`：101 件成功（追加 1 件。依存 SDK 由来の非推奨警告 1 件）。API キーを環境から外し、dotenv 読込を無効化して実施。コード変更前の新データでも既存 100 件が成功することを先に確認した。
- `node scripts/validate-dataset.js`：成功。11 作品 / 732 キャラクター / 許可 187・不許可 545 / 画像参照 699 件実在・未解決 2 件（既存）。
- `batch_generate --nums 1,57 --forms both --provider both --dry-run`：8 件すべて DRY-RUN（課金 API 未実行）。
- `git diff --check`：成功。両サブモジュール内部の作業ツリーは未変更。

課金を伴う画像・文章生成、実 Vision 観察、公開サーバー反映、コミット・push は実施していない。

