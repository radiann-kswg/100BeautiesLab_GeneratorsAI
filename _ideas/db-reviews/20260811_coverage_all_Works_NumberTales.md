# AppearanceDetail 充足性レビュー（配色検知ツール向け・一括） — #Works_NumberTales

配色検知ツール (`tools/patch-colorpalette.mjs`) は `AppearanceDetail` の色語から
`ColorPalette.AppliesTo` を転記する。**色語が拾えない／`BodyPart` が無い**と、
検出した色を部位へ紐づけられない。以下はその不足の一覧。

判定は上流 `tools/extract-palette.mjs` の `collectColorHints()` / `colorWordMatchesHex()` を
直接呼んで得ている（判定ロジックの再実装なし）。形態では絞っていない（欠落は形態に依らないため）。

- 判定日: 2026-08-11
- 対象レコード: 111 件
- **BodyPart 欠落: 71 件 / 49 キャラ**
- **根拠となる色語が無い ColorPalette: 197 色 / 83 キャラ**
- 色語表に無い色語: 7 種

## 1. 色語表に無い色語（配色ツール側で対応すると全キャラに効く）

記述には色が書かれているのに `COLOR_WORD_RANGES` に該当語が無く、ヒントが生成されないもの。
色語の抽出には `gpt-4o` を使用（画像は見ていない）。

| 色語 | 出現 | キャラ数 | 記述例 |
|---|---|---|---|
| **dark** | 22 | 19 | `the front-left chest of the top / dark / Arabic numeral '3'` |
| **dark color** | 5 | 4 | `on left shoulder, around right just below the edge of the spherical ho…` |
| **amber** | 5 | 5 | `amber eyes` |
| **light** | 1 | 1 | `small area from the center of the sweater collar to the cleavage / lig…` |
| **light color** | 1 | 1 | `left collar, around the neck / light color / Roman numeral 'LI' (sligh…` |
| **blonde** | 1 | 1 | `blonde ponytail` |
| **burgundy** | 1 | 1 | `burgundy double-breasted vest dress with number markings` |

## 2. BodyPart 欠落（DB 側の記述で埋める）

色語は拾えているのに `BodyPart` が空で、`AppliesTo` へ転記できないエントリ。

| キャラ | # | DesignElement | 記述 | 色語 |
|---|---|---|---|---|
| 11(トウイチ) | 5 | `#Element_Expression` | divine self-assured composure / Slightly rampaging (when in a hyper-focused state) | red |
| 14(トヨ) | 9 | `#Element_Motif` | teal blazer(sometimes worn casually or taken off) | cyan |
| 17(トナ) | 4 | `#Element_Motif` | short blue indigo bob | blue |
| 20(ハツカ) | 9 | `#Element_Motif` | orange inner wear | orange |
| 27(ツギナ) | 9 | `#Element_Motif` | four white buttons | white |
| 28(ニハチ) | 14 | `#Element_Motif` | red blazer (2 outfit variants) | red |
| 34(サトシ) サンジ | 9 | `#Element_Motif` | yellow apron with numbers, resembling an employee uniform | yellow |
| 37(サナ) | 7 | `#Element_Motif` | red blazer with blue trim | blue, red |
| 40(ヨソ) | 9 | `#Element_Motif` | pattern inspired by '40' | red |
| 41(ヨソイチ) | 7 | `#Element_Motif` | open teal blazer | cyan |
| 42(ヨツグ) | 5 | `#Element_Motif` | blue eyes | blue |
| 42(ヨツグ) | 6 | `#Element_Motif` | blue eyes | blue |
| 42(ヨツグ) | 8 | `#Element_Motif` | light pink long blazer | pink |
| 46(シロー) | 7 | `#Element_Motif` | red eyes | red |
| 47(シナ) | 6 | `#Element_Motif` | navy miko outfit with number | blue |
| 50(ナカバ) | 9 | `#Element_Motif` | green tunic | green |
| 51(イソイチ) | 6 | `#Element_Emblem` | original green casual wear with diagonal patterns | green |
| 51(イソイチ) | 7 | `#Element_Motif` | dark green belt with pale-colored charm | green, red |
| 52(イツギ) | 10 | `#Element_Motif` | gray inner layer | gray |
| 53(イツゾウ) | 8 | `#Element_Motif` | orange apron jumper | orange |
| 55(イソゴ) | 10 | `#Element_Motif` | dark green long sleeves | green |
| 55(イソゴ) | 11 | `#Element_Motif` | white inner collar | white |
| 57(イズナ) | 6 | `#Element_Motif` | yellow blazer | yellow |
| 57(イズナ) | 9 | `#Element_Motif` | yellow sailor-collar uniform with white stripes | white, yellow |
| 63(ムツミ) | 9 | `#Element_Motif` | orange accents | orange |
| 66(ムロク) | 7 | `#Element_Motif` | orange-yellow yoke bib with number markings | orange, yellow |
| 66(ムロク) | 9 | `#Element_Motif` | pink puff sleeves | pink |
| 66(ムロク) | 11 | `#Element_Motif` | yellow trim accents | yellow |
| 67(ムナ) | 6 | `#Element_Motif` | pale reddish-purple trainer wear | purple, red |
| 67(ムナ) | 6 | `#Element_Motif` | pale reddish-purple trainer wear | purple, red |
| 68(ロクヤ) | 10 | `#Element_Motif` | light brown workwear (work outfit) | brown |
| 69(ロック) | 5 | `#Element_Motif` | light pink cape-like collar | pink |
| 69(ロック) | 8 | `#Element_Motif` | red eyes | red |
| 69(ロック) | 11 | `#Element_Motif` | white buttons | white |
| 70(ナナト) | 8 | `#Element_Motif` | light blue armwear with white lines and purple accents | blue, purple, white |
| 72(ナフタ) | 10 | `#Element_Tag` | barcode-style numbered tag | red |
| 74(ナナヨ) | 3 | `#Element_Motif` | translucent white shawl/cape with number marking | white |
| 74(ナナヨ) | 6 | `#Element_Motif` | blue off-shoulder wrap top | blue |
| 75(シチゴ) | 5 | `#Element_Motif` | yellow eyes | yellow |
| 84(ヤツヨ) | 7 | `#Element_Motif` | orange neckerchief | orange |
| 85(ハッコ) 85(パコ) | 8 | `#Element_Motif` | cyan blue off-shoulder neckline | blue, cyan |
| 86(ハチロ) | 7 | `#Element_Motif` | cream-colored apron | red, white |
| 88(ヤソハチ) | 5 | `#Element_Motif` | red eyes | red |
| 89(ヤスモ) | 6 | `#Element_Motif` | red eyes | red |
| 92(コトジ) | 5 | `#Element_Motif` | cream-beige inner tank-top | brown, white |
| 93(クミ) | 5 | `#Element_Motif` | yellow eyes | yellow |
| 94(ツクシ) | 5 | `#Element_Motif` | blue eyes (usually closed) | blue |
| 94(ツクシ) | 6 | `#Element_Motif` | blue innerwear | blue |
| 96(クルリ) | 5 | `#Element_Motif` | pink masquerade mask with number decoration (occasionally worn) | pink |
| 96(クルリ) | 8 | `#Element_Motif` | pink one-piece dress with white collar (casual wear) | pink, white |
| 98(キュウヤ) | 5 | `#Element_Motif` | red eyes | red |
| 99(ツクモ) | 8 | `#Element_Halo` | pink light-ring halo behind head | pink |
| 99(ツクモ) | 11 | `#Element_Motif` | pink-and-white striped inner kimono | pink, white |
| バイナ 2(ツギ) | 6 | `#Element_Tag` | orange '試用' (trial / test) label | orange |
| バイナ 2(ツギ) | 9 | `#Element_Motif` | amber-orange eyes | orange |
| ディケ 10(ツナイ) | 9 | `#Element_Motif` | red support pillar (base) | red |
| 000(チトセ) | 5 | `#Element_Motif` | yellow eyes | yellow |
| 000(チトセ) | 8 | `#Element_Motif` | yellow eyes | yellow |
| 000(チトセ) | 10 | `#Element_CostumeItem` | casual suit resembling a white coat | white |
| 零 零 | 5 | `#Element_Motif` | green-brown eyes | brown, green, red |
| 零 零 | 7 | `#Element_CostumeItem` | casual suit resembling a white coat | white |
| 零 百 | 7 | `#Element_CostumeItem` | casual suit resembling a white coat | white |
| 111(アイズ) | 9 | `#Element_CostumeItem` | dark red military-style uniform | red |
| 444(シテン) | 5 | `#Element_Expression` | stands majestically (normal state) / occasionally becomes overly defensive to protect prid… | brown |
| 777(ヨロコビ) | 8 | `#Element_Motif` | gray tracksuit resembling gym clothes | gray |
| 777(ヨロコビ) | 7 | `#Element_CostumeItem` | wearing a dark yellow slot machine-type addon and functioning like a slot machine | yellow |
| 777(ヨロコビ) | 9 | `#Element_Motif` | gray tracksuit resembling gym clothes | gray |
| 量産型 111(アイズ) | 10 | `#Element_CostumeItem` | red military-style uniform | red |
| 量産型 777(ヨロコビ) | 9 | `#Element_Motif` | gray tracksuit resembling gym clothes | gray |
| 量産型 777(ヨロコビ) | 8 | `#Element_CostumeItem` | wearing a dark yellow slot machine-type addon and functioning like a slot machine | yellow |
| 量産型 777(ヨロコビ) | 10 | `#Element_Motif` | gray tracksuit resembling gym clothes | gray |

## 3. 根拠となる色語が無い ColorPalette

検出済みの色に対応する色語が記述に無く、`AppliesTo` を決められないもの。
1 の色語を追加すると解消するものが含まれる。

| キャラ | HEX | Role | 現在の AppliesTo |
|---|---|---|---|
| 1(ハジメ) | `#FFBFA7` | #ColorRole_Sub | — |
| 2(ツグ) | `#FFA073` | #ColorRole_Primary | — |
| 2(ツグ) | `#FFA579` | #ColorRole_Accent | — |
| 2(ツグ) | `#FFCFAE` | #ColorRole_Sub | — |
| 2(ツグ) | `#FFE6D5` | #ColorRole_Sub | — |
| 3(ナオ) | `#F7FFB9` | #ColorRole_Sub | — |
| 8(ワカツ) | `#FFA9A8` | #ColorRole_Secondary | — |
| 8(ワカツ) | `#FC6932` | #ColorRole_Sub | — |
| 9(チカ) | `#A1A9BF` | #ColorRole_Primary | — |
| 9(チカ) | `#484551` | #ColorRole_Secondary | — |
| 9(チカ) | `#5F676F` | #ColorRole_Accent | — |
| 9(チカ) | `#445465` | #ColorRole_Sub | — |
| 9(チカ) | `#B2AFCF` | #ColorRole_Sub | — |
| 9(チカ) | `#A5ADC2` | #ColorRole_Sub | — |
| 11(トウイチ) | `#8B9BAC` | #ColorRole_Secondary | — |
| 11(トウイチ) | `#FFAC8F` | #ColorRole_Sub | — |
| 11(トウイチ) | `#C6CCD8` | #ColorRole_Sub | — |
| 11(トウイチ) | `#E7ECE9` | #ColorRole_Sub | — |
| 12(トウジ) | `#FFAC8F` | #ColorRole_Primary | — |
| 12(トウジ) | `#FFD7C2` | #ColorRole_Secondary | — |
| 12(トウジ) | `#FFEFE4` | #ColorRole_Sub | — |
| 12(トウジ) | `#FEF3D9` | #ColorRole_Sub | — |
| 14(トヨ) | `#FFC5BC` | #ColorRole_Secondary | — |
| 15(トウゴ) | `#FFB1AB` | #ColorRole_Primary | — |
| 15(トウゴ) | `#FFC4A6` | #ColorRole_Accent | — |
| 15(トウゴ) | `#E8EDBE` | #ColorRole_Sub | — |
| 15(トウゴ) | `#FFD7C9` | #ColorRole_Sub | — |
| 16(ソロク) | `#A4A2C3` | #ColorRole_Accent | — |
| 16(ソロク) | `#F9BBC1` | #ColorRole_Sub | — |
| 17(トナ) | `#938FAD` | #ColorRole_Sub | — |
| 17(トナ) | `#B2B0CF` | #ColorRole_Sub | — |
| 18(トウヤ) | `#FFAC8F` | #ColorRole_Sub | — |
| 18(トウヤ) | `#F9642D` | #ColorRole_Sub | — |
| 19(トク) | `#FFB1AB` | #ColorRole_Accent | — |
| 19(トク) | `#423F3F` | #ColorRole_Sub | — |
| 20(ハツカ) | `#FFDCAE` | #ColorRole_Sub | — |
| 21(ハツヒ) | `#FFAC8F` | #ColorRole_Primary | — |
| 21(ハツヒ) | `#FFD7C2` | #ColorRole_Accent | — |
| 21(ハツヒ) | `#FEF3D9` | #ColorRole_Sub | — |
| 23(ツグミ) | `#C2F2DE` | #ColorRole_Secondary | — |
| 24(フトシ) | `#0097C9` | #ColorRole_Secondary | — |
| 24(フトシ) | `#AEB8DB` | #ColorRole_Sub | — |
| 24(フトシ) | `#FCE8EC` | #ColorRole_Sub | — |
| 25(フィズ) | `#D3DBDC` | #ColorRole_Sub | — |
| 26(ニロク) | `#F9BBC0` | #ColorRole_Primary | — |
| 26(ニロク) | `#F4ABB4` | #ColorRole_Secondary | — |
| 26(ニロク) | `#FFA79B` | #ColorRole_Sub | — |
| 27(ツギナ) | `#A4A2C3` | #ColorRole_Sub | — |
| 28(ニハチ) | `#DB653F` | #ColorRole_Primary | — |
| 29(ニトク) | `#B2B0CE` | #ColorRole_Accent | — |
| 29(ニトク) | `#CEC7B6` | #ColorRole_Sub | — |
| 32(ミツギ) | `#C2F2DE` | #ColorRole_Primary | — |
| 33(ミサ) | `#FFD5BD` | #ColorRole_Secondary | — |
| 33(ミサ) | `#FFBDA7` | #ColorRole_Accent | — |
| 33(ミサ) | `#FFDECA` | #ColorRole_Sub | — |
| 33(ミサ) | `#FFD9C4` | #ColorRole_Sub | — |
| 33(ミサ) | `#FFE5CE` | #ColorRole_Sub | — |
| 34(サトシ) サンジ | `#A4DAEF` | #ColorRole_Sub | — |
| 36(ミトム) | `#FFA79B` | #ColorRole_Secondary | — |
| 37(サナ) | `#FFD47A` | #ColorRole_Sub | — |
| 39(サク) | `#C1A072` | #ColorRole_Primary | — |
| 39(サク) | `#9A6A4E` | #ColorRole_Secondary | — |
| 39(サク) | `#FFF4DF` | #ColorRole_Accent | — |
| 39(サク) | `#FFD07D` | #ColorRole_Sub | — |
| 39(サク) | `#F6FFD2` | #ColorRole_Sub | — |
| 40(ヨソ) | `#D4F6F2` | #ColorRole_Secondary | — |
| 41(ヨソイチ) | `#FFC5BC` | #ColorRole_Secondary | — |
| 41(ヨソイチ) | `#000101` | #ColorRole_Sub | — |
| 42(ヨツグ) | `#0097C9` | #ColorRole_Sub | — |
| 43(シトミ) | `#FCCD2F` | #ColorRole_Sub | — |
| 43(シトミ) | `#A4DAEF` | #ColorRole_Sub | — |
| 43(シトミ) | `#000001` | #ColorRole_Sub | — |
| 45(シゴ) | `#010102` | #ColorRole_Sub | — |
| 46(シロー) | `#CACDCC` | #ColorRole_Accent | — |
| 47(シナ) | `#8B9BAC` | #ColorRole_Sub | — |
| 48(シハチ) | `#9EA388` | #ColorRole_Primary | — |
| 48(シハチ) | `#EF9D46` | #ColorRole_Accent | — |
| 48(シハチ) | `#CACDCB` | #ColorRole_Sub | — |
| 48(シハチ) | `#FFD07D` | #ColorRole_Sub | — |
| 50(ナカバ) | `#C2F2DE` | #ColorRole_Accent | — |
| 50(ナカバ) | `#DCF8F3` | #ColorRole_Sub | — |
| 51(イソイチ) | `#FFB1AB` | #ColorRole_Secondary | — |
| 51(イソイチ) | `#E8EDBE` | #ColorRole_Accent | — |
| 51(イソイチ) | `#FFD7C9` | #ColorRole_Sub | — |
| 52(イツギ) | `#D4DBDC` | #ColorRole_Accent | — |
| 57(イズナ) | `#F7FFB9` | #ColorRole_Accent | — |
| 58(イソヤ) | `#CACDCB` | #ColorRole_Primary | — |
| 58(イソヤ) | `#EF9D46` | #ColorRole_Accent | — |
| 58(イソヤ) | `#C48455` | #ColorRole_Sub | — |
| 60(ムソウ) | `#FFA79B` | #ColorRole_Primary | — |
| 61(ロクイチ) 61(ロイ) | `#A4A2C3` | #ColorRole_Accent | — |
| 61(ロクイチ) 61(ロイ) | `#F9BBC1` | #ColorRole_Sub | — |
| 62(ロジ) | `#F9BCC1` | #ColorRole_Primary | — |
| 62(ロジ) | `#F4ABB4` | #ColorRole_Secondary | — |
| 62(ロジ) | `#FFE2E9` | #ColorRole_Sub | — |
| 63(ムツミ) | `#FFA79B` | #ColorRole_Secondary | — |
| 64(ムトシ) | `#F26383` | #ColorRole_Accent | — |
| 64(ムトシ) | `#E55951` | #ColorRole_Sub | — |
| 65(ロクゴ) | `#F4ABB4` | #ColorRole_Secondary | — |
| 65(ロクゴ) | `#ECEBE4` | #ColorRole_Sub | — |
| 66(ムロク) | `#6D7880` | #ColorRole_Primary | — |
| 66(ムロク) | `#F9BBC0` | #ColorRole_Sub | — |
| 66(ムロク) | `#CC8C8C` | #ColorRole_Sub | — |
| 67(ムナ) | `#FF76A2` | #ColorRole_Primary | — |
| 67(ムナ) | `#B494A2` | #ColorRole_Sub | — |
| 67(ムナ) | `#FE76A2` | #ColorRole_Primary | — |
| 67(ムナ) | `#B494A2` | #ColorRole_Sub | — |
| 68(ロクヤ) | `#614D4F` | #ColorRole_Accent | — |
| 68(ロクヤ) | `#B5AD9B` | #ColorRole_Sub | — |
| 68(ロクヤ) | `#5E5E41` | #ColorRole_Sub | — |
| 70(ナナト) | `#9995B0` | #ColorRole_Accent | — |
| 70(ナナト) | `#9FA7BE` | #ColorRole_Sub | — |
| 71(ナナヒ) | `#938FAD` | #ColorRole_Secondary | — |
| 72(ナフタ) | `#A4A2C3` | #ColorRole_Secondary | — |
| 73(ナトミ) | `#FFD47A` | #ColorRole_Sub | — |
| 74(ナナヨ) | `#8B9BAC` | #ColorRole_Accent | — |
| 75(シチゴ) | `#F8FFB9` | #ColorRole_Secondary | — |
| 77(ナヅナ) | `#000101` | #ColorRole_Sub | — |
| 78(ナナハ) | `#FFE1EA` | #ColorRole_Secondary | — |
| 80(ヤソ) | `#FC6932` | #ColorRole_Sub | — |
| 81(ヤイチ) | `#010000` | #ColorRole_Sub | — |
| 84(ヤツヨ) | `#9EA388` | #ColorRole_Primary | — |
| 85(ハッコ) 85(パコ) | `#EF9D46` | #ColorRole_Primary | — |
| 85(ハッコ) 85(パコ) | `#C48455` | #ColorRole_Sub | — |
| 86(ハチロ) | `#614D4F` | #ColorRole_Accent | — |
| 86(ハチロ) | `#5E5E41` | #ColorRole_Sub | — |
| 88(ヤソハチ) | `#FFBFA7` | #ColorRole_Accent | — |
| 88(ヤソハチ) | `#F9642D` | #ColorRole_Sub | — |
| 92(コトジ) | `#B2AFCF` | #ColorRole_Secondary | — |
| 93(クミ) | `#FFD07D` | #ColorRole_Primary | — |
| 93(クミ) | `#9A6A4E` | #ColorRole_Accent | — |
| 93(クミ) | `#C1A072` | #ColorRole_Sub | — |
| 93(クミ) | `#F7FFD3` | #ColorRole_Sub | — |
| 93(クミ) | `#FFD486` | #ColorRole_Sub | — |
| 93(クミ) | `#FFD995` | #ColorRole_Sub | — |
| 96(クルリ) | `#F26383` | #ColorRole_Secondary | — |
| 99(ツクモ) | `#4F506F` | #ColorRole_Secondary | — |
| 99(ツクモ) | `#6D7881` | #ColorRole_Sub | — |
| 99(ツクモ) | `#727D85` | #ColorRole_Sub | — |
| バイナ 2(ツギ) | `#FFDCAE` | #ColorRole_Sub | — |
| ディケ 10(ツナイ) | `#5F676F` | #ColorRole_Primary | — |
| ディケ 10(ツナイ) | `#293B3A` | #ColorRole_Accent | — |
| ディケ 10(ツナイ) | `#F3D8DB` | #ColorRole_Sub | — |
| 000(チトセ) | `#85929C` | #ColorRole_Secondary | — |
| 零 零 | `#FFD184` | #ColorRole_Accent | — |
| 零 零 | `#ECAC42` | #ColorRole_Sub | — |
| 零 零 | `#CEC7B6` | #ColorRole_Sub | — |
| 零 零 | `#FFB0AA` | #ColorRole_Sub | — |
| 零 百 | `#A1A198` | #ColorRole_Accent | — |
| 零 百 | `#CDC7B7` | #ColorRole_Sub | — |
| 111(アイズ) | `#FFAC8F` | #ColorRole_Secondary | — |
| 111(アイズ) | `#CDCCC6` | #ColorRole_Sub | — |
| 111(アイズ) | `#FCBD47` | #ColorRole_Sub | — |
| 111(アイズ) | `#FFD58F` | #ColorRole_Sub | — |
| 222(ペルゲン) | `#FFC4B8` | #ColorRole_Secondary | — |
| 222(ペルゲン) | `#EAE5D6` | #ColorRole_Accent | — |
| 222(ペルゲン) | `#FFF4E6` | #ColorRole_Sub | — |
| 222(ペルゲン) | `#FFE1C7` | #ColorRole_Sub | — |
| 222(ペルゲン) | `#F3F1EA` | #ColorRole_Sub | — |
| 222(ペルゲン) | `#E8E9E3` | #ColorRole_Sub | — |
| 222(ドッペル) | `#FFD07D` | #ColorRole_Primary | — |
| 222(ドッペル) | `#EAE5D6` | #ColorRole_Secondary | — |
| 222(ドッペル) | `#FFE2C7` | #ColorRole_Accent | — |
| 222(ドッペル) | `#FFF4E4` | #ColorRole_Sub | — |
| 222(ドッペル) | `#F7F5EA` | #ColorRole_Sub | — |
| 222(ドッペル) | `#E8E9E3` | #ColorRole_Sub | — |
| 444(シテン) | `#FFD47A` | #ColorRole_Primary | — |
| 444(シテン) | `#ECAC43` | #ColorRole_Accent | — |
| 444(シテン) | `#C1A072` | #ColorRole_Sub | — |
| 444(シテン) | `#C9CDCB` | #ColorRole_Sub | — |
| 444(シテン) | `#020202` | #ColorRole_Sub | — |
| 777(ヨロコビ) | `#C1A072` | #ColorRole_Primary | — |
| 777(ヨロコビ) | `#FFA634` | #ColorRole_Accent | — |
| 777(ヨロコビ) | `#8B9BAC` | #ColorRole_Sub | — |
| 777(ヨロコビ) | `#FFD47A` | #ColorRole_Sub | — |
| 777(ヨロコビ) | `#D0B897` | #ColorRole_Sub | — |
| 777(ヨロコビ) | `#C1A072` | #ColorRole_Primary | — |
| 777(ヨロコビ) | `#FFA634` | #ColorRole_Accent | — |
| 777(ヨロコビ) | `#8B9BAC` | #ColorRole_Sub | — |
| 777(ヨロコビ) | `#FFD47A` | #ColorRole_Sub | — |
| トレッド 3×11(トリィレブン) | `#FFB1AB` | #ColorRole_Accent | — |
| 量産型 111(アイズ) | `#FFAC8F` | #ColorRole_Secondary | — |
| 量産型 111(アイズ) | `#CDCBC5` | #ColorRole_Accent | — |
| 量産型 111(アイズ) | `#FCBD47` | #ColorRole_Sub | — |
| 量産型 111(アイズ) | `#FFD58F` | #ColorRole_Sub | — |
| 量産型 444(シテン) | `#FFD47A` | #ColorRole_Primary | — |
| 量産型 444(シテン) | `#C1A072` | #ColorRole_Sub | — |
| 量産型 444(シテン) | `#020202` | #ColorRole_Sub | — |
| 量産型 666(リリス) | `#E0B0BC` | #ColorRole_Primary | — |
| 量産型 777(ヨロコビ) | `#C1A072` | #ColorRole_Primary | — |
| 量産型 777(ヨロコビ) | `#ECAC42` | #ColorRole_Accent | — |
| 量産型 777(ヨロコビ) | `#8B9BAC` | #ColorRole_Sub | — |
| 量産型 777(ヨロコビ) | `#FFD47A` | #ColorRole_Sub | — |
| 量産型 777(ヨロコビ) | `#C1A072` | #ColorRole_Primary | — |
| 量産型 777(ヨロコビ) | `#ECAC42` | #ColorRole_Accent | — |
| 量産型 777(ヨロコビ) | `#8B9BAC` | #ColorRole_Sub | — |
| 量産型 777(ヨロコビ) | `#FFD47A` | #ColorRole_Sub | — |

---

*色語の抽出は AI による判定です。DB や色語表へ反映する前に確認してください。*
*個別キャラの部位候補（画像からの提案）は `--num <N> --check coverage` で出せます。*

自動生成: `python -m src.tools.verify_appearance_detail --all --check coverage` (100BeautiesLab_GeneratorsAI)
