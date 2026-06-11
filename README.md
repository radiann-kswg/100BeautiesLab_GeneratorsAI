# 100BeautiesLab GeneratorsAI

百花繚乱研究所（RadianN_kswg）のナンバーテールズシリーズ向け AI 画像生成補助リポジトリです。

**Copyright © RadianN_kswg（ラジアン/柏木主税） — [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)**

---

## 概要

Gemini / ChatGPT API を使用してナンバーテールズキャラクターの画像生成プロンプトを構築・検証するためのワークスペースです。
GitHub Copilot エージェントは **57(イズナ)** として作画補助を担当します。

---

## 初期セットアップ

### サブモジュールの取得

```bash
git submodule update --init --recursive
```

または、クローン時に含める場合:

```bash
git clone --recurse-submodules <このリポジトリのURL>
```

### サブモジュール一覧

| ディレクトリ     | リポジトリ                                                                                         | 用途                |
| ---------------- | -------------------------------------------------------------------------------------------------- | ------------------- |
| `_creations-ai/` | [100BeautiesLab_CreationsAI](https://github.com/radiann-kswg/100BeautiesLab_CreationsAI)           | AI 学習データセット |
| `_creations-db/` | [100BeautiesLab_CreationsDB](https://github.com/radiann-kswg/100BeautiesLab_CreationsDB) (develop) | キャラクター原典 DB |

---

## ディレクトリ構成

```
├── AGENTS.md               # Copilot エージェント指示
├── .github/
│   ├── copilot-instructions.md      # Copilot 全体指示
│   ├── instructions/                # applyTo 付き自動ロード指示
│   └── _roleplay-datas/             # Copilot ロールプレイ設定 (正本)
├── _creations-ai/          # AI 学習データ（サブモジュール）
├── _creations-db/          # キャラクター DB（サブモジュール・読み取り専用）
├── _ideas/                 # プロンプト草案・アイデア
├── docs/                   # 使い方ドキュメント (docs/README.md が入口)
└── src/                    # 生成スクリプト
```

---

## 使い方ドキュメント

セットアップやコマンドの詳細は [`docs/README.md`](docs/README.md) を参照してください。

- 環境準備: [`docs/setup.md`](docs/setup.md)
- 生成コマンド: [`docs/usage-generation.md`](docs/usage-generation.md)
- i2i 改稿 (`--iterate-from`): [`docs/usage-iterate.md`](docs/usage-iterate.md)
- 出力レイアウト / 実行ログ: [`docs/output-and-logs.md`](docs/output-and-logs.md)
- 補助ツール / 形態共通データセット: [`docs/tools.md`](docs/tools.md)

---

## ライセンス

- 本リポジトリの設定ファイル・スクリプト: CC BY-NC 4.0
- `_creations-ai/`, `_creations-db/` 内コンテンツ: 各サブモジュールのライセンスに従う
- 非商用目的に限り利用可。商用利用・再配布には著作権者の許諾が必要。
