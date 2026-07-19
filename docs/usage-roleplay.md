# ロールプレイプロンプトの消費 — `src.roleplay.export`

上流 creations-db（`addon-ai-tag`）が `tools/build-roleplay-prompts.mjs` で、各キャラの
`ConversationPattern` 等の**充填済みフィールド**からキャラ単位のロールプレイプロンプト
Markdown を機械生成するようになった（2026-07-19）。データセットは各レコードに
`roleplay_prompt: { path }`（本文非埋め込み・パス参照のみ）と `has_roleplay_prompt` フラグを付ける。

このリポジトリの `src.roleplay` は、その**生成済み Markdown を組み立て直さずゲート付きで消費する**
（policy を再実装しないのと同じ原則で、上流生成器 `build-roleplay-prompts.mjs` を src で二重実装しない）。

> **漏洩ガード（最重要）**: `manifest.jsonl` は `allowed=false` レコードの `path` も載せる
> （例: `#DB_SemiPrimary` Num 100 は生成物があるが不許可）。本文を読む前に必ず
> **ロールプレイ用ゲート**（`generation_permitted(usage="roleplay")` は権利軸・充填軸とも拒否）
> を通す。上流も「フォルダ一括読みは漏洩事故のため厳禁」と明記している。

---

## コマンド

```powershell
# 生成済みロールプレイプロンプトを取得して output/ に保存 + 標準出力
python -m src.roleplay.export --num 57

# 人手先行ワークフロー用に _ideas/roleplay/ にも保存
python -m src.roleplay.export --num 57 --to-ideas

# ロールプレイプロンプトを持つ (かつ権利上許可された) キャラ一覧
python -m src.roleplay.export --list
python -m src.roleplay.export --list --all-works   # 全作品を対象
```

### フラグ

| フラグ         | 既定値                | 役割                                                              |
| -------------- | --------------------- | ----------------------------------------------------------------- |
| `--num`        | ―                     | キャラクター番号 (例: `57`)。`--list` 指定時は不要                |
| `--work`       | `#Works_NumberTales`  | 作品キー                                                          |
| `--to-ideas`   | off                   | `_ideas/roleplay/num{N}.md` にも保存する                          |
| `--out`        | None                  | 出力ベースディレクトリの上書き (既定は `output/`)                 |
| `--list`       | off                   | `has_roleplay_prompt` を持つキャラと許可状態を一覧表示            |
| `--all-works`  | off                   | `--list` を全作品対象にする (既定は `--work` のみ)               |

---

## 出力

```
output/{YYYYMMDD}/{ts}_roleplay_any_num{N}/
  roleplay_prompt.md   — ロールプレイプロンプト本文 (上流生成物のコピー)
  run_meta.json        — メタ (本文は含めない。source_path / submodule_commit / ai_training_gate / char_count)
_ideas/roleplay/num{N}.md   — --to-ideas 指定時のみ
```

- `run_meta.json` には**本文を残さない**（`char_count` のみ）。`source_submodule_commit` で
  どの creations-db 版から取り出したかを追える。
- `--num` の終了コード: 許可・保存成功=`0` / 未生成(`unavailable`)=`0` / オプトアウト(`refused`)=`2` / エラー=`1`。

---

## 判定の流れ（`load_roleplay_prompt`）

1. **ロールプレイ用ゲート**（最厳格: 権利軸・充填軸とも拒否）→ 非許可なら `refused`（本文を読まない）。
2. `has_roleplay_prompt` / `roleplay_prompt.path` の有無 → 無ければ `unavailable`（未生成。捏造しない）。
3. パス解決 + **トラバーサル防止**（creations-db ルート配下かつ `RoleplayPrompts/` を含むこと）。
4. ファイル名 `roleplay-prompt-<charId>.md` の charId が要求 num と一致すること（取り違え防止）。
5. 実在確認 → 本文読み込み（`ok`）。

---

## 制約・スコープ

- **上流生成物の消費のみ**。src で `ConversationPattern` からの組み立て直しはしない（上流二重実装の回避）。
- 対話ループ・記憶・投稿は本リポジトリの対象外（参考実装 `NumberTales-MisskeyAIBot` の領分）。
- 出力本文は原著作物の創作設定そのもの。CC BY-NC 4.0（非商用）に従い、最終的な公開判断は User が行う。
- num→レコードの解決は作品キー+Num のみ（`find_character` 同様）。同一 Num が別 DB に併存する場合の
  DB 指定は未対応（Primary が優先ヒットしうる）。
