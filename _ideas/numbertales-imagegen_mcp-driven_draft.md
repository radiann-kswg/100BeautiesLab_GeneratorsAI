# 草案: numbertales-imagegen スキルの MCP 駆動版

`src/mcp_server/`（→ [docs/mcp-server.md](../docs/mcp-server.md)）を立てたことで、
スキルを **bash でパイプラインを直叩き**する案内役から、**MCP ツールを呼ぶ**薄い案内役へ
切り替えられる。ここはその差し替え案メモ（installed skill 本体の編集は別途、設定 > Capabilities から）。

---

## 何が変わるか

| 観点 | 現行（bash 駆動） | MCP 駆動版 |
|---|---|---|
| 実行 | `python -m src.pipeline.image_pipeline …` を Bash で起動 | `numbertales_generate_*` ツールを呼ぶ |
| 待ち | フォアグラウンドで完了まで占有 | `job_id` 即返し → `numbertales_job_status` でポーリング |
| 出力 | ローカル `output/` のみ | `OUTPUT_SINK` で local / Drive / GCS 切替・リンク返却 |
| 実行場所 | 手元のみ | 手元 or Cloud Run（リモート） |

## リクエスト → ツールの対応表

| ユーザ依頼例 | 呼ぶツール | 主な引数 |
|---|---|---|
| 「57をコアフォルダで生成して」 | `numbertales_generate_character` | `num=57, form=corefolder` |
| 「図書館で本を読んでるシーンの57を」 | `numbertales_generate_character` | `num=57, scene="図書館で本を読んでいるシーン"` |
| 「25と57を並べて」 | `numbertales_generate_joint` | `nums=[25,57]` |
| 「コアフォルダ姿の25がチョコ咥えてる絵」 | `numbertales_generate_from_natural` | `text="…"` |
| 「前回の画像の表情だけ笑顔に」 | `numbertales_iterate` | `iterate_from=…, revisions="表情だけ笑顔にして"` |
| 「さっきのジョブどうなった？」 | `numbertales_job_status` | `job_id=…` |

## 標準フロー（スキル本文に入れる手順）

1. 依頼を上表でツールに対応づけ、生成系ツールを呼ぶ。
2. 返ってきた `job_id` を保持し、`numbertales_job_status` で `succeeded` まで確認する。
3. `result.outputs[].url`（Drive/GCS）または `local_path`（local）を先輩に提示する。
4. `note` が付いていればフォールバック理由（クレデンシャル未設定など）を伝える。

## 不変条件（現行スキルから引き継ぎ）

- 不変特徴（耳・尻尾本数・髪色・瞳色）の改変提案はしない（パイプライン側でも検証）。
- CC BY-NC 4.0 / 反社会的・性的表現の禁止はそのまま。
- 参照優先順位（manifest / creations-db / usage ドキュメント）は現行どおり。

## 移行メモ

- bash 起動の記述は「ローカル fallback」として残してよい（MCP サーバ未起動時の保険）。
- リモート運用時は `OUTPUT_SINK=local` を使わない（画像が手元に届かない）。
