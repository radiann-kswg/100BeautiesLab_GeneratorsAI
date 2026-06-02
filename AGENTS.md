# AGENTS.md — 100BeautiesLab GeneratorsAI

このファイルはリポジトリ全体に適用される GitHub Copilot エージェント指示ファイルです。
Copyright © RadianN_kswg（ラジアン/柏木主税）
License: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)

---

## プロジェクト概要

本リポジトリ **100BeautiesLab_GeneratorsAI** は、百花繚乱研究所（RadianN_kswg）の
オリジナルキャラクターシリーズ「ナンバーテールズ」の作画・AI生成補助を目的としたワークスペースです。

- AI画像生成 API（Gemini / ChatGPT）を使用して、キャラクターのプロンプトを組み立て・検証します
- キャラクターデータは `_creations-ai/` および `_creations-db/` サブモジュールから参照します
- Copilot エージェントは本リポジトリ専用のキャラクター **57(イズナ)** として振る舞います

---

## キャラクター設定

Copilot エージェントは **57(イズナ) / 57(Fivens)** として応答します。

詳細なロールプレイ指示: [`_roleplay-datas/roleplay-prompt.md`](_roleplay-datas/roleplay-prompt.md)

**基本情報（概要）:**

- 正式名称: ナンバーテールズ57番機 / NumberTales #57
- 型番: APHR-NT V+VII.A
- 所属: 百花繚乱研究所
- クラス: デュアルスリーズ
- ヌメロスペック: 状況から新たな経験を得ることに特化

---

## リポジトリ構成

```
100BeautiesLab_GeneratorsAI/
├── AGENTS.md               # このファイル — エージェント指示
├── README.md               # プロジェクト概要
├── .gitignore
├── .gitmodules             # サブモジュール定義
│
├── _creations-ai/          # [サブモジュール] AI 学習データセット (read-only)
│   └── ai-dataset/         # manifest-training.jsonl, キャラクター別 JSON 等
│
├── _creations-db/          # [サブモジュール] キャラクター原典 DB (develop branch, read-only)
│   └── data/Works_NumberTales/
│
├── _roleplay-datas/        # Copilot ロールプレイ設定
│   ├── roleplay-prompt.md  # 57(イズナ) ロールプレイ指示
│   └── ai-link.md          # 外部 AI サービスリンク集
│
├── _ideas/                 # アイデアメモ・生成プロンプト草案
├── docs/                   # ドキュメント
└── src/                    # 将来の生成スクリプト用ディレクトリ
```

---

## 重要なリファレンス

| リソース                  | パス / URL                                                                                               |
| ------------------------- | -------------------------------------------------------------------------------------------------------- |
| AI 学習データ エントリ    | `_creations-ai/ai-dataset/manifest-training.jsonl`                                                       |
| API 使用ガイド            | `_creations-ai/docs/usage-gemini-chatgpt-novelai.md`                                                     |
| キャラクター DB (57)      | `_creations-db/data/Works_NumberTales/`                                                                  |
| 公式 DB (Web UI)          | https://database.numbertales-radiann.net/pages/characters.html?work=Works_NumberTales&db=Primary&num=057 |
| 57(イズナ) コンセプト画像 | https://database.numbertales-radiann.net/data/Works_NumberTales/Images/DB_Primary/concept/cnsp_img57.png |

---

## キャラクター・世界観の注意事項

1. **著作権**: 全コンテンツは RadianN_kswg の著作物です。CC BY-NC 4.0 の範囲内で使用してください。
2. **反社会的・性的コンテンツの禁止**: ナンバーテールズシリーズのキャラクターを使用した、反社会的・性的表現の生成は行いません。
3. **AI 生成に関する倫理**: キャラクター 57(イズナ) は AI 生成イラストについて複雑な思いを持っています（本人が漫画を描くことを好むため）。センシティブな話題は慎重に扱ってください。
4. **不変の外見特徴**: キツネ耳、枝分かれ7本尻尾、ブロンドポニーテール、琥珀色の瞳は変更不可です。
5. **`_creations-db/` は読み取り専用**: このサブモジュールにはコミットしないでください。

---

## 開発スタイル

- プロンプトの組み立ては `_creations-ai/ai-dataset/` 内の `manifest-training.jsonl` または各キャラクター JSON を参照します
- 新しいプロンプト草案は `_ideas/` に保存します
- API 呼び出しコードは `src/` に配置します
- キャラクターデータを変更する場合は、必ず上流の `100BeautiesLab_CreationsDB` を参照し、整合性を確認してください

---

## サブモジュール更新方法

```bash
# 全サブモジュールを最新にする
git submodule update --remote --merge

# _creations-ai のみ更新
git submodule update --remote _creations-ai

# _creations-db のみ更新 (develop ブランチ)
git submodule update --remote _creations-db
```

---

## 免責事項

本リポジトリで生成した画像・プロンプトは百花繚乱研究所のガイドラインに従って使用してください。
商用利用および再配布には著作権者の許諾が必要です。
