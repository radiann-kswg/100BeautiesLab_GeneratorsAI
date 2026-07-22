# numbertales-imagegen — 適用手順（実機 Windows で実行）

このフォルダはスキル一式の**正本**です（`.agents/skills/numbertales-imagegen/`）。
`.claude/skills/numbertales-imagegen/` は同期スクリプトが作る**生成ミラー**なので、直接編集しないでください。

## 0. 配置の考え方

| パス | 位置づけ | 読むエージェント |
|---|---|---|
| `.agents/skills/numbertales-imagegen/` | **正本（実体）** | GPT Codex（プロジェクトスキル） |
| `.claude/skills/numbertales-imagegen/` | 生成ミラー | Claude Code / Cowork |
| `~/.claude/skills/numbertales-imagegen` | ジャンクション | Claude パーソナルスキル |

## 1. 更新版を持ち込む場合（.skill 展開版など）

このフォルダの中身を、リポジトリの `.agents/skills/numbertales-imagegen/` へ上書きコピー:

```
SKILL.md / REFERENCE.md / install-personal-skill.ps1 / build-skill-package.ps1 / bin/ntimg.ps1 / bin/ntimg.sh
```

（`repo_path.txt` はコピー不要。次の install で自動生成される）

## 2. インストール（正本 → ミラー → パーソナルスキル）

```powershell
cd "C:\Visual Studio Code UserFile\100BeautiesLab_GeneratorsAI\.agents\skills\numbertales-imagegen"
./install-personal-skill.ps1
```

→ `repo_path.txt` を生成 → `.claude/skills/` へミラー同期 → `~/.claude/skills/numbertales-imagegen` にジャンクション。
   Settings > Capabilities で Code execution を ON、スキル一覧で `numbertales-imagegen` を ON。

Codex はリポジトリ内 `.agents/skills/` をプロジェクトスキルとして直接読むため、追加操作は不要です。

## 3. スキル本文を編集したとき

正本を直したら、必ずミラーへ反映すること。

```powershell
powershell -ExecutionPolicy Bypass -File scripts\sync-agent-skills.ps1 -Check   # 差分確認
powershell -ExecutionPolicy Bypass -File scripts\sync-agent-skills.ps1 -Apply   # 反映
```

> スキル本文は**ツール中立に書く**こと（「実機 Claude Code」「実機 Codex」等の断定を避ける）。
> 同じファイルが Codex 側にも Claude 側にも配られます。

## 4. 動作確認

```powershell
./bin/ntimg.ps1 -Module src.pipeline.natural_parser "コアフォルダ姿の57が図書館で本を読む絵"
```

## 5.（任意）配布用 .skill を作る

```powershell
./build-skill-package.ps1     # numbertales-imagegen.skill を出力（repo_path.txt 除外）
```

## 関連ドキュメント

- エージェント設定の配布とスキル同期: [`docs/agent-config.md`](../../../docs/agent-config.md)
- 共通仕様の正典: [`AGENTS.md`](../../../AGENTS.md)
