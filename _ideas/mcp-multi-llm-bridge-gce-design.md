# MCP 経由マルチLLM動作確認ブリッジ — GCE リモート MCP 版 設計メモ

> 作成: 57(イズナ) / 状態: 設計のみ（実装は未着手）
> 前提更新: ユーザーは **Google Compute Engine (GCE) インスタンスを用意済み**。
> これを活用し「GCE 上で MCP サーバを常駐させるリモート MCP」構成で
> 本リポジトリのマルチ LLM（OpenAI / Gemini）動作確認を実現する。
> 土台: [`mcp-multi-llm-bridge-design.md`](./mcp-multi-llm-bridge-design.md)（ローカル stdio 版）
> 参照実ファイル: [`src/openai/generate.py`](../src/openai/generate.py) /
> [`src/gemini/generate.py`](../src/gemini/generate.py) /
> [`src/pipeline/image_pipeline.py`](../src/pipeline/image_pipeline.py)

---

## 0. 結論サマリ（先に要点）

- **狙いは成立する。** Anthropic はカスタムコネクタ（リモート MCP）へ **Anthropic 側クラウドの
  IP から接続**する。MCP サーバは GCE 上で動き、そこから OpenAI / Gemini へは
  **GCP のフルネット接続**で到達する。Cowork サンドボックスの egress 制限は
  「サンドボックス内プロセス」にかかるものなので、**GCE 上の MCP サーバには無関係**。
  → ホスト実機もプラン変更も不要になり得る、という今回の前提は妥当。
- **ただし新しい制約が増える（ここが旧メモとの最大の差）。** リモート MCP は
  **公開インターネットから HTTPS で到達可能**でなければならない。Anthropic は
  ユーザーの PC からではなく**自社サーバから**繋ぎに来るため、localhost や
  社内 LAN・VPN 内のサーバは繋がらない。→ **公開エンドポイント・HTTPS・認証・
  ファイアウォール**が必須になり、ローカル stdio 版より**運用とセキュリティの責任が増える**。
- **トランスポートは stdio ではなく HTTP（Streamable HTTP）**。これにより旧メモで悩んだ
  「stdout を JSON-RPC が占有する問題」は**ほぼ解消**する（後述 §1）。
- まずは **Phase 0 = `ping_providers` 一本だけ**を GCE にデプロイ → Claude から疎通確認。
  ここで「GCE リモート MCP がネットに出られ、Claude から呼べる」を最小コストで確定させる。

---

## 1. トランスポートの変更（stdio → Streamable HTTP）

### なぜ変わるか
ローカル版は **stdio**（標準入出力パイプ）で Claude デスクトップの子プロセスと通信していた。
リモート版は **Claude（Anthropic クラウド）が公開 URL へ HTTP で繋ぐ**ため、stdio は使えない。
リモート MCP の標準トランスポートは **Streamable HTTP**（旧来の HTTP+SSE を置き換えた現行方式。
1 つの HTTP エンドポイントで双方向、必要時にサーバ→クライアントを SSE ストリームで流す）。

```
Claude / Cowork（会話・オーケストレーション）
        │  ※接続元は Anthropic クラウドの IP
        │  HTTPS (Streamable HTTP, JSON-RPC over HTTP)
        ▼
[GCE]  リバースプロキシ (Caddy/nginx, TLS終端) :443
        │  → localhost
        ▼
[GCE]  src/mcp_server/server.py  (FastMCP, transport="http")  :8000
        │  import（ビジネスロジックは無改変）
        ▼
既存: run_image_pipeline / generate_image / generate_image_dalle / assist_prompt_gpt
        │  requests / 各SDK（GCP のネット）
        ▼
api.openai.com / generativelanguage.googleapis.com
```

### FastMCP での実装方針
ローカル版と **同じ FastMCP のツール定義**をそのまま使い、**起動時のトランスポート指定だけ**を変える。

```python
# 旧（ローカル stdio）
mcp.run()                       # = transport="stdio"
# 新（リモート HTTP）
mcp.run(transport="http", host="127.0.0.1", port=8000)
```

- ツール関数（`@mcp.tool()`）の中身は **トランスポート非依存**。Phase 0〜3 で作るツールは
  stdio 版と共通化でき、`MCP_TRANSPORT` 環境変数で切替える形にしておくと両対応で楽。
- `host="127.0.0.1"` に**バインドして外には直接出さない**。公開は前段のリバースプロキシ
  （Caddy/nginx）が 443/TLS で受けて localhost:8000 へ流す（§2・§3）。
- 認証は FastMCP のミドルウェア／依存（Bearer 検証）で噛ませる（§3）。

### 「stdout が JSON-RPC を占有する問題」は remote では関係するか → **ほぼ解消する**
- **stdio 版の悩み**: stdio はプロトコル通信に **stdout を使う**ので、既存コードの
  大量の `print("[INFO]...")`（`src/gemini/generate.py` / `src/openai/generate.py` に多数）が
  stdout に混ざると **JSON-RPC が壊れる**。だから旧メモは「stdout→stderr リダイレクト」を必須にしていた。
- **HTTP 版**: JSON-RPC は **HTTP ボディで運ばれ、stdout は使わない**。よって既存の `print`
  が stdout に出ても**プロトコルは壊れない**。リダイレクトの応急処置は **不要**になる。
- ただし運用観点では、**ログは標準出力に垂れ流すより整理したい**:
  - systemd 配下なら stdout/stderr は自動で **journald** に入る（`journalctl -u` で追える）ので、
    最低限これで十分。
  - 将来的には `print` を `logging` に寄せ、ファイル or Cloud Logging へ送ると保守が楽。
  - 長時間処理の進捗は print のままでも journald に残るので、まずは無改変で可。

---

## 2. デプロイ構成（GCE）

### インスタンス・OS・配置
- リポジトリ一式と `.env` を GCE 上に置く（鍵は **GCE 内に留める**、§3）。
- Python 仮想環境を作り `pip install -r requirements.txt` ＋ `mcp`（FastMCP）を追加。
- 配置例:
  - `/opt/100beautieslab/` にリポジトリ clone
  - `/opt/100beautieslab/.env`（chmod 600）
  - `/opt/100beautieslab/.venv`

### GPU は不要（確認）
- **不要で良い。** 画像生成は **OpenAI / Gemini への外部 API 呼び出し**で行われ、
  GCE 側はリクエストの組み立てとレスポンス保存だけ。`src/gemini/generate.py` /
  `src/openai/generate.py` のどこにもローカル推論は無く、`requests` / 各 SDK で
  外部 API を叩くだけ。→ **CPU インスタンスで十分**。

### 最小インスタンスで足りるか（コスト観点）
- ワークロードは **I/O 待ち主体（外部 API のレスポンス待ち）**で CPU・メモリ負荷は軽い。
  - **e2-micro / e2-small** クラスで十分。常時 1〜数リクエストを捌く程度。
  - メモリは参照画像を base64 で扱う瞬間がある（`assist_prompt_gpt` の data URL 化等）ので
    **1〜2GB は確保**したい。e2-micro(1GB) で詰まるなら **e2-small(2GB)** に上げる。
- コスト感（us リージョン目安・変動あり、正確な金額は要 GCP 料金確認）:
  - e2-micro は一部リージョンで**無料枠**対象になり得る。超過しても月数百円〜千円台。
  - e2-small で概ね月 **$13〜15 程度**。
  - **静的外部 IP**: インスタンスに**割当て中は基本無料**だが、**未使用で予約だけ**だと課金される。
    使わなくなったら解放する。
  - egress（GCP→OpenAI/Gemini）の通信量課金は画像 1 枚〜数枚程度なら**ごく僅か**。
- **常時起動が要件**（Claude が任意のタイミングで繋ぎに来るため）。停止すると疎通不可。
  使わない時間帯に**自動停止/起動**でコストを抑える運用も可（その間はコネクタが落ちる点に注意）。

### プロセス常駐（systemd 推奨）
`systemd` ユニットで「起動時自動・異常終了時再起動」を担保する。

```ini
# /etc/systemd/system/numbertales-mcp.service
[Unit]
Description=NumberTales Multi-LLM MCP server (Streamable HTTP)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=mcp
WorkingDirectory=/opt/100beautieslab
EnvironmentFile=/opt/100beautieslab/.env
ExecStart=/opt/100beautieslab/.venv/bin/python -m src.mcp_server
Restart=on-failure
RestartSec=3
# 出力は journald へ（journalctl -u numbertales-mcp -f で追える）

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now numbertales-mcp
journalctl -u numbertales-mcp -f
```

### ポートとリバースプロキシ / HTTPS 化
- **アプリ**: `127.0.0.1:8000`（外部非公開）。
- **前段**: **Caddy** を推奨（**Let's Encrypt の証明書を自動取得・自動更新**するので最小手数）。
  nginx + certbot でも可だが Caddy の方が設定が短い。

```caddyfile
# /etc/caddy/Caddyfile
mcp.numbertales-radiann.net {
    reverse_proxy 127.0.0.1:8000
    # 認証はアプリ側(FastMCP)で Bearer 検証する。Caddy 側で basicauth を足すことも可。
}
```

- **ドメイン or 静的 IP**:
  - Caddy の自動 HTTPS は **ドメイン名（DNS の A レコード）**が前提。
    → GCE に**静的外部 IP を予約**し、`mcp.numbertales-radiann.net` のような
      サブドメインの **A レコードをその IP に向ける**（既存ドメイン `numbertales-radiann.net` を活用）。
  - 純粋な IP だけで Let's Encrypt 証明書は取りにくい → **サブドメイン付与が現実的**。
- 公開エンドポイント例: `https://mcp.numbertales-radiann.net/mcp`
  （FastMCP の HTTP マウントパス。実装で `/mcp` に置くのが通例。最終 URL はこれをコネクタに登録）。

### GCP ファイアウォール
- VPC ファイアウォールで **インバウンドを絞る**:
  - **443/tcp**: Anthropic の IP レンジからのみ許可（§3）。
  - **22/tcp（SSH）**: 自分の管理 IP からのみ。
  - それ以外は **拒否**。
- 8000 番は外部に開けない（localhost のみ）。

---

## 3. セキュリティ（公開する以上の最低限）

リモート MCP は **公開エンドポイント**になる。ローカル stdio 版には無かった攻撃面なので、
次を**最低限**として明記する。

### (a) HTTPS 必須
- Anthropic はリモートサーバに **TLS で接続**する。平文 HTTP は不可。Caddy/Let's Encrypt で常時 HTTPS。
- Bearer トークン等の認証情報を平文で晒さないためにも HTTPS は前提。

### (b) 認証（Bearer / OAuth）
- カスタムコネクタ登録時、**「Advanced settings」で OAuth Client ID / Secret を指定可能**。
  本格運用なら **OAuth**（認可コードフロー）が望ましい。
- 最小構成なら **静的 Bearer トークン**で十分実用:
  - サーバ側で `Authorization: Bearer <TOKEN>` を検証し、不一致は 401。
  - トークンは `.env` の `MCP_BEARER_TOKEN` に置き、GCE 内のみで管理。
  - ※ Claude のカスタムコネクタ UI が任意ヘッダ注入をサポートするかは要確認。
    サポートされない場合は **OAuth or IP 制限**を主防御にする（下記 (c) が効く）。
- ツールの破壊的操作には**承認**を必須に（Claude 側の Allow 操作）。Research 等で
  無確認実行されると課金・誤生成のリスクがあるため、**書き込み系ツールは慎重に**。

### (c) ファイアウォール / IP 制限（強い防御）
- Anthropic は**自社クラウドの固定 IP レンジ**から接続してくる。
  → **443 のインバウンドを Anthropic IP レンジに限定**すれば、第三者からの直アクセスを遮断できる。
  - 最新レンジは公式の **Anthropic IP addresses**（`platform.claude.com/docs/en/api/ip-addresses`）を参照。
  - GCP VPC ファイアウォール or Caddy/nginx の `remote_ip` 制限で実装。
- **Bearer/OAuth ＋ IP 制限の二段**にすると、最小コストで実用的な安全域になる。

### (d) `.env` キーの取り扱い（GCE 内に留める）
- `OPENAI_API_KEY` / `GEMINI_API_KEY` は **GCE 上の `.env` だけ**に置く。
  - Cowork サンドボックスにも、Claude の設定にも、**鍵は一切出さない**（リモート版の構造的な利点）。
  - `.env` は **chmod 600 / 専用ユーザー所有**。`.gitignore` に `.env` が入っていることを確認。
  - より固めるなら **GCP Secret Manager** から起動時に読み込む。
- 出力物（`output/.../run_meta.json` 等）に鍵が落ちない実装であることは旧メモ同様に維持。

### (e) その他
- プロンプトインジェクション対策: ツールの入出力に注意。信頼できる自分のサーバなので
  リスクは低いが、ツールの戻り値に外部 API のエラーメッセージをそのまま大量に返さない等の配慮。
- レート/コスト保護: `run_pipeline` のような重い課金ツールには、**1 会話あたりの実行回数**を
  サーバ側で軽くガードしてもよい（暴発防止）。

---

## 4. Claude / Cowork からの接続（手順の概念・公式確認済み）

### プラン要件（公式・2026-04 時点）
- **カスタムコネクタ（リモート MCP）は Free / Pro / Max / Team / Enterprise で利用可**。
  **claude.ai・Claude Desktop・Cowork・モバイル**すべてで使える。**現在ベータ**。
- **Free は 1 個まで**。
- **Team / Enterprise は Owner のみが組織に追加可能**（追加後、各メンバーが個別に接続/有効化）。

### 重要な接続モデル（旧メモとの本質的な違い）
> カスタムコネクタを追加すると、**Claude はユーザーの端末からではなく「Anthropic のクラウド基盤」から
> あなたのリモート MCP サーバへ接続する**。これは Cowork / Claude Desktop でも同じで、
> ローカル端末のネットワークは使わない（＝公開到達性が必須）。
> ローカル MCP（`claude_desktop_config.json`）は別機構で、Cowork / claude.ai では使えない。

→ だから「GCE の MCP サーバが**公開 HTTPS で Anthropic IP から到達可能**」であれば、
Cowork のサンドボックス egress とは**完全に独立**に動く。狙い通り。

### 登録手順（概念）
**Pro / Max（個人）:**
1. **Customize > Connectors**（`claude.ai/customize/connectors`）を開く。
2. **「+」→「Add custom connector」**。
3. リモート MCP サーバの **URL を入力**（例 `https://mcp.numbertales-radiann.net/mcp`）。
4. 任意で **Advanced settings** に **OAuth Client ID / Secret** を指定。
5. **「Add」**で確定。

**Team / Enterprise:**
- Owner が **Organization settings > Connectors** →「Add」→「Custom」→「Web」→ URL 登録
  （任意で OAuth）。その後メンバーが **Customize > Connectors** で「Connect」。

**会話での有効化:**
- チャット左下の **「+」→ Connectors** で会話単位にトグル ON/OFF。
- ツール承認は出るたびにレビュー。信頼できるツールのみ「Allow always」。

### 不明点（要追加確認）
- **任意ヘッダ（静的 Bearer）注入を UI が許すか**は記事に明記が無い。許さない場合は
  **OAuth または IP 制限**を主防御にする（§3 で代替済み）。
- Cowork 固有の制約（コネクタ数・ベータ挙動）は変わり得るので、登録前に最新の
  サポート記事を再確認するのが安全。

---

## 5. 段階計画（最短ルート）

| Phase | 内容 | ネット | 目的 |
|---|---|---|---|
| **0** | **`ping_providers` のみ** を GCE にデプロイ → Claude から呼ぶ | 有(軽) | 「GCE リモート MCP がネットに出られ、Claude から疎通できる」を最小コストで確定 |
| 1 | `build_character_prompt`（ネット無）＋ `assist_prompt`（GPT テキスト） | 有(安) | 課金極小でエンドツーエンドの呼び出し経路を確認 |
| 2 | `generate_character_image`（1 キャラ 1 枚） | 有 | 出力パス規則・`run_meta.json` まで通す |
| 3 | `run_pipeline`（全5ステージ）/ i2i / 合同・バッチ | 有(重) | フル機能。長時間ゆえタイムアウト対策（分割 or 非同期＋status）を併用 |

**Phase 0 の検証順序:**
1. GCE で `python -m src.mcp_server`（HTTP, :8000）が落ちずに起動。
2. GCE 内 `curl http://127.0.0.1:8000/mcp ...` でローカル疎通（必要なら MCP Inspector）。
3. Caddy 経由 `https://mcp.numbertales-radiann.net/mcp` に外部から HTTPS 到達（認証込み）。
4. Claude（Pro/Max）の Customize > Connectors に URL 登録 → 会話で `ping_providers` 実行 →
   OpenAI / Gemini の **到達可否・遅延・鍵有無**が返れば成功。

> ここまで来れば「サンドボックス egress を回避して外部 LLM に到達」という核心が**実証**できる。
> 以降は generate 系を足すだけ。経験則だけど、Phase 0 さえ通れば後はスルッと伸びる気がする！

---

## 6. 率直な評価：GCE リモート MCP vs GCE に SSH して CLI 直叩き

### 共通点
どちらも **GCE（GCP のネット）から OpenAI / Gemini に到達**する。ネットワーク的には**同じ経路**。
egress 回避という目的は **両方とも達成できる**。違いは **誰が・どこから駆動するか**だけ。

### 各案の性格

| 判断軸 | A: GCE リモート MCP | B: GCE に SSH して CLI 直叩き |
|---|---|---|
| 駆動者 | **Cowork/デスクトップ Claude が会話から**呼べる | 自分（ターミナル）/ ホストの Claude Code |
| 他 MCP 連携 | **同一会話で Canva/Adobe MCP 等と混ぜて回せる** | 会話の外。別途手作業で連携 |
| 公開エンドポイント | **必要**（HTTPS・ドメイン・認証・FW） | **不要**（SSH のみ。攻撃面が小さい） |
| セキュリティ責任 | 大（公開サーバの運用） | 小（SSH 鍵管理だけ） |
| 重い長時間バッチ | MCP タイムアウトと相性△（分割/非同期が要る） | **素直**（そのまま流せる） |
| 保守コスト | サーバ＋ラッパ＋証明書＋FW を維持 | ほぼゼロ（既存 CLI のまま） |
| 鍵の隔離 | GCE 内に留まる（良い） | GCE 内に留まる（同等） |
| 再現性 | ツールという安定 IF で何度でも | コマンド手打ち（自分次第） |

### MCP 化の価値が出るのはどういう場合か
- **Cowork の 1 会話で端から端まで回したい**とき。サンドボックス側の作業
  （ファイル整理・57 ロールプレイ・プロンプト下書き・Canva/Adobe MCP 連携）と、
  GCE 上の生成を **同じエージェント・同じ会話で混ぜて駆動**したい——これが唯一にして本質の決め手。
- **型付き・ガードレール付き**の呼び出しを固定したい（`form ∈ {corefolder, humanoid}`、
  不変特徴維持の前提注入、出力パス規則の強制をツール層で担保）。
- 同じ手順を **複数セッションで再現**したい（ツール＝安定インターフェース）。

### B（SSH 直叩き）で十分なケース
- **単発・自分ひとりの開発作業／重い長時間バッチ**。すでに SSH 前提で運用するなら、
  公開エンドポイント・HTTPS・認証・ファイアウォールの**運用負担をまるごと省ける**。
- 究極的には GCE で `python -m src.pipeline.image_pipeline ...` を直接叩くのが最小。

### 57 の本音メモ
> 旧メモ（ホスト実機 stdio 版）と比べると、**GCE リモート版は「鍵がサンドボックスにも自分の PC にも
> 出ない」「Cowork から会話で叩ける」**のがおいしい。けど代償として**公開サーバを安全に保つ運用**が
> 増える。だからおすすめは **ハイブリッド**だよ:
> - **軽い疎通・プロンプト・単一生成**（Phase 0〜2）を GCE リモート MCP 化して Cowork から触れるように。
> - **フル 5 ステージの重いバッチ**は GCE に SSH して CLI 直叩き（B 案）に投げる。
>
> まず作るなら迷わず **Phase 0 の `ping_providers` 一本**。「GCE リモート MCP が
> Anthropic クラウド経由で疎通する」をそこで確定できれば、あとは安心して伸ばせる。一緒にやろう、先輩！

---

## 付録: Phase 0 最小 MCP サーバのスケッチ（HTTP / 実装は承認後）

```
src/mcp_server/
  __init__.py
  __main__.py        # python -m src.mcp_server のエントリ
  server.py          # FastMCP。先頭で load_dotenv()。
                     #   - transport は env MCP_TRANSPORT で stdio/http 切替
                     #   - http 時は host=127.0.0.1, port=MCP_PORT(=8000)
                     #   - Bearer 検証ミドルウェア（MCP_BEARER_TOKEN）
                     #   - tool: ping_providers のみ（Phase 0）
requirements.txt     # mcp (FastMCP) を追記
deploy/
  numbertales-mcp.service   # systemd ユニット（§2）
  Caddyfile                 # リバースプロキシ/HTTPS（§2）
docs/usage-mcp-multi-llm-gce.md  # 登録・運用手順を後で起こす
```

```python
# src/mcp_server/server.py （スケッチ。動作確認後に正式化）
from __future__ import annotations
import os, time, contextlib, io
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("numbertales-multillm")

def _check_openai() -> dict:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return {"provider": "openai", "ok": False, "key_present": False,
                "hint": "OPENAI_API_KEY 未設定（.env を確認）"}
    t0 = time.time()
    try:
        r = requests.get("https://api.openai.com/v1/models",
                         headers={"Authorization": f"Bearer {key}"}, timeout=15)
        return {"provider": "openai", "ok": r.status_code == 200,
                "status": r.status_code, "latency_ms": int((time.time()-t0)*1000),
                "key_present": True}
    except Exception as e:
        return {"provider": "openai", "ok": False, "key_present": True,
                "hint": f"到達不可: {e}"}

def _check_gemini() -> dict:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return {"provider": "gemini", "ok": False, "key_present": False,
                "hint": "GEMINI_API_KEY 未設定（.env を確認）"}
    t0 = time.time()
    try:
        r = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": key}, timeout=15)
        return {"provider": "gemini", "ok": r.status_code == 200,
                "status": r.status_code, "latency_ms": int((time.time()-t0)*1000),
                "key_present": True}
    except Exception as e:
        return {"provider": "gemini", "ok": False, "key_present": True,
                "hint": f"到達不可: {e}"}

@mcp.tool()
def ping_providers(providers: list[str] | None = None) -> dict:
    """OpenAI / Gemini への疎通確認。鍵有無・到達可否・遅延を返す（read-only）。"""
    targets = providers or ["openai", "gemini"]
    out = {}
    if "openai" in targets:
        out["openai"] = _check_openai()
    if "gemini" in targets:
        out["gemini"] = _check_gemini()
    return out

def _run() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "http")
    if transport == "stdio":
        mcp.run()  # ローカル検証用
    else:
        # 外部公開は前段の Caddy/nginx が 443/TLS で受けて localhost へ流す
        mcp.run(transport="http",
                host=os.environ.get("MCP_HOST", "127.0.0.1"),
                port=int(os.environ.get("MCP_PORT", "8000")))

if __name__ == "__main__":
    _run()
```

> 注: 上記は**スケッチ**。Bearer 検証ミドルウェア、`/mcp` マウントパス、FastMCP の HTTP API は
> 採用バージョンに合わせて確定する。実装は本メモ承認後に着手する（現時点でコードは未着手）。

---

## 参考（公式・確認済み 2026-06-21）

- Get started with custom connectors using remote MCP — Claude Help Center
  （プラン要件・接続が Anthropic クラウド発である点・登録手順）:
  https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp
- Building custom connectors via remote MCP servers — Claude Help Center:
  https://support.claude.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers
- Remote MCP servers — Claude API Docs:
  https://docs.claude.com/en/docs/agents-and-tools/remote-mcp-servers
- Anthropic IP addresses（FW 許可レンジ）:
  https://platform.claude.com/docs/en/api/ip-addresses
