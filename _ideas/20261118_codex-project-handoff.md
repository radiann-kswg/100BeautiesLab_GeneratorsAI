# 百花繚乱研究所 生成AI周りへの引き継ぎ

2026-11-18 JST 確認。Codex の「百花繚乱研究所 生成AI周り」にチャット「生成AI対応内容を統合」を移動済み。同じ作業フォルダを参照していた旧プロジェクト `100BeautiesLab_GeneratorsAI` は削除済み。作業フォルダは `C:\Visual Studio Code UserFile\100BeautiesLab_GeneratorsAI`、確認時のブランチと HEAD は `develop` の `ca3d758`。運用ルールは [AGENTS.md](../AGENTS.md)、Codex の確認手順は [docs/agent-config.md](../docs/agent-config.md#6-codex-で生成パイプラインを確認する) を参照する。

## 引き継いだ作業

- **データセット追従**。11月16日に `TailsUnit.Count` の `null` 許容に追従（`8afebea`）し、辞書レコード欠落を解消する `_creations-ai` を取り込んだ（`2247033`）。11月18日の同期で `_creations-ai` を `7cd5819` から `d4ac56f` に更新。ネストの DB は同期記録上 `272d513`。manifest と画像インデックスの差分を比較し、追加バッジ4件の解決と生成可否をローカルで確認した。今回の同期に伴う `src/`・`docs/` の追従修正は不要。[11月18日の同期ログ](../_tasks/20261118_submodule-sync.md#最適化メモ)
- **画像生成と公式部位図**。Stage 2 で公式画像を観察して AIHints を補助し、その結果をラフ生成と検査へ渡す。観察失敗時の利用者確認は `397ae41`、公式部位図の取り回しとラフ／完成枚数の既定復元は `f3bcb6f`、追加修正は `ec2ac4d`。[生成 CLI](../src/pipeline/image_pipeline.py)・[分割 CLI](../src/pipeline/stage_cli.py)
- **再現精度の確認**。10月1日の 93・666 の生成記録では、93 の番号は公式線画に近づいた。666 のブローチと光輪中央には差が残り、Stage 4 の検査は通過した。666 の再確認時は、部位図の投入結果と Stage 4 の判定を同じ run から照合する。[公式参照の監査](20261001_official-reference-audit.md)・[実生成レビュー](20261001_reference-generation-review.md)
- **SDXL と MCP**。過去の Codex 履歴では、`sdxl-guide` を構図参照に用いた 57 の実機 VM での通し実行を確認。MCP の Drive 連携はユーザー OAuth に変更した記録がある。現時点のリモート MCP、ChatGPT Web 経由の動作、Drive への出力は再検証していない。[生成ガイド](../docs/usage-generation.md)・[MCP 運用ガイド](../docs/mcp-server.md)

## 今回の確認範囲

- 仮想環境の Python 3.14.0 で画像パイプラインと分割 CLI の `--help` を確認した。作画スキル正本と Claude ミラーの同期チェックは成功。ローカルの `manifest.jsonl` と `manifest-training.jsonl` を読み取れた。
- 移動後の回帰確認は88件成功。同期前のデータでも再現する `10-alt` のローカル検索失敗が2件あり、MCP のログ切り替えテスト1件はローカル環境で初期化中に停止した。[確認結果の詳細](../_tasks/20261118_submodule-sync.md#11月18日-jst-のローカル確認)
- 10月1日の合同生成 `444,666` はローカルの `output/20261001/20261001_165703_pipeline_corefolder_nums444_666/pipeline_summary.json` で `status=ok` を確認した。今回は生成 API の呼び出しと画像品質の再評価を行っていない。サブモジュール内の Git 作業ツリーはアクセス制限により未確認。

履歴の補助資料はアーカイブ済みの Codex チャット「GeneratorsAIの対応内容を統合」「画像生成機能アトラス追従」「画像特徴抽出とCodex対応」「Update Claude AGENTS SSOT setup」「実装 SDXL provider プラン」「MCP画像生成の実装提案を確認・調整」。過去の承認や環境確認を、次回実行時の承認・動作確認には流用しない。
