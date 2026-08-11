# AppearanceDetail 充足性レビュー（配色検知ツール向け） — 57(イズナ) / corefolder

配色検知ツール (`tools/patch-colorpalette.mjs`) は `AppearanceDetail` の色語から
`ColorPalette.AppliesTo`（その色がどの部位か）を転記する。したがって **色語を含むエントリに
`BodyPart` が無いと、検出した色を部位へ紐づけられない**。
以下は上流の `collectColorHints()` / `colorWordMatchesHex()` を直接呼んで得た充足状況で、
判定ロジックの再実装はしていない。

- 判定日: 2026-08-11
- 色語ヒントを持つエントリ: 1 / 5
- **BodyPart 欠落: 0 件**（AppliesTo へ転記できない）
- **根拠となる色語が無い ColorPalette: 1 色** / 全 5 色
- 色語ヒント 0 のエントリ: 4 件（色語表に無い語の可能性）
- 部位候補: 公式画像 `emstk_corefolderNTS-57-1.png`, `emstk_corefolderNTS-57-2.png`, `cnsp_imgNTS-57.png` から `gpt-4o` が提案

## 1. BodyPart 欠落（最優先）

なし。色語を含むエントリにはすべて `BodyPart` が入っている。

## 2. 根拠となる色語が無い ColorPalette

| HEX | Role | 現在の AppliesTo | 画像からの部位候補 |
|---|---|---|---|
| `#F7FFB9` | #ColorRole_Accent | — | `#BodyPart_Ear` (耳) — #F7FFB9 が耳の内側に塗られています。 |

## 3. 色語ヒント 0 のエントリ（参考）

配色ツールの色語表に載っている語が記述に含まれていない。形状のみを述べたエントリなら正常。
`blonde` / `amber` のような色を指す語は現在の色語表に無いため、拾われない。

| # | BodyPart | DesignElement | 記述 |
|---|---|---|---|
| 3 | `#BodyPart_Ear` (耳) | `#Element_Ear` | #DesignAttr_Ear: #EarShapeType_Fox |
| 4 | `#BodyPart_Hair` (髪) | `#Element_Motif` | #DesignAttr_Overview: blonde ponytail |
| 5 | `#BodyPart_Eye` (目・瞳) | `#Element_Motif` | #DesignAttr_Overview: amber eyes |
| 11 | `#BodyPart_Shoulder` (肩), `#BodyPart_Arm` (腕) | `#Element_Motif` | #DesignAttr_Overview: armband with number on right shoulder |

---

*部位候補は AI が公式画像から推定した**下書き**です。DB へ反映する前に原典設定で確認してください。*

自動生成: `python -m src.tools.verify_appearance_detail --num 57 --check coverage --form corefolder` (100BeautiesLab_GeneratorsAI)
