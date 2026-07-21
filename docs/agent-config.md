# エージェント設定の配布とスキル同期

このリポジトリは **GitHub Copilot / Claude / GPT Codex** の 3 系統・4 モードの AI エージェントで運用しています。
どのエージェントから作業しても**同じルールが適用される**ように、設定を SSOT（Single Source of Truth）で管理しています。

> ルール本体の正典は [`AGENTS.md`](../AGENTS.md)。このドキュメントは**その配布の仕組み**を説明します。

---

## 1. 全体像

```
                        ┌──────────────────────────────┐
                        │        AGENTS.md             │  ← 共通仕様の唯一の正典 (SSOT)
                        │  概要 / 境界 / Git / コマンド │
                        │  出力規則 / 禁止事項 …       │
                        └──────────────┬───────────────┘
                                       │ 参照（重複させない）
        ┌──────────────┬───────────────┼───────────────┬──────────────┐
        │              │               │               │              │
   ┌────▼────┐   ┌─────▼──────────┐  ┌─▼──────────┐  ┌─▼────────────┐
   │CODEX.md │   │copilot-        │  │CLAUDE.md   │  │CLAUDE.       │
   │         │   │instructions.md │  │            │  │Cowork.md     │
   │GPT Codex│   │Copilot / VSCode│  │Claude Code │  │Cowork        │
   └─────────┘   └────────────────┘  └────────────┘  └──────────────┘
        薄い設定書（ツール固有の事項だけを書く）
```

### 読み込み経路

| エージェント | 自動ロードされる入口 | AGENTS.md への到達 |
|---|---|---|
| **GPT Codex** | `AGENTS.md`（ネイティブ読込） | **直接**。AGENTS.md の「前提条件」冒頭で [`CODEX.md`](../CODEX.md) の読込を指示 |
| **GitHub Copilot** (VS Code) | [`.github/copilot-instructions.md`](../.github/copilot-instructions.md)<br>＋ [`.github/instructions/roleplay-izuna.instructions.md`](../.github/instructions/roleplay-izuna.instructions.md) (`applyTo: '**'`) | 設定書冒頭のリンク |
| **Claude Code** | [`CLAUDE.md`](../CLAUDE.md) | 設定書冒頭のリンク |
| **Claude デスクトップ / Cowork** | [`CLAUDE.Cowork.md`](../CLAUDE.Cowork.md) | 設定書冒頭のリンク |

Codex だけ矢印が逆（AGENTS.md → 薄い設定書）である点に注意してください。
Codex は `AGENTS.md` をネイティブに読むため、そこを起点に固有設定へ降りる形になります。

> **Copilot に AGENTS.md を直接読ませたい場合**は、VS Code のユーザー設定で `chat.useAgentsMdFile` を有効化します（任意）。
> `.vscode/settings.json` は `.gitignore` 対象のため、リポジトリからは強制していません。

---

## 2. どこに何を書くか

| 書きたい内容 | 書く場所 |
|---|---|
| プロジェクト概要・編集境界・Git 運用・実行コマンド・出力規則・ログ規約・禁止事項 | **`AGENTS.md` のみ** |
| ロールプレイの口調・呼称・禁止事項 | [`.github/_roleplay-datas/roleplay-prompt.md`](../.github/_roleplay-datas/roleplay-prompt.md)（ロールプレイの正本） |
| 承認モード・サンドボックス・ネットワーク制約 | 各ツールの薄い設定書 |
| ファイル操作ツールの使い分け、CLI の癖 | 各ツールの薄い設定書 |
| 使い方・コマンド例・仕様の詳細 | `docs/*.md` |

**共通仕様を薄い設定書へ重複させないこと。** 重複は必ず乖離を生み、エージェントごとに挙動が変わります。
薄い設定書を書いていて「これは他のツールでも同じだな」と思ったら、その内容は `AGENTS.md` へ巻き取ってください。

### エージェントを追加するとき

1. `AGENTS.md` の「エージェント設定の配布構成（SSOT）」の読み込み経路表に 1 行追加する
2. 薄い設定書を新設する（既存 4 つをテンプレにする。冒頭の SSOT 宣言ブロックは必ず入れる）
3. 既存の薄い設定書すべての「対をなす薄い設定書」リンクへ追記する（**漏れやすいので全部確認**）
4. このドキュメントの表を更新する

---

## 3. スキルの正本とミラー

作画支援スキル `numbertales-imagegen` も同じ思想で配置しています。
設定書が「中立な `AGENTS.md` が正典 / ツール別ファイルは薄い設定書」なのと対称に、
スキルも「中立な `.agents/` が正本 / ツール別ディレクトリはミラー」です。

| パス | 位置づけ | 読むエージェント |
|---|---|---|
| [`.agents/skills/numbertales-imagegen/`](../.agents/skills/numbertales-imagegen/) | **正本（実体）。編集はここ** | GPT Codex（プロジェクトスキル） |
| `.claude/skills/numbertales-imagegen/` | **生成ミラー。直接編集しない** | Claude Code / Cowork |
| `~/.claude/skills/numbertales-imagegen` | ジャンクション | Claude パーソナルスキル |

### 同期コマンド

```powershell
# 差分チェック（差分ありなら exit 1。作業前・コミット前の確認用）
powershell -ExecutionPolicy Bypass -File scripts\sync-agent-skills.ps1 -Check

# 正本 -> ミラーへ反映
powershell -ExecutionPolicy Bypass -File scripts\sync-agent-skills.ps1 -Apply
```

- 引数なしで実行した場合は `-Check` 扱い（安全側）。
- 処理対象は**正本に存在するスキルのみ**。ミラー側にしか無いスキルは削除せず警告します。
- `repo_path.txt`（環境固有）と `*.skill`（配布パッケージ）は同期対象外・`.gitignore` 済み。
- 実装: [`scripts/sync-agent-skills.ps1`](../scripts/sync-agent-skills.ps1)

### インストール（パーソナルスキル化）

```powershell
cd .agents\skills\numbertales-imagegen
./install-personal-skill.ps1
```

正本の確定 → `repo_path.txt` 生成 → ミラー同期 → `~/.claude/skills/` へジャンクション、までを一括で行います。
Codex はリポジトリ内 `.agents/skills/` を直接読むため追加操作は不要です
（別途パーソナル化したい場合のみ `-LinkCodexPersonal` を付ける。参照先は実機の Codex 版を確認すること）。

### スキルを書くときの注意

- **ツール中立に書くこと。** 「実機 Claude Code」「実機 Codex」のような特定ツール名の断定を避け、
  「実機（Windows / ローカル CLI エージェント）」のように書きます。同じファイルが両方へ配られるためです。
- 共通仕様（ロールプレイ・出力規則・禁止事項）はスキルに重複させず `AGENTS.md` を参照させます。
- 変更後は `-Check` が exit 0 になる状態でコミットしてください。

---

## 4. PowerShell スクリプトの文字コード

このリポジトリの `.ps1` は **UTF-8 (BOM あり)** で保存します。

Windows PowerShell 5.1 は BOM の無いファイルを ANSI（日本語環境では CP932）として読むため、
BOM 無し UTF-8 で日本語コメント・文字列を書くと文字化けし、**構文エラーで起動すらしません**。
新規スクリプトを追加したら、次で確認してください。

```powershell
# 先頭 3 バイトが EF BB BF なら OK
Get-Content scripts\sync-agent-skills.ps1 -Encoding Byte -TotalCount 3
```

---

## 5. チェックリスト（設定を触ったとき）

- [ ] 共通仕様の変更を `AGENTS.md` **だけ**に書いたか（薄い設定書へ重複していないか）
- [ ] 薄い設定書 4 種の相互リンクに漏れがないか
- [ ] スキルを触ったなら `scripts\sync-agent-skills.ps1 -Check` が exit 0 か
- [ ] 新しい `.ps1` は UTF-8 BOM 付きか
- [ ] 新しい `docs/*.md` を追加したなら [`docs/README.md`](README.md) の目次に追記したか

---

## 関連ドキュメント

- 共通仕様の正典: [`AGENTS.md`](../AGENTS.md)
- ロールプレイ正本: [`.github/_roleplay-datas/roleplay-prompt.md`](../.github/_roleplay-datas/roleplay-prompt.md)
- `.agents/` の説明: [`.agents/README.md`](../.agents/README.md)
- 環境準備: [`setup.md`](setup.md)
