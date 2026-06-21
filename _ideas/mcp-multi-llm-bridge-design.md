# MCP 経由マルチLLM動作確認ブリッジ — 設計メモ

> 作成: 57(イズナ) / 状態: 設計のみ（実装は未着手）
> 目的: Cowork サンドボックスから `api.openai.com` / `generativelanguage.googleapis.com` への
> egress がブロックされている制約下で、本リポジトリのマルチLLMパイプラインを「MCP 経由」で動作確認する構成を決める。
> 参照: [`docs/usage-mcp-canva-adobe.md`](../docs/usage-mcp-canva-adobe.md) / [`AGENTS.md`](../AGENTS.md) /
> mcp-builder スキル（FastMCP/stdio）。

---

## 0. 前提の整理（事実確認済み）

- 既存の外部API呼び出しは Python の `requests` / 各SDK で行われ、鍵は **`.env` → `load_dotenv()` → `os.environ`** で読まれる。
  - Gemini: `src/gemini/generate.py` の `generate_image()`（`GEMINI_API_KEY`、`generativelanguage.googleapis.com`）
  - OpenAI: `src/openai/generate.py` の `generate_image_dalle()` / `assist_prompt_gpt()`（`OPENAI_API_KEY`、`api.openai.com`）
  - 統合: `src/pipeline/image_pipeline.py` の `run_image_pipeline(num, form, ...)` が単一エントリ。
- これらは **普通の関数として import 可能**。CLI(`main()`)と内部関数(`generate_image()` 等)が分離しているので、薄くラップしやすい構造。
- 既製の OpenAI/Gemini MCP コネクタはレジストリに無い（確認済み）→ **自前 MCP サーバ前提**。

---

## 1. 実行場所の整理（最重要）

### 結論
- **MCP サーバのプロセスは「ホスト実機」で動かす。** そうすればホストの通常ネットワークに乗るので
  `api.openai.com` / `generativelanguage.googleapis.com` に到達できる。
- **サンドボックス内で MCP サーバを動かしても egress 制限は同じくかかる**。回避にはならない。
- 「MCP連携経由の通信はegress設定に関わらず可能」が成立する理由は、**ローカル(stdio) MCP サーバが
  Cowork の Linux サンドボックスの中ではなく、デスクトップ版 Claude（ホストアプリ）の子プロセスとして
  ホスト側で起動するから**。egress ポリシーは「どのプロセスがどこから外に出るか」に対してかかるので、
  ホストで動くプロセスはサンドボックスのネット檻の外側にいる。

### なぜそうなるか（egress はプロセスの実行場所で決まる）
egress ブロックは「Cowork サンドボックスという実行環境の外向き通信」に対して設定されている。
つまり制限を受けるのは **サンドボックス内で動くプロセス**。

| 何を | どこで動く | api.openai.com への到達 |
|---|---|---|
| `python -m src.pipeline...`（Bash ツール） | Cowork サンドボックス内 | ❌ ブロック |
| MCP サーバをサンドボックス内で起動 | Cowork サンドボックス内 | ❌ 同じくブロック（回避にならない） |
| ローカル(stdio) MCP サーバ | **ホスト実機**（Claude の子プロセス） | ✅ 到達可能 |

Claude ↔ MCP サーバ間は stdio（標準入出力パイプ）または別経路でつながり、これは
サンドボックスの egress ルールの対象外。だから「MCP 経由なら通る」。
**ポイントは MCP という仕組みが魔法なのではなく、MCP サーバの実体がホストで動くこと。**

### 「ホストで MCP を動かす」と「ホストでパイプラインを直接動かす」の違い
ネットワーク経路だけ見れば **同じ**（どちらもホストのプロセス＝ホストのネットを使う）。
違いは **コントロールプレーン（誰がオーケストレーションするか）** だけ。

- **ホスト MCP 化した場合**: いま会話している Cowork/デスクトップ Claude が、その MCP を
  **会話の中からツールとして呼べる**。サンドボックス側でできること（ファイル整理・ロールプレイ・
  プロンプト下書き・Canva/Adobe MCP との連携）と、ネットを必要とする生成ステップを
  **ひとつのエージェント・ひとつの会話で混ぜて回せる**。ホスト MCP は「ネット越え担当の実行係（remote hands）」になる。
- **ホストで直接動かす場合（後述 C 案）**: ホスト側に別の Claude/ターミナル・セッションを立てて、
  そこで直接シェル＋ネットを使う。MCP ラッパは要らない代わりに、それは **別セッション**であり
  Cowork 側エージェントからは駆動できない。

> したがって「Cowork/デスクトップ Claude 側からオーケストレーションしつつ、実行はホスト MCP に委ねる」形は
> **成立する**。これが B 案（MCP 化）の唯一にして本質的なメリット。
> 逆に言うと、オーケストレーションを Cowork 会話に集約したいのでなければ、MCP 化の旨味は薄い。

### 副次的なうれしさ
- **鍵がサンドボックスに入らない**。`.env` はホストに置いたまま、MCP サーバプロセスだけが読む。
  サンドボックス側のログやファイルに API キーが落ちる経路を作らずに済む。

---

## 2. 推奨アーキテクチャ

### 全体像
既存クライアントとパイプラインを、**薄い stdio MCP サーバ（Python / FastMCP）**でラップする。
ビジネスロジックは触らず、`src/pipeline/image_pipeline.py` 等の **既存関数をそのまま import して呼ぶだけ**にする。

```
デスクトップ Claude / Cowork（会話・オーケストレーション）
        │  MCP (stdio, JSON-RPC)
        ▼
ホスト実機：src/mcp_server/server.py  (FastMCP, 薄いラッパ)
        │  import
        ▼
既存: run_image_pipeline / generate_image / generate_image_dalle / assist_prompt_gpt
        │  requests / SDK（ホストのネット）
        ▼
api.openai.com / generativelanguage.googleapis.com
```

### 公開ツール案（最小→拡張）

| ツール名 | 役割 | 主な引数 | ネット | 注釈(hint) |
|---|---|---|---|---|
| `ping_providers` | **疎通確認（最小の出発点）** OpenAI/Gemini に軽量リクエスト（モデル一覧など）を投げ、鍵有無・到達可否・遅延を返す | `providers=["openai","gemini"]` | 有(軽) | readOnly |
| `build_character_prompt` | 既存 `build_dalle_prompt`/`build_gemini_prompt` をラップしてプロンプト文字列だけ返す | `num`, `form`, `scene?`, `style?` | **無** | readOnly |
| `assist_prompt` | `assist_prompt_gpt()` ラップ（GPT でプロンプト改善＝安いテキスト疎通確認） | `num`, `form`, `scene?` | 有(安) | readOnly |
| `generate_character_image` | `generate_image()`(Gemini) / `generate_image_dalle()`(OpenAI) を単一キャラ生成でラップ | `num`, `form`, `provider`, `scene?`, `out_dir?` | 有 | 非idempotent |
| `run_pipeline` | `run_image_pipeline()` 全5ステージをラップ（重い・後期フェーズ） | `num`, `form`, `scene?`, `skip_canva?`, `iterate_from?`, `revisions?` | 有(重) | 非idempotent |
| `list_characters` / `get_character` | 創作DBの読み取り（任意・補助） | `num?` | 無 | readOnly |

引数は既存関数のシグネチャに 1:1 で対応させる（`run_image_pipeline(num, form, work_key, out_dir, scene, style, composition, background, skip_canva, correction_mode, iterate_from, revisions)`）。
新しいセマンティクスを足さず、Pydantic で型と制約（`form ∈ {corefolder, humanoid}` 等）だけ付ける。

### 段階的な計画（最小スコープから）
- **Phase 0 — 疎通だけ**: `ping_providers` のみ実装。「ホスト MCP がネットに出られる」事実を 1 ツールで確定させる。
  ここが今回いちばん検証したい核心。失敗時は鍵未設定/到達不可を区別したメッセージを返す。
- **Phase 1 — 安いテキスト**: `build_character_prompt`（ネット無）＋ `assist_prompt`（GPT テキスト）。
  画像課金ゼロ〜極小でエンドツーエンドの呼び出し経路を確認。
- **Phase 2 — 単一画像**: `generate_character_image`（1 キャラ・1 枚）。出力パス規則・`run_meta.json` まで通す。
- **Phase 3 — フルパイプライン / i2i**: `run_pipeline`、`iterate_from`/`revisions` 対応。合同・バッチは最後。

### 実装上の重要な注意（stdio 特有の落とし穴）
- **stdout を汚さないこと。** stdio トランスポートは **stdout を JSON-RPC 通信に使う**。
  ところが既存コードは `print("[INFO]...")` を **大量に stdout へ**出している。これをそのまま動かすと
  プロトコルが壊れる。対策は次のいずれか:
  1. MCP サーバ側で標準出力を **stderr にリダイレクト**してから既存関数を呼ぶ（`contextlib.redirect_stdout(sys.stderr)`）。
  2. もしくは将来的にロギングへ寄せる（今回は 1 の即効対応で十分・経験則的にこれが楽な気がする）。
- **長時間処理のタイムアウト**: フル 5 ステージ生成は分単位になりうる。MCP ツール呼び出しが
  タイムアウトする場合は、(a) `skip_canva=True` や単一ステージで分割、(b) 即座にパスを返して
  バックグラウンド実行＋ステータス確認ツールを足す、の二段構えを検討。最小スコープでは
  まず軽いツール（ping / prompt / 単一生成）に絞ってこの問題を避ける。
- **出力パス規則は維持**: 既存の `output/{YYYYMMDD}/{ts}_..._numNNN/` と `prompt.txt`/`run_meta.json`/`notes.md`
  をそのまま使う（MCP 経由でもレイアウトを揃えると比較しやすい）。`out_dir` を引数で渡せるようにしておく。

---

## 3. セットアップ手順の骨子

### サーバ本体
- 置き場所: `src/mcp_server/server.py`（FastMCP）。起動は `python -m src.mcp_server`。
- 依存: `mcp`（FastMCP 同梱）を `requirements.txt` に追加。既存の `python-dotenv` を流用。
- サーバ先頭で `load_dotenv()` を呼ぶ（既存スクリプトと同じく cwd/リポジトリ直下の `.env` を読む）。

### デスクトップ Claude / Cowork への登録（概念）
ローカル MCP サーバは「コマンドを起動する」形で登録する。設定の考え方は次の 4 点:
- **command**: `python`（ホストの venv の Python。フルパス推奨）
- **args**: `["-m", "src.mcp_server"]`
- **cwd**: リポジトリ直下（`.env` と `src/` を解決するため）
- **env**: 鍵の渡し方は下記いずれか

### `.env` の鍵を MCP サーバプロセスに渡す方法
ローカル stdio サーバは **起動元（Claude）から環境変数を継承**しつつ、サーバ側で `.env` も読める。実用上の選択肢:
1. **`.env` をそのまま使う（推奨・変更最小）**: cwd をリポジトリ直下にして `load_dotenv()` 任せ。
   鍵はファイルに留まり、設定ファイルへ平文で書かない。
2. **MCP 設定の `env` ブロックで明示注入**: `GEMINI_API_KEY` 等を設定側に書く。可搬だが
   設定ファイルに鍵が載るので扱いに注意。
3. 併用も可（`.env` 優先 / 不足分のみ `env` で補完）。

> セキュリティ上は **1 を基本**にしたい。鍵はホストの `.env` にだけ存在し、サンドボックスにも
> 設定ファイルにも漏らさない。`.gitignore` に `.env` が入っていることは要確認。

### 動作確認の順番
1. ホストのターミナルで `python -m src.mcp_server` が起動してエラーで落ちないこと。
2. MCP Inspector（`npx @modelcontextprotocol/inspector`）でツール一覧と `ping_providers` を叩く。
3. デスクトップ Claude に登録し、会話から `ping_providers` → `assist_prompt` の順で確認。

---

## 4. B 案（MCP 化）の率直な評価

### B 案（自前 MCP）に価値があるケース
- **Cowork の 1 会話で端から端まで回したい**。サンドボックス側の作業（ファイル整理・57 ロールプレイ・
  下書き・Canva/Adobe MCP 連携）と、ネット必須の生成を **同じエージェントが混ぜて駆動**したい。
  これが本質的な唯一の決め手（§1 の結論）。
- **型付き・ガードレール付きの呼び出し**を固定したい（`form` の制約、不変特徴維持の前提注入、
  出力パス規則の強制をツール層で担保）。
- 既に **Canva / Adobe を MCP で使っている**ので、生成も MCP に揃えるとワークフローが一貫する。
- 同じ手順を **何度も・複数セッションで**再現したい（ツールという安定インターフェース）。

### C 案（ホスト側 Claude Code / 直接 CLI）で十分なケース
- **単発・自分ひとりの開発作業**。すでにホストのターミナル前にいる。
- フル 5 ステージのような **重い・長時間バッチ**（MCP のタイムアウトと相性が悪い。CLI 直叩きが素直）。
- 自由なデバッグ・試行錯誤がしたい。ラッパの保守コストを払いたくない。
- 究極的には **Claude を介さず `python -m src.pipeline.image_pipeline` を直接叩く**のが最小。
  MCP の価値は「Cowork エージェントに駆動させたい」一点に集約されるので、それが要らないなら C で十分。

### 線引き（経験則）
| 判断軸 | B（MCP）寄り | C（ホスト直実行）寄り |
|---|---|---|
| 誰が回す | Cowork/デスクトップ Claude に任せたい | 自分（or ホストの Claude Code） |
| ワークフロー | 対話の中で他MCPと連携・反復 | 単発・バッチ・デバッグ |
| 処理の重さ | 軽〜中（ping/prompt/単一生成） | 重い（フルパイプライン長時間） |
| 保守コスト | ラッパを作り維持する | ゼロ（既存 CLI のまま） |
| 鍵の隔離 | ホストに留めたい（強み） | どちらでも |

> 57 メモ: たぶん現実的な最適解は **ハイブリッド**だよ。
> 「疎通確認・プロンプト・単一生成」みたいな軽いところだけ Phase 0–2 で MCP 化して
> Cowork から触れるようにして、フル生成の重いバッチはホスト CLI（C 案）に投げる。
> まず作るなら **Phase 0 の `ping_providers` 一本**。ここで「ホスト MCP はネットに出られる」を
> 確定できれば、あとは経験則的にスルッと伸びる気がする！

---

## 次に作るなら（最小スコープ・スケッチ）

```
src/mcp_server/
  __init__.py
  server.py        # FastMCP。先頭で load_dotenv() と stdout→stderr リダイレクト。
                   # tool: ping_providers のみ（Phase 0）。
                   #   - openai: GET https://api.openai.com/v1/models（鍵で）
                   #   - gemini: GET .../v1beta/models（鍵で）
                   #   - 返り値: {provider, ok, status, latency_ms, key_present, hint}
requirements.txt   # mcp を追記
docs/usage-mcp-multi-llm.md  # 登録手順（§3）を後で起こす
```

実装は本メモ承認後に着手する。コードはまだ書いていない（設計のみ）。
