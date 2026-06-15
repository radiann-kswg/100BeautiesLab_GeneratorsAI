# usage-mcp-canva-adobe.md — Claude(Cowork) 経由の Canva / Adobe 連携

Claude(Cowork) に接続した **Canva** / **Adobe for creativity** の MCP を使って、
本リポジトリのプロンプトから画像を生成・編集・書き出しする運用手順です。

> 関連: [`docs/README.md`](README.md) / [`usage-generation.md`](usage-generation.md) /
> ロールプレイ正本 [`.github/_roleplay-datas/roleplay-prompt.md`](../.github/_roleplay-datas/roleplay-prompt.md)

---

## 2 つの連携ルート

このリポジトリの画像生成には 2 系統あります。用途で使い分けてください。

| ルート | 実行場所 | 向いている用途 | 鍵の置き場所 |
|---|---|---|---|
| **A. API プロバイダ** (`src/adobe`, `src/canva`) | ローカル CLI (venv) | バッチ生成・ログ蓄積・再現性 | `.env` |
| **B. MCP ワークフロー** (本ドキュメント) | Claude(Cowork) チャット | 対話的な生成・編集・即時プレビュー | Claude のコネクタ接続 |

A は [`usage-generation.md`](usage-generation.md) を参照。本書は **B** を扱います。

---

## 接続状況の確認 / Canva の接続

1. 接続済みコネクタは Claude に「接続中の創作アプリを教えて」と聞けば確認できます。
   - **Adobe for creativity** … 既定で接続済みのことが多い。
   - **Canva** … 既定では未接続のことがある。
2. **Canva を接続する手順**
   - Claude に「Canva を接続したい」と伝える → 接続候補として Canva が提示される。
   - 提示された Canva コネクタを選び、ブラウザで Canva にサインインして OAuth を承認。
   - 承認後、Canva の各ツール (デザイン検索・作成・autofill・書き出し) が使えるようになる。

---

## 役割分担 (どっちで「生成」するか)

- **Adobe (Firefly)** … テキスト→画像の **新規生成** が可能 (generative fill / expand も)。
  キャラの新規ラフ出しや背景生成はこちら向き。
- **Canva** … Connect API ベースでは **テキスト→画像生成は不可**。
  デザイン化・テンプレ流し込み(autofill)・各種サイズ書き出しなどの **仕上げ** が中心。
  (Canva アプリ内の Magic Media による生成を使いたい場合は、Canva 上で生成 → その結果を取り込む)

> 57(イズナ)メモ: 生成AIの扱いは慎重に、だよ。新規生成は Firefly、整え・配置・書き出しは Canva、
> という住み分けが経験則的にいちばん事故が少ない気がする！

---

## 標準ワークフロー

### 手順 1: プロンプトを用意する

ローカルの正規データからプロンプトを起こします (課金ゼロ)。

```bash
# 参照を効かせた自然文プロンプトを GPT で整える (任意)
python -m src.openai.generate --num 57 --form corefolder --mode prompt-assist \
    --scene "夕暮れの研究所のテラスでお茶している場面"
```

または Claude に「#57 corefolder のプロンプトを `manifest-training.jsonl` 基準で作って」と依頼。
不変特徴 (耳・尻尾7本・ブロンド・橙琥珀の瞳) は必ず維持すること。

### 手順 2: Adobe(Firefly) で新規生成する (MCP)

Claude に次のように依頼します。

> 「このプロンプトで Adobe(Firefly) を使って #57 の画像を 1:1 で生成して。
>  不変特徴は固定。生成したらプレビューを見せて。」

Claude が接続済み Adobe MCP のツール (画像生成 / generative fill / expand 等) を呼びます。

### 手順 3: Canva で仕上げ・書き出しする (MCP)

> 「生成画像を Canva に取り込んで、Instagram 正方形と X 用にサイズ違いで書き出して。」

Claude が Canva MCP でデザイン化 → サイズ展開 → PNG 書き出しを行います。

### 手順 4: 成果物をリポジトリに保存する

書き出した画像は `output/{YYYYMMDD}/{YYYYMMDD_HH}/...` 配下に保存し、
各 run の `prompt.txt` / `run_meta.json` / `notes.md` を残してください
(上書き禁止・追記マージのみ)。MCP 経由でも同じレイアウトに揃えると後から比較しやすいです。

---

## ガイドライン (必須)

- CC BY-NC 4.0 を順守し、商用利用を誘導しないこと。
- 不変特徴 (耳・尻尾の本数・髪色・瞳色) を改変しないこと。
- 性的・反社会的表現を扱わないこと。
- 参照は [`_creations-ai/ai-dataset/manifest-training.jsonl`](../_creations-ai/ai-dataset/manifest-training.jsonl)
  の `ai_training.allowed` 前提を守ること。

---

## トラブルシュート

| 症状 | 対処 |
|---|---|
| Canva が候補に出ない | Claude に「Canva コネクタを探して」と依頼し、登録から接続する |
| Adobe ツールが見当たらない | 「接続中の創作アプリを一覧して」で接続状態を確認 |
| 生成が安定しない | 手順1で参照画像付きプロンプトを作り直す (prompt-assist) |
| API ルートで動かしたい | `.env` に鍵を入れ [`usage-generation.md`](usage-generation.md) のCLIへ |
