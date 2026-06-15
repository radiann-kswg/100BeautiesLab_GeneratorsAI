# LICENCE — 100BeautiesLab_GeneratorsAI

**Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)**

100BeautiesLab.(百花繚乱研究所) Primary Works/Creations and derivatives
Copyright © 2021–2026 RadianN_kswg（ラジアン / 柏木主税）

This work is licensed under the Creative Commons Attribution-NonCommercial 4.0
International License. To view a copy of this license, visit:
http://creativecommons.org/licenses/by-nc/4.0/

> 本リポジトリ（`100BeautiesLab_GeneratorsAI`）は、原典データベース
> [`100BeautiesLab_CreationsDB`](https://github.com/radiann-kswg/100BeautiesLab_CreationsDB) を
> ネストサブモジュール（`_creations-ai/creations-db`）として参照する、
> **非公式・非営利**の AI 画像生成補助リポジトリです。
> 原典 DB のライセンス（CC BY-NC 4.0）を継承し、これに準拠します。

---

## 1. ライセンスの継承 / Licence Inheritance

本リポジトリは、原典である百花繚乱研究所の一次創作作品データベースが
CC BY-NC 4.0 で提供されていることを受け、リポジトリ全体に同一ライセンスを適用します。

| 区分 | 取得元 | ライセンス |
|---|---|---|
| 原著作物（キャラクター設定・画像・JSON） | [100BeautiesLab_CreationsDB](https://github.com/radiann-kswg/100BeautiesLab_CreationsDB) | CC BY-NC 4.0 |
| AI 学習用整形データ（サブモジュール経由） | [100BeautiesLab_CreationsAI](https://github.com/radiann-kswg/100BeautiesLab_CreationsAI) | CC BY-NC 4.0（継承） |
| 本リポジトリのコード・ドキュメント・プロンプト | 本リポジトリ | CC BY-NC 4.0 |
| 本リポジトリで生成された画像・出力物（`output/` 等） | 本リポジトリ（原著作物の派生物） | CC BY-NC 4.0（継承） |

原著作物の権利はすべて **RadianN_kswg（ラジアン / 柏木主税）** に帰属します。
本リポジトリで生成される画像は CC BY-NC 4.0 で保護された創作データに基づく**派生物**であり、
同ライセンス条件（特に非営利条件）を引き継ぎます。

CC BY-NC 4.0 の完全な法文は、サブモジュール内の以下に同梱されています。

- `_creations-ai/LICENCE`
- `_creations-ai/creations-db/LICENCE`

---

## 2. 適用範囲 / Scope

本ライセンスは、本リポジトリに含まれる次のすべてに適用されます。

- ソースコード（`src/`, `scripts/`）およびドキュメント（`docs/`, `README.md`, `AGENTS.md` 等）
- プロンプト草案・アイデア（`_ideas/`）、形態共通データセット
- 本リポジトリのツールを用いて生成された画像・テキスト・実行ログ等の出力物
- サブモジュール経由で参照される原著作物データ（その権利は原著者に帰属）

なお、第三者ライブラリ（`requirements.txt` に列挙された Python パッケージ等）は、
各配布元のライセンスに従います。本ライセンスはそれらの第三者著作物には及びません。

---

## 3. 許可される利用 / Permitted Use

CC BY-NC 4.0 の下で、**非営利目的**に限り以下が許可されます。

- 複製・共有（コード・データ・生成物の全部または一部）
- 改変・翻案（プロンプトの改良、生成物の加工等）

### 帰属表示（必須） / Attribution

共有・再配布の際は、少なくとも次を明記してください。

- 作品名／DB 名：百花繚乱研究所 一次創作作品 / 100BeautiesLab CreationsDB
- 著作者：RadianN_kswg（ラジアン / 柏木主税）
- 出典リンク：https://github.com/radiann-kswg/100BeautiesLab_CreationsDB
- ライセンス表記：CC BY-NC 4.0（http://creativecommons.org/licenses/by-nc/4.0/）
- 改変した場合はその旨

---

## 4. 制限・禁止事項 / Restrictions

原典 DB の[ガイドライン](https://github.com/radiann-kswg/100BeautiesLab_CreationsDB/blob/develop/guideline.md)
および[第三者ポリシー](https://github.com/radiann-kswg/100BeautiesLab_CreationsDB/blob/develop/docs/third-party-policy.md)を尊重し、以下を遵守してください。
（ローカル参照: `_creations-ai/creations-db/guideline.md` / `_creations-ai/creations-db/docs/third-party-policy.md`）

### 4.1 商用利用（原則禁止）

データ・API・画像・生成物の商用利用（有料アプリ、広告収益主目的のサイト、
商用プロダクトへの組み込み等）は原則禁止です。例外は原著者の**明示的な個別許可**がある場合のみ。

### 4.2 AI 学習 / データセット化（非営利・条件付き）

非営利の範囲でのみ許可します。利用時は以下をすべて満たすこと。

1. 出典（リポジトリ URL 等）を明記する
2. 非営利目的に限定する（商用モデルの学習・商用サービスへの組み込みは原則禁止）
3. 改変・加工した場合はその旨を明記する

推奨入口は `_creations-ai/ai-dataset/manifest-training.jsonl`（`ai_training.allowed = true` のレコードのみ）です。

### 4.3 再配布（非推奨）

データ・画像のミラー／再配布は混乱回避のため原則避け、本家へのリンク参照を推奨します。
やむを得ず再配布する場合は「出典リンク明記・改変点明記・**公式ではない旨の明示**」を守ってください。
公式関係者を装うなりすまし、公式承認と誤認させる表現は禁止します。

### 4.4 表現上の禁止事項

原典ガイドラインに基づき、以下を禁止します。

- 反社会的・良俗に反する表現、および過度に性的な表現
- ナンバーテールズへの性器・精液に関わる表現全般（身体構造上、無性別のため）
- キャラクター不変特徴（耳・尻尾数・髪色・瞳色）の無断改変
- 作者偽称、作品の印象を著しく損なう運用、ヘイト・名誉毀損的な運用
- その他、原典ガイドラインの「違反行為」に該当する一切の行為

---

## 5. 免責 / Disclaimer

本リポジトリは「百花繚乱研究所」の**非公式・非営利**の創作補助リポジトリです。
原著作物はすべて「AS-IS（現状有姿）」で提供され、いかなる保証も行いません。
利用により生じた損害について、原著者および本リポジトリは責任を負いません
（CC BY-NC 4.0 第5条に準拠）。

---

## 6. 連絡先 / Contact

例外許可（商用利用・AI 学習・再配布等）の相談、ガイドライン違反の報告は以下へ。

- メール：radiann.kswg6631＠gmail.com
- 原典 DB Issues：https://github.com/radiann-kswg/100BeautiesLab_CreationsDB/issues
- ホームページ：https://www.numbertales-radiann.com / https://database.numbertales-radiann.net

---

*This repository inherits and complies with the CC BY-NC 4.0 licence of its
source database. 本リポジトリは原典 DB の CC BY-NC 4.0 を継承し、これに準拠します。*
