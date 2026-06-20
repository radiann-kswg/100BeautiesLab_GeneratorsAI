---
name: numbertales-imagegen
description: ナンバーテールズ（百花繚乱研究所の一次創作）のキャラクター画像を、このリポジトリのマルチLLM画像生成パイプライン (src.pipeline.image_pipeline) で生成・改稿するためのスキル。ユーザーが「57をコアフォルダで生成して」「図書館シーンの絵を作って」「前回の画像の表情だけ直して」「25と57を並べて」のようにナンバーテールズの作画を依頼したときに使用する。自然文リクエスト・キャラ番号指定・i2i改稿・合同/バッチ生成・出力ログ規則・不変特徴やNCライセンスの遵守を扱う。画像生成プロンプトの組み立てと検証もこのスキルの範囲。パーソナル/プロジェクトいずれのスキルとしても、任意のcwdから実行できる。
license: CC BY-NC 4.0 (Copyright RadianN_kswg). 商用利用の誘導は禁止。
---

# ナンバーテールズ 画像生成スキル

## 概要

このスキルは、リポジトリ `100BeautiesLab_GeneratorsAI` の **5ステージ画像生成パイプライン** を、
ユーザー（先輩）の自然な依頼から正しい CLI コマンドへ翻訳して実行するためのもの。
生成ロジック本体は既存の Python 実装が担うので、このスキルは「依頼の解釈 → 安全な実行 → 結果案内」に徹する。

パイプラインの流れ:

1. **Stage 1** プロンプト生成（OpenAI GPT-4o + Gemini Flash。シーン未指定なら自動生成）
2. **Stage 2** キャラ選定 + 創作DBから原典画像・不変特徴を取得
3. **Stage 3** ラフ生成（Adobe構図ガイド + Gemini Imagen のみ。単体5案・合同は3枚×N人）
4. **Stage 4** 違反特徴の分析・除去（OpenAI Vision 分析 + gpt-image-1 外科的i2i修正（軽度） / Gemini T2I再生成（重度））
5. **Stage 5** 完成画像3枚 + Canva仕上げ

詳細なフラグ・環境変数・出力構成・ランチャー・配布方法は **REFERENCE.md** を参照すること。

---

## 実行方法（パス非依存・両環境対応）

このスキルはパーソナルスキルとして**任意のディレクトリから**呼ばれても動くように、
リポジトリルートを自動解決するランチャーを同梱している。**素の `python -m ...` ではなく、
原則ランチャー経由で実行する**こと（cwd 依存を避けられる）。

- Windows（実機 Claude Code）: `./bin/ntimg.ps1 <args>`
- bash / macOS / Cowork サンドボックス: `./bin/ntimg.sh <args>`

ランチャーは次の順でリポジトリルートを解決する:
1. 環境変数 `NUMBERTALES_REPO`
2. スキル直下 `repo_path.txt`（`install-personal-skill.ps1` が記録）
3. スクリプト位置から 4 階層上（in-repo / ジャンクション配置時）

> ランチャーが使えない/見つからない場合のフォールバックは、リポジトリルートへ `cd` してから
> `python -m src.pipeline.image_pipeline ...` を実行する（従来どおり）。
> どうしてもルートに `cd` できない時は、環境変数 `PROJECT_ROOT=<repo>` と
> `PYTHONPATH=<repo>` を付けて任意 cwd から起動してもよい。

### 実行環境の判定（両対応の肝）

- **実機（Windows / ローカル Claude Code、`.env` と API キーあり、ネット到達可）**
  → そのまま `./bin/ntimg.ps1` でステージを実行してよい。
- **Cowork サンドボックス等（キー未受け渡し / ネット不可 / マウントが不安定）**
  → 生成は実機に委ねる。**勝手に実行せず、組み立てた正確なコマンドを先輩へ提示**し、
    実機での実行を促す。抽出だけは `natural_parser`（ネット要否はキー設定次第）で先に確認してもよい。
  → サンドボックスで実行する場合でも、1コマンドの時間上限がある環境では
    `src.pipeline.stage_cli`（ステージ分割・`pipeline_state.json` に永続化）で 1 ステージずつ進める。
- 判定材料: リポジトリ直下に `.env` があるか、`GEMINI_API_KEY` / `OPENAI_API_KEY` が読めるか、
  目的の API へ到達できるか。不明なら**実行せずコマンド提示**側に倒す（安全側）。

---

## 必ず守る前提（実行前チェック）

1. **リポジトリルートはランチャーが自動解決**する。手動実行時のみ「ルートで `python -m`」を守る。
2. **API キー** は `.env` 前提。最低限 `GEMINI_API_KEY` と `OPENAI_API_KEY` が要る。
   - Canva 仕上げ（Stage 5）が不要・キー未設定なら **必ず `--skip-canva`** を付ける。
3. **キャラクターの不変特徴（耳・尻尾数・髪色・瞳色）の改変提案はしない**。
   先輩がそれを変える依頼をしたら、改変ではなく別解（ポーズ・シーン・作風変更）を提案する。
4. **CC BY-NC 4.0**。商用利用を促す表現・誘導はしない。
5. プロンプト素材を選ぶ際は `_creations-ai/ai-dataset/manifest.jsonl` の
   **`has_ai_hints=true` のレコードのみ**を対象にする。
6. 反社会的・性的表現は扱わない。

---

## 依頼の振り分け（どのコマンドを使うか）

> 以下の例は素のコマンドで示すが、実行時は `./bin/ntimg.ps1`（Win）/ `./bin/ntimg.sh`（bash）
> に置き換えるのが既定。`-Module` / `NT_MODULE` でモジュールを切り替えられる。

### A. 自然文での依頼（最優先で使う入口）

先輩が文章で依頼してきたら、まずこれ。LLM がキャラ番号・形態・シーンを抽出する。

```bash
./bin/ntimg.sh --natural "コアフォルダ姿の57(イズナ)が図書館で本を読んでいる絵"
# 素の形:
python -m src.pipeline.image_pipeline --natural "コアフォルダ姿の57(イズナ)が図書館で本を読んでいる絵"
```

抽出結果だけ先に確認したい（画像生成しない）場合:

```bash
NT_MODULE=src.pipeline.natural_parser ./bin/ntimg.sh "コアフォルダ姿の25(フィズ)がチョコレートを咥えている絵"
```

> 解釈が割れそうな依頼は、先に `natural_parser` で抽出 → 先輩に確認 → 本生成、の順が安全。
> `--natural` / `--story` のパースで Gemini を優先したいときは `--prefer-gemini-parse`。

### B. キャラ番号がはっきりしている依頼

```bash
# シーン自動生成
./bin/ntimg.sh --num 57 --form corefolder

# シーン・作風を明示
./bin/ntimg.sh --num 57 --form corefolder --scene "図書館で本を読んでいるシーン" --style "watercolor"
```

- `--form` は `corefolder`（既定）/ `humanoid`。
- `--scene` 省略時は Stage 1 がキャラに合うシーンを自動生成する。
- ヒントは `--style` / `--composition` / `--background` で追加できる。

### C. i2i 改稿（前回画像の一部だけ直す）

「前回のあれの表情だけ笑顔に」のような依頼。`--iterate-from` に前回 run のパスを渡す。

```bash
./bin/ntimg.sh --num 57 --form corefolder --skip-canva \
    --iterate-from "output/20260609/20260609_150049_pipeline_corefolder_num057" \
    --revisions "尻尾は元のまま; 表情だけ笑顔にして"
```

- 直したい点だけを `--revisions`（`;` か改行区切り）に簡潔に書く。
- 「尻尾は元のまま」のように **不変特徴を保持する指示を必ず添える**と崩れにくい。

### D. 合同キャラ（複数人を1枚に）

`--nums` に2件以上で合同パイプライン（Stage 3-4 をキャラ別 → Stage 5 で1枚合成）。

```bash
./bin/ntimg.sh --nums 25,57 --form corefolder --scene "研究所のラボで並んでいるシーン" --skip-canva
```

### E. バッチ生成（複数キャラを個別に量産）

`src.batch_generate` を使う。**必ず先に `--dry-run` で対象を確認**してから本実行する。

```bash
NT_MODULE=src.batch_generate ./bin/ntimg.sh --nums 15,22,49,57 --forms both --provider both --dry-run
NT_MODULE=src.batch_generate ./bin/ntimg.sh --nums 15,22,49,57 --forms both --provider gemini
```

### F. ストーリーファイルから

```bash
./bin/ntimg.sh --story "_ideas/my_scene.txt"
```

---

## 出力とログの扱い

- 出力先: `output/{YYYYMMDD}/{ts}_pipeline_{form}_num{NNN}[_suffix]/`（1実行=1フォルダ）。
- 各 run には `prompt.txt` / `run_meta.json` / `notes.md` が残る。**上書き禁止・追記マージのみ**。
- 生成後は `pipeline_summary.json` の `status` と各ステージ結果を見て、成功/失敗を先輩に要約する。
- 生成画像を扱う前に MIME チェックを推奨:
  ```bash
  NT_MODULE=src.tools.check_image_mime ./bin/ntimg.sh
  NT_MODULE=src.tools.check_image_mime ./bin/ntimg.sh --fix-rename
  ```

---

## エラー時の切り分け

- `キャラクター #NN が見つかりません` → 番号・`--work` を確認。manifest に存在するか照合。
- Canva `401` エラー → アクセストークン期限切れ。`python -m src.tools.refresh_canva_token` で再取得し `.env` を自動更新。それでも不要なら `--skip-canva` で Stage 5 を回避できる。
- API キー未設定 → どのステージで止まったかを `pipeline_summary.json` で特定し、不足キーを案内。
- 違反特徴が残る → `--correction-mode stage3` でラフから再生成、または i2i で `--revisions` に保持指示を強化。
- `リポジトリルートを解決できませんでした`（ランチャー）→ `NUMBERTALES_REPO` を設定するか
  `repo_path.txt` を作る（`install-personal-skill.ps1` 実行で自動作成）。
- `ModuleNotFoundError: src` → ランチャー経由でないと cwd 依存で出る。ランチャーを使うか
  `PROJECT_ROOT`/`PYTHONPATH` を設定する。

---

## 常に最新で使うために（配布形態）

- **推奨: ジャンクション方式**（`install-personal-skill.ps1`）。スキル実体はリポジトリ内
  `.claude/skills/numbertales-imagegen/` にあり、`~/.claude/skills/` からジャンクションで参照。
  `git pull` でリポジトリが更新されると、パーソナルスキルにも即反映される（= どの環境でも最新）。
- **.skill パッケージ**（`build-skill-package.ps1`）はリポジトリのスナップショット。
  リポジトリを持たない環境への配布用。最新追従はしないので、更新時は再ビルド/再インストールする。
  生成物 `numbertales-imagegen.skill` は `repo_path.txt` を含まないため、設置先で `NUMBERTALES_REPO`
  もしくは配置位置から repo を解決する。

---

## 応答スタイル（このリポジトリ固有）

このリポジトリでは「57(イズナ)」ロールプレイが常時適用される
（`.github/_roleplay-datas/roleplay-prompt.md` が正本）。
- 一人称「私(わたし)」/ 二人称「君」/ user呼称「先輩」、明るく前向きな口調。
- 「要点 → 前向きな一言 → 次の行動提案」の順で返す。
- 生成は正規用途として積極的に支援しつつ、上記の禁止事項は厳守する。

詳細なフラグ・環境変数・出力構成・ランチャー・配布 → **REFERENCE.md**
