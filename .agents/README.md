# `.agents/` — ベンダー中立なエージェント資産

このフォルダは、特定の AI ツールに紐づかない**エージェント共有資産の正本**を置く場所です。
GPT Codex 導入に伴って追加されました。

> 共通仕様の正典（SSOT）は [`AGENTS.md`](../AGENTS.md)。
> 配布の仕組み全体は [`docs/agent-config.md`](../docs/agent-config.md) を参照してください。

---

## 構成

```
.agents/
  README.md
  skills/
    numbertales-imagegen/    ← 作画支援スキルの正本（実体）
```

## スキルの正本とミラー

| パス | 位置づけ | 読むエージェント |
|---|---|---|
| `.agents/skills/<skill>/` | **正本（実体）。ここを編集する** | GPT Codex（プロジェクトスキル） |
| `.claude/skills/<skill>/` | **生成ミラー。直接編集しない** | Claude Code / Cowork |
| `~/.claude/skills/<skill>` | ジャンクション（`install-personal-skill.ps1` が作成） | Claude パーソナルスキル |

設定書が「中立な `AGENTS.md` が正典 / ツール別ファイルは薄い設定書」という構成なのと同じ考え方で、
スキルも「中立な `.agents/` が正本 / ツール別ディレクトリはミラー」に揃えています。

## 同期

```powershell
# 差分チェック（差分ありなら exit 1）
powershell -ExecutionPolicy Bypass -File scripts\sync-agent-skills.ps1 -Check

# 正本 -> ミラーへ反映
powershell -ExecutionPolicy Bypass -File scripts\sync-agent-skills.ps1 -Apply
```

- `repo_path.txt`（環境固有）と `*.skill`（配布パッケージ）は同期対象外・`.gitignore` 済み。
- ミラー側にしか無いスキルは削除されず警告のみ表示されます。

## スキルを書くときの注意

- **ツール中立に書くこと。** 「実機 Claude Code」「実機 Codex」のような特定ツール名の断定を避け、
  「実機（Windows / ローカル CLI エージェント）」のように書きます。同じファイルが両方へ配られるためです。
- ロールプレイ設定・禁止事項・出力規則などの共通仕様はスキル側に重複させず、
  [`AGENTS.md`](../AGENTS.md) と [`.github/_roleplay-datas/roleplay-prompt.md`](../.github/_roleplay-datas/roleplay-prompt.md) を参照します。
- 変更後は必ず `-Check` が通る状態でコミットしてください。
