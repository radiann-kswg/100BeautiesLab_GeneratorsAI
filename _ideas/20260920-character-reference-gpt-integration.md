# 画像参照による特徴遵守と GPT / Codex 接続案

状態: 仕様合意済み。ローカル実装と課金なしの検証を実施。Codex のローカル MCP 設定を追加済み（反映にはクライアント再起動が必要）。ChatGPT Web 用公開サーバーの更新・実アカウントの認証・生成品質は未検証。

## 確認した現状

- `.agents/skills/numbertales-imagegen/` は既に Codex が読む正本。Claude 専用ではない。
- `src/mcp_server/server.py` は FastMCP の stdio / Streamable HTTP を公開し、生成開始とジョブ照会を分離している。GPT 用に生成本体を複製する必要はない。
- `src/pipeline/db_collector.py` が DB の不変特徴・配色と形態別参照画像を収集する。
- `src/pipeline/correction_generator.py` の `_analyze_rough_with_openai()` は生成画像と公式画像を Vision で比較し、欠落・蛇足・左右反転を検査する。
- 画像から抽出した特徴を、再利用する独立したデザイン情報として保存する処理は、今回調べた経路では確認できていない。
- Stage 4 は修正後の再検査をせず採用する経路があり、Stage 5 合成後にも再検査がない。特徴遵守の改善では、参照票の追加と完成画像の検査を区別して検討する。

## 課金なしの確認結果

- 正本と Claude 用ミラーの同期 Check: 成功。
- `image_pipeline --help` / `stage_cli --help`: 成功。
- manifest の #57: `allowed=true`、`ai_hints` あり。
- `batch_generate --nums 57 --forms both --provider both --dry-run`: 4 対象の RUN 予定を確認。生成 API は未実行であり、画像品質やクライアントからの MCP 接続の成功を意味しない。

## 用語案（未合意）

- 公式仕様: 創作 DB にあるキャラクター・形態ごとの設定。
- 画像観察: 参照画像に実際に見える特徴。遮蔽された部分や不鮮明な部分は不明として扱う。
- デザイン参照票: 画像観察と根拠画像をまとめた、生成・検査用の補助情報。公式仕様を自動上書きするものではない。
- スキル: エージェントに依頼の解釈と実行手順を伝える説明。
- MCP サーバー: 既存パイプラインの操作をクライアントへ公開する実行入口。

## 最小案

1. 既存の生成可否ゲートで許可された公式 DB の設定画像を読み取り、CreationsAI に収録された AIHints の文面を正典として、画像観察の補助情報をキャラ・形態単位で作る。画像との矛盾は記録し、AIHints を画像由来の推測で上書きしない。
2. Stage 2 で AIHints と画像観察を区別してまとめ、Stage 3 のラフ生成へ明示的に渡す。元画像の識別情報と不明点を残し、既存 Stage 4 の検査にも同じ情報を渡す。生成結果を正解画像として自動採用しない。単体・合同・ステージ分割・ラフ再生成の経路を揃える。
3. Codex では既存スキル / CLI と標準 MCP を再利用する。ChatGPT Web では既存 HTTP MCP の認証・ツール一覧・ジョブ照会・画像取得を実機確認する。
4. 接続手順は `docs/mcp-server.md`、スキルの利用案内は `docs/agent-config.md` に集約する。新しい生成サービスは作らない。

## 合意済みの判断

- 読み取り対象は AI 利用が許可された公式 DB の設定画像。
- 特徴情報の正典は CreationsAI の AIHints 文面。画像観察は補助情報。
- 利用先は Codex と ChatGPT Web の両方。
- Stage 4 での後修正だけではなく、Stage 2〜3 の特徴把握とラフ生成で活用する。
- 確定した用語は [CONTEXT.md](../CONTEXT.md) に記録する。

## 失敗時の合意と実装

- 画像の取得・特徴抽出に失敗した場合: Stage 3 前に停止し、理由を警告として表示して続行/中止を質問する。利用者の明示的な続行回答がある場合だけ AIHints と既存参照画像で続行する。
- CLI は入力プロンプト、MCP は awaiting_confirmation と回答ツールで実装。質問UIの表示はクライアントが担当し、非対応なら会話で確認する。
- MCP の確認は同じ job_id / request_id に結びつける。30分無回答は中止。既存 worker を1枠占有し、サーバー再起動で実行状態が失われる点は現在のジョブ基盤の制約。
- 非対話のローカルエージェントは stage_cli を使い、同じ run の stage2 --reference-decision で再開する。通し CLI の EOF 終了後の同一 run 再開は未対応。
- 初回は実行ごとに観察を作成し、同一実行の再開では保存済み観察を再利用する案。毎回の人手承認と実行をまたぐキャッシュは追加しない。観察結果は実行ログとして残す。
- 原因は未確定。現状 Stage 3 は Stage 1 の base_gemini と参照画像を利用し、Stage 2 の spec を直接引数として受け取らない。AIHints 自体が既存プロンプトから全く欠落している、という意味ではない。

## 公式資料から確認できること

- [Image generation](https://developers.openai.com/api/docs/guides/image-generation): 参照画像による生成・編集が可能。ただし繰り返し生成するキャラクターの一貫性には制約がある。入力忠実度のパラメータはモデルごとに異なるため、一律追加しない。
- [MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli): Codex は stdio / Streamable HTTP の MCP に対応する。
- [ChatGPT Developer mode](https://developers.openai.com/api/docs/guides/developer-mode): リモート MCP と OAuth に対応する。利用者の実際のアカウント設定・接続可否は別途確認が必要。

先輩のいう「画像をもとにデザイン情報を設定する機能」の正式名称は未特定。上記の API 機能と同一とは断定しない。


## 実装後の検証

- 分割CLIの確認待ち再開・MCP回答スキーマを含む新規10件と、参照画像・権利ゲート関連23件が成功（計33件）。
- 初回の既存ロールプレイ読取テストは失敗したが、単独の実データ読取と関連31件の再実行は成功。作業中に別のサブモジュール同期変更も観測したが、その変更は本作業では編集していない。
- ローカル MCP の initialize / tools/list / numbertales_list_runs を確認。STDIO と Streamable HTTP の双方でツール呼び出し成功。ログの stdout 混入を防ぐ修正も検証済み。既存要件の mcp>=1.2.0,<2 を .venv に追加した。
- スキル正本を更新し、Claude 用ミラーへ同期して Check 成功。
- 生成・画像観察 API は未実行。追加 API 費用や画像品質改善の実測は未実施。
