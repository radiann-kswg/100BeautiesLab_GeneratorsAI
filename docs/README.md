# 100BeautiesLab_GeneratorsAI — docs index

百花繚乱研究所 (ナンバーテールズ) 向け AI 画像生成ワークスペースの実務ドキュメント集です。
このフォルダは「使い方」を一通り辿るためのハブで、各ページは独立して読めるようになっています。

> 仕様変更があった場合は **必ずこのフォルダのドキュメントも同時に更新してね。**
> 詳しい運用ルールの正典は [`AGENTS.md`](../AGENTS.md)。
> 各エージェント（Copilot / Claude / GPT Codex）への配布の仕組みは [`agent-config.md`](agent-config.md) を参照。

---

## 目次

| ドキュメント                                 | 内容                                                                                        |
| -------------------------------------------- | ------------------------------------------------------------------------------------------- |
| [`setup.md`](setup.md)                       | 依存パッケージ、`.env`、サブモジュール、API キー準備、macOS `setup_mac.sh`、PowerShell での注意点 |
| [`usage-generation.md`](usage-generation.md) | `src.gemini` / `src.openai` / `src.adobe` / `src.canva` / `src.batch_generate` の基本コマンドとフラグ |
| [`usage-mcp-canva-adobe.md`](usage-mcp-canva-adobe.md) | Claude(Cowork) 経由で接続済み Adobe / Canva MCP を使う対話的ワークフロー、Canva 接続手順 |
| [`usage-iterate.md`](usage-iterate.md)       | `--iterate-from` / `--revisions` による i2i (前回画像をベースに改稿) のワークフロー         |
| [`usage-roleplay.md`](usage-roleplay.md)     | `src.roleplay.export` — 上流生成済みロールプレイプロンプトのゲート付き消費 (漏洩ガード)      |
| [`output-and-logs.md`](output-and-logs.md)   | `output/` の3階層レイアウト、`prompt.txt` / `run_meta.json` / `notes.md` の役割と書式       |
| [`tools.md`](tools.md)                       | 画像 MIME チェック、output レイアウト移行、形態共通データセットの管理                       |
| [`mcp-server.md`](mcp-server.md)             | パイプラインを MCP ツール化して公開する `src/mcp_server/`、ローカル/Cloud Run デプロイ、出力シンク(local/drive/gcs) |
| [`agent-config.md`](agent-config.md)         | Copilot / Claude / GPT Codex への設定配布 (SSOT)、`.agents/` スキルの正本とミラー同期、`.ps1` の文字コード |

---

## クイックリファレンス (1 行コマンド)

```powershell
# 単発生成 (Gemini)
python -m src.gemini.generate --num 57 --form corefolder

# 単発生成 (OpenAI / gpt-image-1)
python -m src.openai.generate --num 57 --form corefolder

# 単発生成 (Adobe Firefly)
python -m src.adobe.generate --num 57 --form corefolder

# 生成済み画像を Canva でデザイン化・書き出し (--from-image 必須)
python -m src.canva.generate --num 57 --from-image <生成済み画像のパス>

# シーン・作風・構図・背景を指定
python -m src.gemini.generate --num 57 --form humanoid `
  --scene "図書館で本を読んでいるシーン" `
  --style "watercolor" --composition "bust shot" --background "wooden veranda"

# i2i 改稿 (前回 run dir を起点に、修正指示だけ当て直す)
python -m src.gemini.generate --num 57 --form corefolder `
  --iterate-from "output/20260609/20260609_15/20260609_150049_gemini_corefolder_num057" `
  --revisions "尻尾は元のまま; 表情だけ笑顔にして"

# マルチ LLM パイプライン (Stage 1〜5 を一括実行、単体キャラ)
python -m src.pipeline.image_pipeline --num 57 --form corefolder
python -m src.pipeline.image_pipeline --num 57 --form corefolder --skip-canva `
  --scene "図書館で本を読んでいるシーン"

# マルチ LLM パイプライン (合同キャラ: Stage 3-4 をキャラ別に実行し Stage 5 で合成)
python -m src.pipeline.image_pipeline --nums 25,57 --form corefolder

# パイプライン i2i (前回 run を起点に Stage 3〜5 を改稿モードで実行)
python -m src.pipeline.image_pipeline --num 57 --form corefolder --skip-canva `
  --iterate-from "output/20260609/20260609_15/20260609_150049_gemini_corefolder_num057" `
  --revisions "尻尾は元のまま; 表情だけ笑顔にして"

# 複数キャラ/形態/プロバイダのバッチ実行 (本実行前は必ず --dry-run)
python -m src.batch_generate --nums 15,22,49,57 --forms both --provider both --dry-run
python -m src.batch_generate --nums 15,22,49,57 --forms both --provider both

# プロンプト改善提案 (GPT-4o)
python -m src.openai.generate --num 57 --mode prompt-assist --scene "縁側で日向ぼっこ"

# 生成済みロールプレイプロンプトの消費 (ゲート付き)
python -m src.roleplay.export --num 57
python -m src.roleplay.export --list

# 画像 MIME 不一致チェック
python -m src.tools.check_image_mime --strict
```

---

## ドキュメントを直すべきタイミング

次のような変更を加えるときは、 **必ず関連する `docs/*.md` も同じ PR / コミットで更新する** こと。
古いドキュメントが残るとフィードバックループが壊れるよ。

| 変更内容                                                        | 更新先候補                                              |
| --------------------------------------------------------------- | ------------------------------------------------------- |
| 新しい CLI フラグ追加・既存フラグの動作変更                     | `usage-generation.md` / `usage-iterate.md`              |
| 出力ディレクトリ階層・ログファイル仕様変更                      | `output-and-logs.md` / `AGENTS.md` の出力規則セクション |
| 新しい `src/tools/` スクリプト追加                              | `tools.md`                                              |
| 形態共通データセット (`Works_*.json`) のスキーマ変更            | `tools.md` の形態共通データセットセクション             |
| 新しい環境変数 (`.env`) を導入                                  | `setup.md`                                              |
| プロンプトビルダー側で重要なブロック追加 (例: `[番号印字仕様]`) | `usage-generation.md` のプロンプト構造説明              |

---

## ライセンス

本リポジトリのドキュメント・スクリプト: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)
非商用目的に限り利用可。商用利用・再配布には著作権者の許諾が必要です。
