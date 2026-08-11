# AppearanceDetail エントリ別 HEX 対応 — Works_NumberTales

色語（13 語）だけでは `yellow blazer` と `yellow boots` が同じ語になり、
`ColorPalette` のどの HEX がどのエントリの色なのか一意に決まらない。
そこで **各エントリに実際に塗られている HEX** を画像から特定した。

候補は「`ColorPalette` の登録色」＋「透過イラストからの実測色」の和集合で、
`gpt-4o` には候補から**選ばせている**（HEX を生成させると当てにならないため）。
候補に無い HEX を返した場合は捨てている。

- 判定日: 2026-08-11
- 対応づけできたエントリ: **712 件**
- うち登録済みの色: 667 件 / **未登録の実測色: 45 件**

## 1. 登録済み `ColorPalette` との対応

`AppliesTo` へそのエントリの `BodyPart` を足せば、その色の使用部位が埋まる。

| キャラ | # | 記述 | 部位 | HEX | Role |
|---|---|---|---|---|---|
| 1(ハジメ) | 2 | the front shoulder area near t… | 肩 | `#ED5D47` | Primary |
| 1(ハジメ) | 3 | red orange hair / short hair | 髪 | `#ED5D47` | Primary |
| 1(ハジメ) | 4 | #EarShapeType_Fox | 耳 | `#FFAC8F` | Secondary |
| 1(ハジメ) | 6 | arrow-shaped chest zipper | 胸 | `#ED5D47` | Primary |
| 1(ハジメ) | 7 | light pink hooded top | 首/頭 | `#FF8682` | Primary |
| 1(ハジメ) | 8 | light pink hooded top | 首/肩/胸 | `#FF8682` | Primary |
| 1(ハジメ) | 10 | shorts | 脚 | `#CEC7B6` | Sub |
| 1(ハジメ) | 11 | gray short boots | 足 | `#C9CDCB` | Accent |
| 2(ツグ) | 1 | the white area on the front-le… | 胸 | `#E9E9E9` | Secondary |
| 2(ツグ) | 2 | the left chest of the top / or… | 胸 | `#FFA579` | Accent |
| 2(ツグ) | 3 | orange hair / short hair | 髪 | `#FFA073` | Primary |
| 2(ツグ) | 5 | rectangular glasses | 目・瞳 | `#E9E9E9` | Secondary |
| 2(ツグ) | 7 | double-knotted scarf | 首 | `#FFA579` | Accent |
| 2(ツグ) | 8 | light orange sporty shirt | 胸 | `#FFCFAE` | Sub |
| 2(ツグ) | 9 | orange business skirt / skirt | 脚 | `#FFBD97` | Sub |
| 3(ナオ) | 3 | yellow hair / spiky hair / yel… | 髪 | `#F8EC72` | Primary |
| 3(ナオ) | 5 | dark yellow eyes | 目・瞳 | `#FFBC08` | Sub |
| 3(ナオ) | 6 | bright yellow cape-jacket | 胸 | `#FFEE60` | Accent |
| 3(ナオ) | 7 | yellow short pants | 脚 | `#FFBC08` | Sub |
| 4(モチ) | 4 | cyan blue eyes | 目・瞳 | `#00B7D9` | Primary |
| 4(モチ) | 6 | teal cape | 肩/首 | `#0097C9` | Secondary |
| 4(モチ) | 7 | long blue hair / small ear-sid… | 髪 | `#00B7D9` | Primary |
| 4(モチ) | 8 | layered teal coat | 胸 | `#67BDBD` | Accent |
| 4(モチ) | 9 | skirt | 脚 | `#67BDBD` | Accent |
| 5(イズ) | 4 | teal green hair with multicolo… | 髪 | `#61DAAC` | Primary |
| 5(イズ) | 5 | teal green hair with multicolo… | 髪 | `#61DAAC` | Primary |
| 5(イズ) | 6 | dark green eyes (heterochromia… | 目・瞳 | `#61DAAC` | Primary |
| 5(イズ) | 7 | dark green eyes with a hint of… | 目・瞳 | `#61DAAC` | Primary |
| 5(イズ) | 13 | green casual clothing | 胸/腰/脚 | `#61DAAC` | Primary |
| 5(イズ) | 14 | light blue short skirt / teal … | 脚 | `#4CD9E8` | Primary |
| 6(ムイ) | 3 | pink hair | 髪 | `#FF76A2` | Primary |
| 6(ムイ) | 6 | hexagonal brooch | 首 | `#185EBD` | Accent |
| 6(ムイ) | 7 | lace trim | 首 | `#FFCEED` | Secondary |
| 6(ムイ) | 8 | Victorian dress | 胸/腰/脚 | `#A783B5` | Primary |
| 7(ナナ) | 4 | navy dark blue hair | 髪 | `#4447A4` | Sub |
| 7(ナナ) | 5 | dark grayish blue eyes | 目・瞳 | `#515271` | Sub |
| 7(ナナ) | 7 | prayer beads necklace | 首 | `#457AC4` | Secondary |
| 7(ナナ) | 10 | wide-leg dark pants | 脚 | `#5E7AA9` | Primary |
| 8(ワカツ) | 2 | the left chest of the mechanic… | 胸 | `#BC4655` | Sub |
| 8(ワカツ) | 5 | orange red hair | 髪 | `#FFA9A8` | Secondary |
| 8(ワカツ) | 6 | VR goggles(red and orange fram… | 頭 | `#FF9E68` | Primary |
| 8(ワカツ) | 9 | tactical vest | 胸 | `#BC4655` | Sub |
| 8(ワカツ) | 10 | tool pouches | 腰 | `#FF9E68` | Primary |
| 9(チカ) | 8 | large dark cape | 肩/首 | `#5F676F` | Accent |
| 10(ミツル) | 1 | the white area on the front-le… | 胸 | `#E85764` | Primary |
| 10(ミツル) | 4 | deep red hair | 髪 | `#E85764` | Primary |
| 10(ミツル) | 5 | red-black eyes (normal state) | 目・瞳 | `#81494A` | Secondary |
| 10(ミツル) | 6 | white eyes (when hitting the c… | 目・瞳 | `#F3DCDF` | Accent |
| 10(ミツル) | 8 | Chinese-style mandarin-collar … | 胸 | `#E85764` | Primary |
| 10(ミツル) | 9 | wide-leg pants | 脚 | `#F3DCDF` | Accent |
| 11(トウイチ) | 1 | one digit on each hem of the c… | 腰 | `#BB3E45` | Accent |
| 11(トウイチ) | 3 | two arrow-shaped hair pins | 髪 | `#BB3E45` | Accent |
| 11(トウイチ) | 6 | long hooded coat | 胸 | `#8B9BAC` | Secondary |
| 11(トウイチ) | 7 | silver gray long hair | 髪 | `#C2CCD0` | Sub |
| 12(トウジ) | 2 | peach orange hair | 髪 | `#FFAC8F` | Primary |
| 12(トウジ) | 3 | bangs covering the left eye | 髪 | `#FFAC8F` | Primary |
| 12(トウジ) | 5 | poncho cape / large cloak | 肩/首/背中 | `#FFEFE4` | Sub |
| 12(トウジ) | 6 | long peach orange hair | 髪 | `#FFAC8F` | Primary |
| 12(トウジ) | 8 | casual private outfit | 胸/腰/脚 | `#FFD7C2` | Secondary |
| 13(トミ) | 2 | on the left chest of the top /… | 胸 | `#5C9ABC` | Sub |
| 13(トミ) | 4 | teal light blue hair | 髪 | `#99D0D7` | Primary |
| 13(トミ) | 6 | sporty jersey | — | `#5C9ABC` | Sub |
| 13(トミ) | 8 | yellow shorts | 脚 | `#FFF13A` | Sub |
| 14(トヨ) | 5 | salmon-pink collar | 首 | `#FFC5BC` | Secondary |
| 14(トヨ) | 6 | long blue hair | 髪 | `#9BC1E6` | Primary |
| 14(トヨ) | 7 | light blue eyelashes with red … | 目・瞳 | `#9BC1E6` | Primary |
| 14(トヨ) | 9 | teal blazer(sometimes worn cas… | 胸 | `#00939F` | Sub |
| 14(トヨ) | 10 | salmon-pink inner shirt | 胸 | `#FFC5BC` | Secondary |
| 14(トヨ) | 11 | red skirt | 脚 | `#E75E5A` | Sub |
| 15(トウゴ) | 1 | on the front left chest of the… | 胸 | `#589D74` | Secondary |
| 15(トウゴ) | 4 | pink hair | 髪 | `#FFC4A6` | Accent |
| 15(トウゴ) | 7 | harness equipped with safety d… | 背中 | `#589D74` | Secondary |
| 15(トウゴ) | 8 | casual private outfit | 胸/腰/脚 | `#E8EDBE` | Sub |
| 15(トウゴ) | 9 | pale-colored jacket | 胸 | `#FFD7C9` | Sub |
| 16(ソロク) | 1 | around the brim of the hat, on… | 頭 | `#6A88C2` | Secondary |
| 16(ソロク) | 3 | very long magenta ponytail / w… | 髪 | `#F26383` | Primary |
| 16(ソロク) | 4 | blue cap | 頭 | `#6A88C2` | Secondary |
| 16(ソロク) | 7 | heart and key motif | 胸 | `#F26383` | Primary |
| 16(ソロク) | 9 | voluminous feminine silhouette | — | `#F26383` | Primary |
| 17(トナ) | 2 | short blue indigo hair / squar… | 髪 | `#9DB0DB` | Primary |
| 17(トナ) | 4 | short blue indigo bob | 髪 | `#9DB0DB` | Primary |
| 17(トナ) | 6 | purple gray shirt | 胸 | `#938FAD` | Sub |
| 17(トナ) | 7 | red pants | 脚 | `#F76D67` | Accent |
| 18(トウヤ) | 1 | the white area on the front le… | 胸 | `#F9642D` | Sub |
| 18(トウヤ) | 4 | short brown dark red hair / li… | 髪 | `#7C4540` | Primary |
| 18(トウヤ) | 5 | horizontal line pattern on che… | フェイスメイク | `#ED5D47` | Secondary |
| 18(トウヤ) | 6 | blazer over shirt | 胸 | `#D46E87` | Accent |
| 18(トウヤ) | 7 | skirt | 脚 | `#F9642D` | Sub |
| 19(トク) | 1 | the white area on the front le… | 胸 | `#BB3E45` | Sub |
| 19(トク) | 4 | short brown red hair / messy h… | 髪 | `#D07C95` | Primary |
| 19(トク) | 5 | half-lidded dark red eyes | 目・瞳 | `#BB3E45` | Sub |
| 19(トク) | 6 | sleeveless black top | 胸 | `#423F3F` | Sub |
| 19(トク) | 7 | wide-leg dark red pants | 脚 | `#BB3E45` | Sub |
| 20(ハツカ) | 1 | the buckle part of the choker … | 首 | `#CBCECD` | Sub |
| 20(ハツカ) | 2 | the buckle part of the belt on… | 腰 | `#CBCECD` | Sub |
| 20(ハツカ) | 4 | choker with a number | 首 | `#CBCECD` | Sub |
| 20(ハツカ) | 5 | silver white long hair / heart… | 髪 | `#E9EBE5` | Sub |
| 20(ハツカ) | 9 | orange inner wear | 胸 | `#FFA457` | Primary |
| 20(ハツカ) | 10 | belt with a number | — | `#CBCECD` | Sub |
| 21(ハツヒ) | 4 | orange hair | 髪 | `#FFAC8F` | Primary |
| 21(ハツヒ) | 5 | pale orange eyes | 目・瞳 | `#FFD7C2` | Accent |
| 21(ハツヒ) | 6 | energetic smile | — | `#FFAC8F` | Primary |
| 21(ハツヒ) | 7 | oversized warm orange coat | 胸 | `#FFAC8F` | Primary |
| 23(ツグミ) | 4 | mint green hair | 髪 | `#C2F2DE` | Secondary |
| 23(ツグミ) | 6 | yellow horizontal line makeup … | フェイスメイク | `#FFF007` | Sub |
| 23(ツグミ) | 7 | green hooded top | 胸 | `#B1DDA6` | Accent |
| 24(フトシ) | 3 | long pink hair / heart-shaped … | 髪 | `#E8AFD8` | Primary |
| 24(フトシ) | 4 | purple eyes | 目・瞳 | `#C680AF` | Sub |
| 24(フトシ) | 6 | pink-mauve skirt with accent c… | 脚 | `#C680AF` | Sub |
| 25(フィズ) | 3 | #EarShapeType_Fox | 耳 | `#D3DBDC` | Sub |
| 25(フィズ) | 4 | steel blue short hair / light … | 髪 | `#688B8A` | Sub |
| 25(フィズ) | 5 | navy eyelashes with teal eyes | 目・瞳 | `#175D7E` | Secondary |
| 25(フィズ) | 10 | dark blue gloves | 手 | `#175D7E` | Secondary |
| 25(フィズ) | 11 | deep green scarf with a charm … | 首 | `#688B8A` | Sub |
| 26(ニロク) | 2 | small area from the center of … | 胸 | `#FFE1EA` | Sub |
| 26(ニロク) | 4 | long pink hair / white accent … | 髪 | `#F4ABB4` | Secondary |
| 26(ニロク) | 6 | pink sleeveless turtleneck | 胸 | `#FFA79B` | Sub |
| 27(ツギナ) | 1 | As a purple name tag on the wh… | 胸 | `#736E9A` | Accent |
| 27(ツギナ) | 3 | number '27' marking on purple … | 胸 | `#736E9A` | Accent |
| 27(ツギナ) | 4 | short blue hair / side ponytai… | 髪 | `#9BC1E6` | Secondary |
| 27(ツギナ) | 5 | erected fox ears | — | `#E2EBEF` | Primary |
| 27(ツギナ) | 7 | white blouse | 胸 | `#EFEFEE` | Sub |
| 27(ツギナ) | 8 | purple pleated skirt | 脚 | `#736E9A` | Accent |
| 27(ツギナ) | 9 | four white buttons | — | `#EFEFEE` | Sub |
| 27(ツギナ) | 10 | blue lace-up ankle boots | 足 | `#736E9A` | Accent |
| 28(ニハチ) | 1 | The somewhat small white area … | 胸 | `#FF9E68` | Accent |
| 28(ニハチ) | 4 | Slightly large on the chest of… | 胸 | `#FF9E68` | Accent |
| 28(ニハチ) | 5 | Earring shape (from one side, … | 耳 | `#F4F1E5` | Secondary |
| 28(ニハチ) | 6 | Somewhat large as body paint o… | 肩 | `#DB653F` | Primary |
| 28(ニハチ) | 7 | Somewhat large as body paint o… | 肩 | `#DB653F` | Primary |
| 28(ニハチ) | 8 | #EarShapeType_Fox | 耳 | `#FF9E68` | Accent |
| 28(ニハチ) | 9 | wavy orange hair | 髪 | `#FF9E68` | Accent |
| 28(ニハチ) | 10 | dangling earrings | 耳 | `#DB653F` | Primary |
| 28(ニハチ) | 11 | mathematical body tattoo | — | `#DB653F` | Primary |
| 28(ニハチ) | 13 | orange ribbon bow at waist | 腰 | `#FF9E68` | Accent |
| 28(ニハチ) | 14 | red blazer (2 outfit variants) | 胸 | `#DB653F` | Primary |
| 29(ニトク) | 1 | #EarShapeType_Fox | 耳 | `#9DB0DB` | Secondary |
| 29(ニトク) | 2 | blue-lavender intake long hair | 髪 | `#9DB0DB` | Secondary |
| 29(ニトク) | 4 | lavender cape | 肩/首 | `#B2B0CE` | Accent |
| 29(ニトク) | 5 | light brown long skirt with wh… | 脚 | `#CEC7B6` | Sub |
| 29(ニトク) | 6 | purple bow ribbon at neck | 首 | `#B2B0CE` | Accent |
| 31(ミツイ) | 6 | short blue-cyan hair | 髪 | `#5C9ABC` | Accent |
| 31(ミツイ) | 8 | red-frame goggles with yellow … | 目・瞳 | `#F56D67` | Secondary |
| 31(ミツイ) | 9 | athletic outfit | 胸/腰/脚 | `#5C9ABC` | Accent |
| 31(ミツイ) | 10 | yellow shorts | 脚 | `#FFF13A` | Sub |
| 31(ミツイ) | 11 | thigh-high socks with boots | 脚/足 | `#5C9ABC` | Accent |
| 31(ミツイ) | 12 | yellow bracelet on the left wr… | 手 | `#FFF13A` | Sub |
| 32(ミツギ) | 1 | the right side of the light gr… | 腰 | `#7BDEC1` | Accent |
| 32(ミツギ) | 2 | the right side of the area wit… | 胸 | `#7BDEC1` | Accent |
| 32(ミツギ) | 3 | short mint green hair | 髪 | `#C2F2DE` | Primary |
| 32(ミツギ) | 6 | yellow horizontal line makeup … | フェイスメイク | `#FFF000` | Sub |
| 32(ミツギ) | 7 | number marking and stripe patt… | — | `#FAFE9D` | Sub |
| 32(ミツギ) | 8 | casual open-collar jacket | 胸 | `#B2DDA7` | Secondary |
| 32(ミツギ) | 9 | yellow diagonal stripe accent | フェイスメイク | `#FFF000` | Sub |
| 32(ミツギ) | 10 | wide-leg yellow pants | 脚 | `#FFF000` | Sub |
| 33(ミサ) | 2 | On the back of each glove / da… | 手 | `#FF8FAD` | Sub |
| 33(ミサ) | 4 | pink layered dress-like cape | 肩/首 | `#FFA79B` | Primary |
| 33(ミサ) | 5 | long orange-pink braided hair | 髪 | `#FFD5BD` | Secondary |
| 33(ミサ) | 6 | large pink bow ribbon | 髪 | `#FFA79B` | Primary |
| 33(ミサ) | 9 | ear-covering maid cap | 頭 | `#FFA79B` | Primary |
| 33(ミサ) | 10 | pink layered dress | 胸/腰/脚 | `#FFA79B` | Primary |
| 33(ミサ) | 11 | white ruffle collar | 首 | `#FFF7F3` | Sub |
| 33(ミサ) | 12 | white gloves with numbers | 手 | `#FFF7F3` | Sub |
| 34(サトシ) サンジ | 1 | Slightly large on the white ar… | 胸 | `#405AB9` | Secondary |
| 34(サトシ) サンジ | 2 | Slightly large on the chest ar… | 胸 | `#405AB9` | Secondary |
| 34(サトシ) サンジ | 4 | short dark navy blue hair | 髪 | `#387EB6` | Primary |
| 34(サトシ) サンジ | 7 | slit eyes / dark navy gray eye… | 目・瞳 | `#405AB9` | Secondary |
| 34(サトシ) サンジ | 8 | blue shorts | 脚 | `#387EB6` | Primary |
| 34(サトシ) サンジ | 9 | yellow apron with numbers, res… | 胸/腰 | `#FFCE2B` | Sub |
| 35(サトコ) 35(ミコ) | 1 | Small on the left collar, near… | 胸 | `#FFA457` | Secondary |
| 35(サトコ) 35(ミコ) | 2 | medium yellow-tan hair | 髪 | `#FFA457` | Secondary |
| 35(サトコ) 35(ミコ) | 4 | medium yellow-tan hair | 髪 | `#FFA457` | Secondary |
| 35(サトコ) 35(ミコ) | 5 | yellow-green eyes | 目・瞳 | `#C8D253` | Accent |
| 35(サトコ) 35(ミコ) | 6 | roundly shaved yellow-tan eyeb… | フェイスメイク | `#FFA457` | Secondary |
| 35(サトコ) 35(ミコ) | 8 | orange sleeveless vest (usual) | 胸 | `#E98D30` | Primary |
| 35(サトコ) 35(ミコ) | 9 | necktie (usual) | 首 | `#E98D30` | Primary |
| 36(ミトム) | 4 | orange short-medium hair | 髪 | `#FFD58F` | Primary |
| 36(ミトム) | 7 | orange bolero jacket | 胸 | `#FFD58F` | Primary |
| 36(ミトム) | 8 | purple-pink button-front skirt | 脚 | `#A95C8D` | Sub |
| 36(ミトム) | 10 | bow ribbon at chest | 胸 | `#FFA79B` | Secondary |
| 37(サナ) | 1 | the shape of the tie pin / red… | 首 | `#FF8682` | Accent |
| 37(サナ) | 3 | short salmon-pink hair | 髪 | `#FFA79B` | Primary |
| 37(サナ) | 4 | red eyelashes with red and yel… | 目・瞳 | `#E75E5A` | Sub |
| 37(サナ) | 7 | red blazer with blue trim | 胸 | `#E75E5A` | Sub |
| 37(サナ) | 10 | yellow necktie and pin with '3… | 首 | `#FFD47A` | Sub |
| 39(サク) | 1 | Slightly large, centered on th… | 胸 | `#9A6A4E` | Secondary |
| 39(サク) | 6 | short amber-blonde hair | 髪 | `#FFD07D` | Sub |
| 39(サク) | 8 | long dark brown trench coat | 胸 | `#9A6A4E` | Secondary |
| 39(サク) | 9 | belt supporter with number des… | 腰 | `#C1A072` | Primary |
| 39(サク) | 10 | wide relaxed pants | 脚 | `#FFF4DF` | Accent |
| 40(ヨソ) | 1 | Geometric pattern resembling A… | 腰 | `#387EB6` | Accent |
| 40(ヨソ) | 4 | teal side-braid hair | 髪 | `#67BDBD` | Primary |
| 40(ヨソ) | 6 | long flowing teal-blue Chinese… | 胸/腰/脚 | `#387EB6` | Accent |
| 40(ヨソ) | 7 | teal lace-up tall boots | 足 | `#387EB6` | Accent |
| 40(ヨソ) | 9 | pattern inspired by '40' | — | `#387EB6` | Accent |
| 41(ヨソイチ) | 1 | on the front center of the whi… | 胸 | `#000101` | Sub |
| 41(ヨソイチ) | 5 | salmon-pink collar | 首 | `#FFC5BC` | Secondary |
| 41(ヨソイチ) | 7 | open teal blazer | 胸 | `#00939F` | Sub |
| 41(ヨソイチ) | 8 | salmon-pink button-up shirt | 胸 | `#FFC5BC` | Secondary |
| 41(ヨソイチ) | 10 | white knee-high socks / cyan s… | 足 | `#4CD9E8` | Sub |
| 42(ヨツグ) | 4 | heart-shaped light accent colo… | 髪 | `#FCE8EC` | Accent |
| 42(ヨツグ) | 5 | blue eyes | 目・瞳 | `#0097C9` | Sub |
| 42(ヨツグ) | 6 | blue eyes | 目・瞳 | `#0097C9` | Sub |
| 42(ヨツグ) | 7 | pink puff-sleeve blouse with w… | 首 | `#E8AFD8` | Primary |
| 42(ヨツグ) | 8 | light pink long blazer | 胸 | `#E8AFD8` | Primary |
| 42(ヨツグ) | 9 | blue-gray shorts | 脚 | `#AEB8DB` | Secondary |
| 42(ヨツグ) | 10 | white socks / pink shoes | 足 | `#FCE8EC` | Accent |
| 43(シトミ) | 1 | on the front center of the whi… | 胸 | `#000001` | Sub |
| 43(シトミ) | 2 | on the dark navy area in the c… | 胸 | `#000001` | Sub |
| 43(シトミ) | 4 | short dark navy hair | 髪 | `#387EB6` | Primary |
| 43(シトミ) | 6 | dark navy polo shirt with numb… | 胸 | `#387EB6` | Primary |
| 43(シトミ) | 7 | gray shorts | 脚 | `#A2AFB8` | Accent |
| 43(シトミ) | 8 | dark navy thigh-high socks | 脚/足 | `#387EB6` | Primary |
| 43(シトミ) | 9 | dark navy boots | 足 | `#387EB6` | Primary |
| 44(シトシ) | 1 | on the front left chest of the… | 胸 | `#B3AD70` | Sub |
| 44(シトシ) | 4 | golden-tan small twin tails / … | 髪 | `#EEC694` | Accent |
| 44(シトシ) | 5 | steel-blue eyes | 目・瞳 | `#7EAEAB` | Sub |
| 44(シトシ) | 6 | light teal vest with four whit… | 胸 | `#A4DAEF` | Sub |
| 44(シトシ) | 7 | orange shorts | 脚 | `#FFA457` | Sub |
| 44(シトシ) | 8 | brown gloves with a '4' motif … | 手 | `#B3AD70` | Sub |
| 44(シトシ) | 9 | light yellow leg warmers / ora… | 足 | `#B1AA6B` | Primary |
| 45(シゴ) | 1 | on the dark navy area from the… | 腰 | `#C8CECD` | Accent |
| 45(シゴ) | 2 | on the dark navy area of the l… | 腰 | `#C8CECD` | Accent |
| 45(シゴ) | 4 | short black ponytail | 髪 | `#010102` | Sub |
| 45(シゴ) | 5 | teal eyes | 目・瞳 | `#4A6B6A` | Sub |
| 45(シゴ) | 6 | dark indigo-purple tunic dress | 胸/腰/脚 | `#6B658C` | Secondary |
| 45(シゴ) | 7 | teal pants | 脚 | `#4A6B6A` | Sub |
| 45(シゴ) | 8 | teal sandals | 足 | `#4A6B6A` | Sub |
| 46(シロー) | 5 | long blue hair braided into fo… | 髪 | `#387EB6` | Primary |
| 46(シロー) | 7 | red eyes | 目・瞳 | `#E55951` | Sub |
| 46(シロー) | 8 | blue jacket with red trim | 胸 | `#387EB6` | Primary |
| 46(シロー) | 9 | pink shirt | 胸 | `#F26383` | Sub |
| 46(シロー) | 11 | blue boots | 足 | `#387EB6` | Primary |
| 47(シナ) | 1 | on the gray body fur area from… | 胸 | `#185EBD` | Accent |
| 47(シナ) | 4 | long lavender-gray hair tied a… | 髪 | `#8B9BAC` | Sub |
| 47(シナ) | 5 | navy eyes | 目・瞳 | `#185EBD` | Accent |
| 47(シナ) | 6 | navy miko outfit with number | — | `#185EBD` | Accent |
| 47(シナ) | 7 | navy skirt | 脚 | `#185EBD` | Accent |
| 47(シナ) | 8 | white knee-high socks / navy g… | 足 | `#185EBD` | Accent |
| 48(シハチ) | 1 | on the front left chest of the… | 胸 | `#9EA388` | Primary |
| 48(シハチ) | 2 | on the left collar, near the n… | 首 | `#9EA388` | Primary |
| 48(シハチ) | 4 | short dark green hair | 髪 | `#9EA388` | Primary |
| 48(シハチ) | 5 | blue-green eyes / glasses with… | 目・瞳 | `#7EAEAB` | Secondary |
| 48(シハチ) | 6 | short dark green hair | 髪 | `#9EA388` | Primary |
| 48(シハチ) | 7 | blue-green eyes / glasses with… | 目・瞳 | `#7EAEAB` | Secondary |
| 48(シハチ) | 8 | blue uniform jacket | 胸/腰/脚 | `#7EAEAB` | Secondary |
| 48(シハチ) | 10 | yellow pants | 脚 | `#FFBC08` | Sub |
| 49(ヨチカ) | 1 | on the front left chest of the… | 胸 | `#4378C3` | Secondary |
| 49(ヨチカ) | 4 | medium dark indigo hair | 髪 | `#405AB9` | Sub |
| 49(ヨチカ) | 5 | dark blue eyes | 目・瞳 | `#405AB9` | Sub |
| 49(ヨチカ) | 8 | white-trimmed blue short-sleev… | 胸/腰/脚 | `#4378C3` | Secondary |
| 49(ヨチカ) | 9 | purple inner turtleneck | 胸 | `#BD8AE6` | Primary |
| 49(ヨチカ) | 10 | blue short pants | 脚 | `#4378C3` | Secondary |
| 50(ナカバ) | 4 | mint-colored hooded top wrappe… | 胸 | `#C2F2DE` | Accent |
| 50(ナカバ) | 6 | green hair in buns (slightly t… | 髪 | `#009489` | Sub |
| 50(ナカバ) | 7 | blue-green eyes | 目・瞳 | `#3DD4CF` | Primary |
| 50(ナカバ) | 8 | mint-colored hooded top wrappe… | 腰 | `#C2F2DE` | Accent |
| 51(イソイチ) | 2 | left collar, around the neck /… | 首 | `#FFD7C9` | Sub |
| 51(イソイチ) | 3 | #EarShapeType_Fox | 耳 | `#E85764` | Primary |
| 51(イソイチ) | 4 | pink short ponytail | 髪 | `#E85764` | Primary |
| 51(イソイチ) | 6 | original green casual wear wit… | — | `#589D74` | Sub |
| 52(イツギ) | 1 | the gray fur area on the left … | 胸 | `#A2AFB8` | Sub |
| 52(イツギ) | 2 | the teal area around the left … | 肩 | `#638887` | Primary |
| 52(イツギ) | 6 | dark teal bodysuit | 胸/腰/脚 | `#165C7D` | Secondary |
| 52(イツギ) | 7 | teal-blue sleeves and shorts | 脚 | `#7EAEAB` | Sub |
| 52(イツギ) | 8 | teal boots | 足 | `#638887` | Primary |
| 52(イツギ) | 9 | teal gloves | 手 | `#7EAEAB` | Sub |
| 52(イツギ) | 10 | gray inner layer | 胸 | `#A2AFB8` | Sub |
| 53(イツゾウ) | 1 | Small on the left collar, near… | 胸 | `#C7D54C` | Secondary |
| 53(イツゾウ) | 3 | short yellow-tan hair | 髪 | `#FFC675` | Primary |
| 53(イツゾウ) | 4 | amber eyes | 目・瞳 | `#E98D30` | Sub |
| 53(イツゾウ) | 5 | roundly shaved green eyebrows | フェイスメイク | `#C7D54C` | Secondary |
| 53(イツゾウ) | 7 | green necktie | 首 | `#C7D54C` | Secondary |
| 53(イツゾウ) | 8 | orange apron jumper | 胸/腰 | `#E98D30` | Sub |
| 53(イツゾウ) | 9 | orange shorts | 脚 | `#E98D30` | Sub |
| 55(イソゴ) | 1 | one digit on each green fur ar… | 胸 | `#71BC51` | Accent |
| 55(イソゴ) | 6 | medium dark green hair | 髪 | `#589D74` | Primary |
| 55(イソゴ) | 7 | green eyes | 目・瞳 | `#71BC51` | Accent |
| 55(イソゴ) | 8 | light green collared blouse | 首 | `#B1DDA6` | Secondary |
| 55(イソゴ) | 9 | red horizontal stripe accents … | 胸 | `#E85764` | Sub |
| 55(イソゴ) | 10 | dark green long sleeves | 腕 | `#589D74` | Primary |
| 56(イソロク) | 5 | green eyes | 目・瞳 | `#66D387` | Accent |
| 56(イソロク) | 6 | pink apron blouse | 胸/腰 | `#F9C9DE` | Secondary |
| 56(イソロク) | 7 | gray skirt | 脚 | `#CECCC6` | Primary |
| 56(イソロク) | 8 | light green scarf | 首 | `#66D387` | Accent |
| 56(イソロク) | 9 | white socks / pink shoes | 足 | `#ECEBE4` | Sub |
| 57(イズナ) | 1 | On the armband attached to the… | 腕 | `#E8F152` | Primary |
| 57(イズナ) | 4 | blonde ponytail | 髪 | `#FFEE62` | Secondary |
| 57(イズナ) | 6 | yellow blazer | 胸 | `#FFEE62` | Secondary |
| 57(イズナ) | 8 | yellow boots | 足 | `#FFEE62` | Secondary |
| 57(イズナ) | 9 | yellow sailor-collar uniform w… | 胸/首 | `#FFEE62` | Secondary |
| 57(イズナ) | 10 | blue inner shirt | 胸 | `#4B79BE` | Sub |
| 58(イソヤ) | 1 | On the light-blue part of the … | 肩 | `#00BACB` | Sub |
| 58(イソヤ) | 3 | long brown hair | 髪 | `#EF9D46` | Accent |
| 58(イソヤ) | 4 | light blue eyes | 目・瞳 | `#85E6EA` | Secondary |
| 58(イソヤ) | 5 | light blue long casual dress (… | 胸/腰/脚 | `#85E6EA` | Secondary |
| 58(イソヤ) | 6 | blue shoes | 足 | `#02A1C8` | Sub |
| 60(ムソウ) | 1 | On the tie (only for usual out… | 首 | `#FFE1EA` | Accent |
| 60(ムソウ) | 3 | pink intake hair | 髪/頭 | `#FFA79B` | Primary |
| 60(ムソウ) | 6 | pink necktie with brooch (usua… | 首 | `#FFA79B` | Primary |
| 60(ムソウ) | 7 | long pink hair (usual outfit) | 髪 | `#FFA79B` | Primary |
| 60(ムソウ) | 8 | pink/magenta tunic dress (usua… | 胸/腰/脚 | `#FFA79B` | Primary |
| 60(ムソウ) | 11 | pink necktie with brooch (usua… | 首 | `#FFA79B` | Primary |
| 60(ムソウ) | 12 | pink ponytail (otaku outfit) | 髪 | `#FFA79B` | Primary |
| 60(ムソウ) | 14 | pink headband (otaku outfit) | 頭 | `#FFA79B` | Primary |
| 60(ムソウ) | 15 | magenta short pants | 脚 | `#CD4479` | Secondary |
| 60(ムソウ) | 16 | magenta boots | 足 | `#CD4479` | Secondary |
| 61(ロクイチ) 61(ロイ) | 1 | On the right side of the hood,… | 頭 | `#6A88C2` | Secondary |
| 61(ロクイチ) 61(ロイ) | 2 | On the red parts of both shoul… | 肩 | `#DC576C` | Sub |
| 61(ロクイチ) 61(ロイ) | 4 | magenta very long ponytail | 髪 | `#F26383` | Primary |
| 61(ロクイチ) 61(ロイ) | 7 | light purple eyes | 目・瞳 | `#A4A2C3` | Accent |
| 61(ロクイチ) 61(ロイ) | 10 | white and navy hood with numbe… | 頭 | `#6A88C2` | Secondary |
| 61(ロクイチ) 61(ロイ) | 12 | blue bow tie (idol outfit) | 首 | `#6A88C2` | Secondary |
| 61(ロクイチ) 61(ロイ) | 14 | blue shoes | 足 | `#6A88C2` | Secondary |
| 62(ロジ) | 1 | Slightly large in the center o… | 腕 | `#F4ABB4` | Secondary |
| 62(ロジ) | 3 | long light pink hair | 髪 | `#F9BCC1` | Primary |
| 62(ロジ) | 4 | pink eyes | 目・瞳 | `#F4ABB4` | Secondary |
| 62(ロジ) | 6 | pink half-pants | 脚 | `#F9BCC1` | Primary |
| 62(ロジ) | 7 | light-colored boots | 足 | `#FFA79B` | Sub |
| 62(ロジ) | 8 | armband (with number on left s… | 肩/腕 | `#FFE2E9` | Sub |
| 63(ムツミ) | 4 | orange hair | 髪 | `#FFA634` | Sub |
| 63(ムツミ) | 5 | orange eyes | 目・瞳 | `#A95C8D` | Sub |
| 63(ムツミ) | 7 | orange bolero jacket | 胸 | `#FFA634` | Sub |
| 63(ムツミ) | 8 | pink bow tie | 首 | `#FFA79B` | Secondary |
| 63(ムツミ) | 9 | orange accents | — | `#FFA634` | Sub |
| 64(ムトシ) | 4 | long magenta hair tied at the … | 髪 | `#B8507C` | Primary |
| 64(ムトシ) | 5 | violet eyes | 目・瞳 | `#6AA6D7` | Secondary |
| 64(ムトシ) | 7 | rose-pink casual dress | 胸/腰/脚 | `#E55951` | Sub |
| 64(ムトシ) | 8 | blue shoes | 足 | `#387EB6` | Sub |
| 65(ロクゴ) | 3 | #EarShapeType_Fox | 耳 | `#CECCC5` | Primary |
| 65(ロクゴ) | 4 | short light gray two-tone hair | 髪 | `#ECEBE4` | Sub |
| 65(ロクゴ) | 6 | pastel green apron dress | 胸/腰/脚 | `#C1F3D6` | Sub |
| 65(ロクゴ) | 8 | pink shoes | 足 | `#F4ABB4` | Secondary |
| 66(ムロク) | 2 | On the collar, one digit on ea… | 胸 | `#6D7880` | Primary |
| 66(ムロク) | 4 | brown hair with pink highlight… | 髪 | `#CC8C8C` | Sub |
| 66(ムロク) | 6 | pink hooded cloak | 肩/首 | `#FF8FAD` | Sub |
| 66(ムロク) | 7 | orange-yellow yoke bib with nu… | 首 | `#FFA634` | Secondary |
| 66(ムロク) | 8 | black habit-style dress | 胸/腰/脚 | `#6D7880` | Primary |
| 66(ムロク) | 9 | pink puff sleeves | 肩/腕 | `#FF8FAD` | Sub |
| 66(ムロク) | 10 | dark gray fingerless gloves | 手 | `#6D7880` | Primary |
| 66(ムロク) | 11 | yellow trim accents | — | `#FFC046` | Accent |
| 67(ムナ) | 4 | navy blue medium-short hair | 髪 | `#5B77A8` | Accent |
| 67(ムナ) | 6 | pale reddish-purple trainer we… | — | `#B494A2` | Sub |
| 67(ムナ) | 7 | dark navy training pants | 脚 | `#9DB0DB` | Secondary |
| 67(ムナ) | 8 | cyan blue sneakers | 足 | `#0097C9` | Sub |
| 67(ムナ) | 4 | navy blue medium-short hair | 髪 | `#5B77A8` | Accent |
| 67(ムナ) | 5 | light blue eyes | 目・瞳 | `#AEBEE1` | Sub |
| 67(ムナ) | 6 | pale reddish-purple trainer we… | — | `#B494A2` | Sub |
| 67(ムナ) | 7 | dark navy training pants | 脚 | `#9DB0DB` | Secondary |
| 67(ムナ) | 8 | cyan blue sneakers | 足 | `#0097C9` | Sub |
| 68(ロクヤ) | 1 | on the right side of the banda… | 頭 | `#614D4F` | Accent |
| 68(ロクヤ) | 2 | on the right side of the banda… | 頭 | `#614D4F` | Accent |
| 68(ロクヤ) | 4 | red bandana with '68' marking | 頭 | `#F1617D` | Secondary |
| 68(ロクヤ) | 5 | short green hair | 髪 | `#6CBA4B` | Primary |
| 68(ロクヤ) | 6 | gray-green eyes | 目・瞳 | `#6CBA4B` | Primary |
| 68(ロクヤ) | 7 | red bandana with number markin… | 頭 | `#F1617D` | Secondary |
| 68(ロクヤ) | 8 | light brown apron (normal outf… | 胸/腰 | `#B5AD9B` | Sub |
| 68(ロクヤ) | 9 | dark green leggings | 脚 | `#6CBA4B` | Primary |
| 68(ロクヤ) | 10 | light brown workwear (work out… | — | `#B5AD9B` | Sub |
| 69(ロック) | 7 | short pink hair | 髪 | `#EC9EB4` | Accent |
| 69(ロック) | 8 | red eyes | 目・瞳 | `#F26383` | Secondary |
| 69(ロック) | 9 | burgundy double-breasted vest … | 胸/腰/脚 | `#B8507C` | Sub |
| 69(ロック) | 12 | pink shoes | 足 | `#EC9EB4` | Accent |
| 70(ナナト) | 1 | on the side left shoulder of t… | 肩 | `#504695` | Sub |
| 70(ナナト) | 2 | on the left hem of the dark bl… | 腰 | `#504695` | Sub |
| 70(ナナト) | 4 | purple hair | 髪 | `#6B658C` | Primary |
| 70(ナナト) | 5 | dark blue eyes | 目・瞳 | `#504695` | Sub |
| 70(ナナト) | 6 | priestly outfit resembling a h… | 脚 | `#5B77A8` | Sub |
| 70(ナナト) | 8 | light blue armwear with white … | 腕/手 | `#5B77A8` | Sub |
| 71(ナナヒ) | 3 | blue ponytail with number moti… | 髪 | `#5B77A8` | Primary |
| 71(ナナヒ) | 6 | gray-purple polo shirt with wh… | 首 | `#938FAD` | Secondary |
| 71(ナナヒ) | 7 | red shorts with white hem | 脚 | `#F76D67` | Sub |
| 71(ナナヒ) | 8 | blue knee-high socks | 足 | `#5B77A8` | Primary |
| 71(ナナヒ) | 9 | blue shoes | 足 | `#5B77A8` | Primary |
| 72(ナフタ) | 1 | on the front right chest to th… | 胸 | `#A4A2C3` | Secondary |
| 72(ナフタ) | 4 | very long pale blue hair | 髪 | `#9BC1E6` | Primary |
| 72(ナフタ) | 5 | lavender eyelashes with lavend… | 目・瞳 | `#A4A2C3` | Secondary |
| 72(ナフタ) | 6 | lavender camisole apron-style … | 胸/腰 | `#A4A2C3` | Secondary |
| 72(ナフタ) | 7 | pale blue long skirt | 脚 | `#9BC1E6` | Primary |
| 72(ナフタ) | 8 | dark purple lace-up boots | 足 | `#736F9A` | Accent |
| 72(ナフタ) | 9 | '研修' (trainee) name tag | — | `#E2EBEE` | Sub |
| 73(ナトミ) | 1 | the shape of the beret patch /… | 頭 | `#FFA79B` | Primary |
| 73(ナトミ) | 3 | short pink hair with cap | 髪/頭 | `#FFA79B` | Primary |
| 73(ナトミ) | 4 | red eyelashes with golden eyes | 目・瞳 | `#FFA79B` | Primary |
| 73(ナトミ) | 5 | yellow belt with blue and red … | 胸/腰/脚 | `#9DB0DB` | Secondary |
| 73(ナトミ) | 6 | blue necktie | 首 | `#9DB0DB` | Secondary |
| 73(ナトミ) | 8 | red short jacket over blue dre… | 胸/腰/脚 | `#FFA79B` | Primary |
| 73(ナトミ) | 9 | yellow waist belt | 腰 | `#FFD47A` | Sub |
| 73(ナトミ) | 10 | blue beret with '73' motif pat… | 頭 | `#9DB0DB` | Secondary |
| 73(ナトミ) | 11 | red shoes | 足 | `#FFA79B` | Primary |
| 74(ナナヨ) | 1 | On the translucent white area … | 肩 | `#387EB6` | Secondary |
| 74(ナナヨ) | 4 | long silver-gray hair | 髪 | `#8B9BAC` | Accent |
| 74(ナナヨ) | 5 | bright blue eyes | 目・瞳 | `#185EBD` | Sub |
| 74(ナナヨ) | 6 | blue off-shoulder wrap top | 胸/腰 | `#387EB6` | Secondary |
| 74(ナナヨ) | 7 | blue short skirt | 脚 | `#387EB6` | Secondary |
| 75(シチゴ) | 4 | yellow side-tail hair | 髪 | `#FFEE62` | Primary |
| 75(シチゴ) | 5 | yellow eyes | 目・瞳 | `#FFEE62` | Primary |
| 75(シチゴ) | 6 | yellow-green sailor uniform to… | 胸/腰/脚 | `#E8F152` | Accent |
| 75(シチゴ) | 7 | blue scarf | 首 | `#6F94C8` | Sub |
| 75(シチゴ) | 8 | blue long skirt | 脚 | `#6F94C8` | Sub |
| 75(シチゴ) | 10 | yellow shoes | 足 | `#FFEE62` | Primary |
| 75(シチゴ) | 11 | left shoulder armband | 肩/腕 | `#FFEE62` | Primary |
| 76(シチロク) | 1 | on the white area of the left … | 胸 | `#5B77A8` | Primary |
| 76(シチロク) | 5 | navy blue medium-length hair | 髪 | `#5B77A8` | Primary |
| 76(シチロク) | 6 | pink necktie scarf | 首 | `#FF76A2` | Accent |
| 76(シチロク) | 7 | pink headphones with round dar… | 目・瞳/頭 | `#FF76A2` | Accent |
| 76(シチロク) | 9 | teal blue sailor-style top | 胸 | `#0097C9` | Sub |
| 76(シチロク) | 10 | pink long skirt | 脚 | `#FF76A2` | Accent |
| 76(シチロク) | 12 | blue shoes | 足 | `#5B77A8` | Primary |
| 77(ナヅナ) | 1 | On the white area of the left … | 胸 | `#000101` | Sub |
| 77(ナヅナ) | 2 | On the navy blue area around t… | 胸 | `#00BFA4` | Accent |
| 77(ナヅナ) | 4 | short teal-blue hair with crys… | 髪 | `#175D7D` | Sub |
| 77(ナヅナ) | 5 | gray-blue eyes | 目・瞳 | `#01878D` | Secondary |
| 77(ナヅナ) | 6 | green crystal forehead marking | フェイスメイク | `#00BFA4` | Accent |
| 77(ナヅナ) | 7 | dark navy blue hakama-style ro… | 脚 | `#175D7D` | Sub |
| 77(ナヅナ) | 8 | blue-platform sandals | 足 | `#434F6F` | Sub |
| 78(ナナハ) | 1 | The heart pattern on the ears … | 耳 | `#FFE1EA` | Secondary |
| 78(ナナハ) | 4 | very long pink hair | 髪 | `#FF8FAD` | Primary |
| 78(ナナハ) | 5 | lavender eyes | 目・瞳 | `#746D9B` | Sub |
| 78(ナナハ) | 6 | purple short-sleeve top with o… | 胸 | `#746D9B` | Sub |
| 78(ナナハ) | 7 | orange skirt | 脚 | `#FF9E68` | Accent |
| 78(ナナハ) | 8 | blue beaded necklace with hear… | 首 | `#6A88C2` | Sub |
| 78(ナナハ) | 9 | blue gloves | 手 | `#6A88C2` | Sub |
| 78(ナナハ) | 10 | purple shoes | 足 | `#746D9B` | Sub |
| 80(ヤソ) | 1 | the white area on the front-le… | 胸 | `#FF9048` | Primary |
| 80(ヤソ) | 4 | dark orange wide-open eyes | 目・瞳 | `#EF9D46` | Sub |
| 80(ヤソ) | 5 | orange-red hair with light och… | 髪 | `#FF9048` | Primary |
| 80(ヤソ) | 10 | brown mechanic vest like an em… | 胸 | `#C48455` | Secondary |
| 80(ヤソ) | 11 | orange shorts that suggest wor… | 腰/脚 | `#EF9D46` | Sub |
| 81(ヤイチ) | 2 | left chest of the top / dark (… | 胸 | `#010000` | Sub |
| 81(ヤイチ) | 4 | short brown side-tail hair wit… | 髪 | `#7C4540` | Accent |
| 81(ヤイチ) | 5 | short brown side-tail hair wit… | 髪 | `#7C4540` | Accent |
| 81(ヤイチ) | 6 | orange-red eyes | 目・瞳 | `#EE6854` | Sub |
| 81(ヤイチ) | 7 | horizontal line pattern on the… | フェイスメイク | `#010000` | Sub |
| 81(ヤイチ) | 8 | pink sleeveless vest with numb… | 胸 | `#FDAB92` | Secondary |
| 81(ヤイチ) | 9 | pink short-sleeve inner top wi… | 胸 | `#FDAB92` | Secondary |
| 81(ヤイチ) | 10 | red-orange long pants | 脚 | `#ED5D47` | Sub |
| 81(ヤイチ) | 11 | pink shoes | 足 | `#FDAB92` | Secondary |
| 84(ヤツヨ) | 2 | the orange area around the lef… | 胸 | `#FFBC08` | Sub |
| 84(ヤツヨ) | 5 | short gray-green hair | 髪 | `#9EA388` | Primary |
| 84(ヤツヨ) | 6 | orange eyes | 目・瞳 | `#EF9D45` | Secondary |
| 84(ヤツヨ) | 7 | orange neckerchief | 首 | `#EF9D45` | Secondary |
| 84(ヤツヨ) | 8 | orange short jacket with brown… | 胸 | `#EF9D45` | Secondary |
| 84(ヤツヨ) | 9 | teal-gray inner blouse with fo… | 胸 | `#7EAEAB` | Sub |
| 84(ヤツヨ) | 11 | gray-green lace-up boots | 足 | `#9EA388` | Primary |
| 85(ハッコ) 85(パコ) | 1 | On the left shoulder cyan-blue… | 肩 | `#85E6EA` | Secondary |
| 85(ハッコ) 85(パコ) | 3 | brown ponytail | 髪 | `#C48455` | Sub |
| 85(ハッコ) 85(パコ) | 4 | cyan eyes | 目・瞳 | `#85E6EA` | Secondary |
| 85(ハッコ) 85(パコ) | 5 | cyan short pants | 脚 | `#01A1C8` | Sub |
| 85(ハッコ) 85(パコ) | 7 | cyan teardrop pendant necklace | 首 | `#00BACB` | Accent |
| 85(ハッコ) 85(パコ) | 8 | cyan blue off-shoulder necklin… | 首/肩 | `#85E6EA` | Secondary |
| 86(ハチロ) | 1 | on the top area of the bandana… | 頭 | `#614D4F` | Accent |
| 86(ハチロ) | 3 | #EarShapeType_Fox | 耳 | `#E1DBCC` | Sub |
| 86(ハチロ) | 4 | short green hair | 髪 | `#6CBA4B` | Primary |
| 86(ハチロ) | 5 | gray-brown eyes | 目・瞳 | `#5E5E41` | Sub |
| 86(ハチロ) | 6 | red bandana with number coveri… | 頭 | `#F1617D` | Secondary |
| 86(ハチロ) | 7 | cream-colored apron | 胸/腰 | `#E1DBCC` | Sub |
| 86(ハチロ) | 8 | dark brown one-piece | 胸/腰/脚 | `#614D4F` | Accent |
| 86(ハチロ) | 9 | dark green stockings | 脚 | `#6CBA4B` | Primary |
| 86(ハチロ) | 10 | dark brown shoes with pink ank… | 足 | `#614D4F` | Accent |
| 87(ヤシナ) 87(ハナ) | 1 | The heart pattern on the ears … | 耳 | `#FFE1EA` | Secondary |
| 87(ヤシナ) 87(ハナ) | 3 | diamond and heart-patterned ea… | 耳 | `#FFE1EA` | Secondary |
| 87(ヤシナ) 87(ハナ) | 4 | very long pink hair | 髪 | `#FF8FAD` | Sub |
| 87(ヤシナ) 87(ハナ) | 5 | amber eyes | 目・瞳 | `#FF9E68` | Accent |
| 87(ヤシナ) 87(ハナ) | 6 | orange short-sleeve sailor top… | 首 | `#FF9E68` | Accent |
| 87(ヤシナ) 87(ハナ) | 7 | blue knee-length skirt with di… | 脚 | `#6A88C2` | Sub |
| 87(ヤシナ) 87(ハナ) | 8 | heart-shaped diamond pendant n… | 首 | `#6A88C2` | Sub |
| 87(ヤシナ) 87(ハナ) | 9 | pink shoes | 足 | `#FF9BB6` | Sub |
| 88(ヤソハチ) | 3 | left ear accessory | 耳 | `#4F506F` | Secondary |
| 88(ヤソハチ) | 4 | orange long ponytail with hair… | 髪 | `#FF8C36` | Sub |
| 88(ヤソハチ) | 5 | red eyes | 目・瞳 | `#E55A52` | Sub |
| 88(ヤソハチ) | 6 | infinity-shaped (∞=88) pin on … | 首 | `#4F506F` | Secondary |
| 88(ヤソハチ) | 8 | navy blue double-breasted butl… | 胸/腰 | `#5B77A8` | Primary |
| 88(ヤソハチ) | 9 | orange long pants | 脚 | `#FF8C36` | Sub |
| 88(ヤソハチ) | 10 | blue shoes | 足 | `#5B77A8` | Primary |
| 89(ヤスモ) | 1 | The white area on the front le… | 胸 | `#000000` | Sub |
| 89(ヤスモ) | 4 | red necktie | 首 | `#E75E5A` | Sub |
| 89(ヤスモ) | 5 | long magenta hair | 髪 | `#AD496B` | Secondary |
| 89(ヤスモ) | 6 | red eyes | 目・瞳 | `#E75E5A` | Sub |
| 89(ヤスモ) | 7 | magenta-red retro nun-like hab… | 胸/腰/脚 | `#AD496B` | Secondary |
| 89(ヤスモ) | 9 | magenta stockings | 脚 | `#AD496B` | Secondary |
| 89(ヤスモ) | 10 | magenta high-heeled boots | 足 | `#AD496B` | Secondary |
| 92(コトジ) | 1 | #EarShapeType_Fox | 耳 | `#9DB0DB` | Primary |
| 92(コトジ) | 4 | pale blue open short-sleeve bl… | 胸 | `#ABBBDF` | Accent |
| 92(コトジ) | 5 | cream-beige inner tank-top | 胸 | `#E1DBCB` | Sub |
| 92(コトジ) | 6 | beige shorts / white tights | 脚 | `#CDC7B7` | Sub |
| 92(コトジ) | 7 | pale blue-gray ankle boots | 足 | `#ABBBDF` | Accent |
| 92(コトジ) | 8 | loose lavender necktie | 首 | `#B2AFCF` | Secondary |
| 93(クミ) | 3 | #EarShapeType_Fox | 耳 | `#FFF5E1` | Secondary |
| 93(クミ) | 4 | short yellow hair with white h… | 髪 | `#FFD07D` | Primary |
| 93(クミ) | 5 | yellow eyes | 目・瞳 | `#FFD07D` | Primary |
| 93(クミ) | 6 | brown short vest | 胸 | `#9A6A4E` | Accent |
| 93(クミ) | 7 | belt supporter with number des… | 腰 | `#C1A072` | Sub |
| 93(クミ) | 8 | yellow full skirt | 脚 | `#FFD07D` | Primary |
| 93(クミ) | 9 | cream-white knee-high socks / … | 足 | `#FFF5E1` | Secondary |
| 93(クミ) | 10 | white long headband | 頭 | `#FFF5E1` | Secondary |
| 94(ツクシ) | 2 | the left shoulder purple part … | 肩 | `#BD8AE6` | Sub |
| 94(ツクシ) | 4 | medium blue hair | 髪 | `#6AA6D7` | Primary |
| 94(ツクシ) | 6 | blue innerwear | 胸 | `#9BC1E6` | Secondary |
| 94(ツクシ) | 7 | purple pajama tunic with many … | 首 | `#BD8AE6` | Sub |
| 94(ツクシ) | 8 | light blue short skirt | 脚 | `#9BC1E6` | Secondary |
| 96(クルリ) | 4 | pink eyes | 目・瞳 | `#EC9EB4` | Accent |
| 96(クルリ) | 5 | pink masquerade mask with numb… | 頭/付け替え可能 | `#F9C9DE` | Primary |
| 96(クルリ) | 6 | short pink hair with crescent-… | 髪 | `#F9C9DE` | Primary |
| 96(クルリ) | 7 | pink eyes (not visible when we… | 目・瞳 | `#EC9EB4` | Accent |
| 96(クルリ) | 8 | pink masquerade mask with numb… | 頭/付け替え可能 | `#F9C9DE` | Primary |
| 96(クルリ) | 9 | light pink collar with number … | 首 | `#F9C9DE` | Primary |
| 96(クルリ) | 10 | high heels (casual wear) | 足 | `#F26383` | Secondary |
| 96(クルリ) | 11 | pink thigh-high stockings (cas… | 脚 | `#F9C9DE` | Primary |
| 96(クルリ) | 12 | pink puff-sleeve dress with wh… | 胸/腕/腰 | `#F9C9DE` | Primary |
| 97(ココナ) | 4 | long side braid with very long… | 髪 | `#4378C3` | Sub |
| 97(ココナ) | 5 | pale lavender-gray eyes | 目・瞳 | `#6C7A8C` | Accent |
| 97(ココナ) | 6 | white cross emblem on gray nun… | 頭 | `#504695` | Primary |
| 97(ココナ) | 7 | gray nun-like top hat with whi… | 頭 | `#504695` | Primary |
| 97(ココナ) | 8 | gray nun's habit with gray-pur… | 肩/首 | `#6C7A8C` | Accent |
| 97(ココナ) | 9 | long purple skirt | 脚 | `#504695` | Primary |
| 97(ココナ) | 10 | gray ankle boots | 足 | `#6C7A8C` | Accent |
| 98(キュウヤ) | 1 | The white area on the front le… | 胸 | `#B8507C` | Sub |
| 98(キュウヤ) | 4 | magenta-pink medium hair | 髪 | `#AC496B` | Secondary |
| 98(キュウヤ) | 6 | magenta-red retro business sui… | 胸/腰/脚 | `#AC496B` | Secondary |
| 98(キュウヤ) | 7 | red necktie | 首 | `#E65E5A` | Sub |
| 98(キュウヤ) | 8 | gray long pleated skirt | 脚 | `#C9CDCB` | Accent |
| 98(キュウヤ) | 9 | red ankle boots with strap | 足 | `#E65E5A` | Sub |
| 99(ツクモ) | 1 | Large on the central tag of th… | 首 | `#6D7881` | Sub |
| 99(ツクモ) | 2 | The halo of the aureole is bas… | 頭 | `#D1A8CD` | Primary |
| 99(ツクモ) | 4 | dark gray short hair | 髪 | `#4F506F` | Secondary |
| 99(ツクモ) | 5 | roundly shaved red eyebrows | フェイスメイク | `#C84557` | Sub |
| 99(ツクモ) | 6 | pink eyes with red makeup pain… | 目・瞳 | `#D1A8CD` | Primary |
| 99(ツクモ) | 8 | pink light-ring halo behind he… | 頭/背中 | `#D1A8CD` | Primary |
| 99(ツクモ) | 10 | dark gray haori coat with red … | 翼 | `#4F506F` | Secondary |
| 99(ツクモ) | 12 | red obi belt | 腰 | `#C84557` | Sub |
| 99(ツクモ) | 13 | gray slacks | 脚 | `#6D7881` | Sub |
| 99(ツクモ) | 14 | white wrist cuffs | 腕 | `#CACDCC` | Sub |
| バイナ 2(ツギ) | 1 | On the white area at the cente… | 胸 | `#EBE5D6` | Sub |
| バイナ 2(ツギ) | 4 | pale silver-gray long hair | 髪 | `#C9CDCB` | Sub |
| バイナ 2(ツギ) | 5 | amber-orange eyes | 目・瞳 | `#FFA558` | Primary |
| バイナ 2(ツギ) | 6 | orange '試用' (trial / test) lab… | — | `#FFA558` | Primary |
| バイナ 2(ツギ) | 7 | fox tails | 髪 | `#C9CDCB` | Sub |
| バイナ 2(ツギ) | 8 | pale silver-gray long hair | 目・瞳 | `#C9CDCB` | Sub |
| バイナ 2(ツギ) | 9 | amber-orange eyes | — | `#FFA558` | Primary |
| ディケ 10(ツナイ) | 1 | On the left chest of the front… | 胸 | `#5F676F` | Primary |
| ディケ 10(ツナイ) | 3 | dark brown long ponytail | 髪 | `#81494A` | Secondary |
| ディケ 10(ツナイ) | 4 | red eyes with dark yellow pupi… | 目・瞳 | `#E85764` | Sub |
| ディケ 10(ツナイ) | 6 | yellow hazard stripes | 首 | `#FFCE2B` | Sub |
| ディケ 10(ツナイ) | 7 | dark gray full-body restraint … | 胸/首 | `#5F676F` | Primary |
| ディケ 10(ツナイ) | 8 | yellow '調整中' (under adjustment… | 胸 | `#FFCE2B` | Sub |
| ディケ 10(ツナイ) | 9 | red support pillar (base) | — | `#E85764` | Sub |
| ディケ 10(ツナイ) | 10 | '取扱注意' (handle with care) caut… | — | `#FFCE2B` | Sub |
| 000(チトセ) | 1 | on the white area of the left … | 胸 | `#93999B` | Primary |
| 000(チトセ) | 4 | gray shoulder-length hair | 髪 | `#85929C` | Secondary |
| 000(チトセ) | 5 | yellow eyes | 目・瞳 | `#FECA12` | Sub |
| 000(チトセ) | 6 | long gray-beige scarf (with st… | 首 | `#85929C` | Secondary |
| 000(チトセ) | 7 | gray shoulder-length hair | 髪 | `#85929C` | Secondary |
| 000(チトセ) | 8 | yellow eyes | 目・瞳 | `#FECA12` | Sub |
| 000(チトセ) | 9 | long gray-beige scarf (with st… | 首 | `#85929C` | Secondary |
| 000(チトセ) | 10 | casual suit resembling a white… | — | `#F1F3EE` | Sub |
| 零 零 | 3 | cat ear accessories | 耳 | `#FF8682` | Secondary |
| 零 零 | 4 | light brown medium hair | 髪 | `#FFD184` | Accent |
| 零 零 | 7 | casual suit resembling a white… | 胸/腰/脚 | `#E1DCCD` | Primary |
| 零 百 | 1 | On the left chest of the white… | 胸 | `#CDC7B7` | Sub |
| 零 百 | 4 | teal medium hair | 髪 | `#7EAEAB` | Primary |
| 零 百 | 5 | green-brown eyes | 目・瞳 | `#A1A198` | Accent |
| 零 百 | 6 | long light teal scarf (ends wi… | 首 | `#95AD72` | Sub |
| 零 百 | 7 | casual suit resembling a white… | 胸/腰/脚 | `#E0DBCE` | Secondary |
| 100(モモ) | 3 | dark brown slightly messy casu… | 髪 | `#81494A` | Primary |
| 111(アイズ) | 1 | from the left shoulder to the … | 翼 | `#BB3E45` | Primary |
| 111(アイズ) | 3 | salmon-red eyes with large yel… | 目・瞳 | `#FFAC8F` | Secondary |
| 111(アイズ) | 4 | eyes turn red when enraged | 目・瞳 | `#BB3E45` | Primary |
| 111(アイズ) | 5 | dark red hood cap with a salmo… | 頭 | `#BB3E45` | Primary |
| 111(アイズ) | 7 | hero-like salmon-red numbered … | 背中/翼 | `#FFAC8F` | Secondary |
| 111(アイズ) | 8 | white cross-strap belt and tie | 胸/尻尾 | `#E7E9E4` | Accent |
| 111(アイズ) | 9 | dark red military-style unifor… | 胸/腰/脚 | `#BB3E45` | Primary |
| 111(アイズ) | 10 | dark red boots | 足 | `#BB3E45` | Primary |
| 222(ペルゲン) | 3 | salmon-red eyes with special p… | 目・瞳 | `#FFA79B` | Primary |
| 222(ペルゲン) | 5 | long pale-colored twin-tail ha… | 髪 | `#F3F1EA` | Sub |
| 222(ペルゲン) | 6 | pale-colored collar | 首 | `#F3F1EA` | Sub |
| 222(ペルゲン) | 8 | pale brown casual vest | 胸 | `#FFC4B8` | Secondary |
| 222(ペルゲン) | 9 | pink short skirt | 腰 | `#FFA79B` | Primary |
| 222(ドッペル) | 3 | yellow eyes with special pupil… | 目・瞳 | `#FFD07D` | Primary |
| 222(ドッペル) | 4 | yellow brim with a pale yellow… | 頭 | `#FFE2C7` | Accent |
| 222(ドッペル) | 5 | long pale-colored twin-tail ha… | 髪 | `#EAE5D6` | Secondary |
| 222(ドッペル) | 6 | pale-colored collar | 首 | `#F7F5EA` | Sub |
| 222(ドッペル) | 7 | pendant featuring three '2's a… | 首 | `#FFD07D` | Primary |
| 222(ドッペル) | 8 | pale brown casual vest | 胸 | `#FFE2C7` | Accent |
| 222(ドッペル) | 9 | yellow short skirt | 腰 | `#FFD07D` | Primary |
| 222(ドッペル) | 10 | yellow and light-colored casua… | 足 | `#FFD07D` | Primary |
| 444(シテン) | 1 | around the fastening area on t… | 腰 | `#ECAC43` | Accent |
| 444(シテン) | 2 | around the fastening area on t… | 腰 | `#ECAC43` | Accent |
| 444(シテン) | 7 | halo consisting of three squar… | Halo | `#ECAC43` | Accent |
| 444(シテン) | 8 | cyan blue short hair | 髪 | `#94CDD5` | Secondary |
| 444(シテン) | 9 | slightly classical ochre cape … | 首 | `#C1A072` | Sub |
| 444(シテン) | 10 | slightly classical ochre basew… | 首/胸/背中 | `#C1A072` | Sub |
| 444(シテン) | 11 | thin and light dark cyan outer… | 胸 | `#94CDD5` | Secondary |
| 444(シテン) | 13 | ochre boots | 足 | `#C1A072` | Sub |
| 666(リリス) | 7 | light purple, curly and unusua… | 髪 | `#BC8797` | Sub |
| 666(リリス) | 9 | slightly classical magenta col… | 首 | `#F26383` | Secondary |
| 666(リリス) | 11 | slightly classical magenta col… | 首/胸/腰 | `#F26383` | Secondary |
| 666(リリス) | 12 | high-heeled shoes in reddish-p… | 足 | `#F26383` | Secondary |
| 777(ヨロコビ) | 1 | There is an emblem on the fore… | フェイスメイク | `#C1A072` | Primary |
| 777(ヨロコビ) | 3 | eyes with a navy and yellow gr… | 目・瞳 | `#504695` | Secondary |
| 777(ヨロコビ) | 6 | long light brown hair tied at … | 髪 | `#C1A072` | Primary |
| 777(ヨロコビ) | 7 | carrying a dark yellow expansi… | 背中/胸 | `#FFA634` | Accent |
| 777(ヨロコビ) | 8 | gray tracksuit resembling gym … | 胸/脚 | `#FFA634` | Accent |
| 777(ヨロコビ) | 9 | navy leather shoes | 足 | `#8B9BAC` | Sub |
| 777(ヨロコビ) | 1 | There is an emblem on the fore… | フェイスメイク | `#C1A072` | Primary |
| 777(ヨロコビ) | 3 | eyes with a navy and yellow gr… | 目・瞳 | `#504695` | Secondary |
| 777(ヨロコビ) | 6 | long light brown hair tied at … | 髪 | `#C1A072` | Primary |
| 777(ヨロコビ) | 7 | wearing a dark yellow slot mac… | — | `#FFA634` | Accent |
| 777(ヨロコビ) | 8 | carrying a dark yellow slot ma… | 背中/胸 | `#FFA634` | Accent |
| 777(ヨロコビ) | 9 | gray tracksuit resembling gym … | 胸/脚 | `#8B9BAC` | Sub |
| 777(ヨロコビ) | 10 | navy leather shoes | 足 | `#504695` | Secondary |
| 888(ムゲン) | 1 | Large on the forehead / vermil… | フェイスメイク | `#E8593A` | Sub |
| 888(ムゲン) | 3 | light pink intake long hair | 髪 | `#FFA79B` | Primary |
| 888(ムゲン) | 4 | thick and large light pink eye… | フェイスメイク | `#FFA79B` | Primary |
| 888(ムゲン) | 5 | narrow vermilion eyes / pupils… | 目・瞳 | `#E8593A` | Sub |
| 888(ムゲン) | 6 | tail feathers resembling a pho… | 翼/尻尾 | `#E8593A` | Sub |
| 888(ムゲン) | 7 | vermilion inner sweater | 胸 | `#E8593A` | Sub |
| 888(ムゲン) | 8 | casual reddish-purple outerwea… | 腕/肩 | `#AD496B` | Accent |
| 888(ムゲン) | 9 | light orange slacks | 脚 | `#FFA276` | Secondary |
| 888(ムゲン) | 10 | vermilion geta / light pink so… | 足 | `#E8593A` | Sub |
| トレッド 3×11(トリィレブン) | 1 | around the edge of the fabric … | 胸 | `#F85DB3` | Sub |
| トレッド 3×11(トリィレブン) | 3 | pale golden hair with a large … | 髪 | `#FFD58F` | Primary |
| トレッド 3×11(トリィレブン) | 9 | purple ribbon with two round b… | 首 | `#BD8AE6` | Sub |
| トレッド 3×11(トリィレブン) | 10 | two round brooches featuring a… | 首 | `#BD8AE6` | Sub |
| トレッド 3×11(トリィレブン) | 12 | bright pink cape with a white … | 首/肩 | `#FFB1AB` | Accent |
| トレッド 3×11(トリィレブン) | 15 | fashion boots in purple and br… | 足 | `#BD8AE6` | Sub |
| 量産型 111(アイズ) | 1 | from the left shoulder to the … | 翼 | `#D75341` | Primary |
| 量産型 111(アイズ) | 2 | lot mark on the left cheek / r… | フェイスメイク | `#D75341` | Primary |
| 量産型 111(アイズ) | 4 | salmon-red eyes with large yel… | 目・瞳 | `#FFD58F` | Sub |
| 量産型 111(アイズ) | 6 | red hood cap with a salmon-red… | 頭 | `#D75341` | Primary |
| 量産型 111(アイズ) | 7 | short blonde hair with white b… | 髪 | `#FCBD47` | Sub |
| 量産型 111(アイズ) | 8 | hero-like salmon-red numbered … | 背中/翼 | `#FFAC8F` | Secondary |
| 量産型 111(アイズ) | 9 | white cross-strap belt and tie | 胸/尻尾 | `#E7E9E3` | Sub |
| 量産型 111(アイズ) | 10 | red military-style uniform | 胸/腰/脚 | `#D75341` | Primary |
| 量産型 111(アイズ) | 11 | red boots | 足 | `#D75341` | Primary |
| 量産型 444(シテン) | 1 | around the fastening area on t… | 腰 | `#C9CDCB` | Sub |
| 量産型 444(シテン) | 8 | halo consisting of three squar… | Halo | `#C9CDCB` | Sub |
| 量産型 444(シテン) | 9 | cyan blue short hair | 髪 | `#94CDD5` | Secondary |
| 量産型 444(シテン) | 10 | slightly classical ochre cape … | 首 | `#C1A072` | Sub |
| 量産型 444(シテン) | 11 | slightly classical ochre basew… | 首/胸/背中 | `#C1A072` | Sub |
| 量産型 444(シテン) | 12 | thin and light dark cyan outer… | 胸 | `#94CDD5` | Secondary |
| 量産型 444(シテン) | 14 | ochre boots | 足 | `#C1A072` | Sub |
| 量産型 666(リリス) | 1 | halo, brooch, and wings are th… | Halo/首/翼 | `#F26383` | Secondary |
| 量産型 666(リリス) | 2 | lot mark on the left cheek / d… | フェイスメイク | `#BC8797` | Sub |
| 量産型 666(リリス) | 6 | halo with three '6's arranged … | Halo | `#F26383` | Secondary |
| 量産型 666(リリス) | 7 | wings inspired by the motif of… | 翼 | `#BC8797` | Sub |
| 量産型 666(リリス) | 8 | light purple, curly and unusua… | 髪 | `#A95D8D` | Sub |
| 量産型 666(リリス) | 9 | brooch with three '6's arrange… | 胸 | `#C84557` | Accent |
| 量産型 666(リリス) | 10 | slightly classical magenta col… | 首 | `#F26383` | Secondary |
| 量産型 666(リリス) | 11 | brooch with three '6's arrange… | 腰 | `#C84557` | Accent |
| 量産型 666(リリス) | 12 | slightly classical magenta col… | 首/胸/腰 | `#F26383` | Secondary |
| 量産型 666(リリス) | 13 | high-heeled shoes in reddish-p… | 足 | `#A95D8D` | Sub |
| 量産型 777(ヨロコビ) | 1 | There is an emblem on the fore… | フェイスメイク | `#ECAC42` | Accent |
| 量産型 777(ヨロコビ) | 2 | lot mark on the left cheek / d… | フェイスメイク | `#ECAC42` | Accent |
| 量産型 777(ヨロコビ) | 4 | mechanical eyes with a navy an… | 目・瞳 | `#504695` | Secondary |
| 量産型 777(ヨロコビ) | 7 | long light brown hair tied at … | 髪 | `#C1A072` | Primary |
| 量産型 777(ヨロコビ) | 8 | carrying a dark yellow expansi… | 背中/胸 | `#ECAC42` | Accent |
| 量産型 777(ヨロコビ) | 9 | gray tracksuit resembling gym … | 胸/脚 | `#ECAC42` | Accent |
| 量産型 777(ヨロコビ) | 10 | navy leather shoes | 足 | `#8B9BAC` | Sub |
| 量産型 777(ヨロコビ) | 1 | There is an emblem on the fore… | フェイスメイク | `#ECAC42` | Accent |
| 量産型 777(ヨロコビ) | 2 | lot mark on the left cheek / d… | フェイスメイク | `#ECAC42` | Accent |
| 量産型 777(ヨロコビ) | 4 | mechanical eyes with a navy an… | 目・瞳 | `#504695` | Secondary |
| 量産型 777(ヨロコビ) | 7 | long light brown hair tied at … | 髪 | `#C1A072` | Primary |
| 量産型 777(ヨロコビ) | 8 | wearing a dark yellow slot mac… | — | `#ECAC42` | Accent |
| 量産型 777(ヨロコビ) | 9 | carrying a dark yellow slot ma… | 背中/胸 | `#ECAC42` | Accent |
| 量産型 777(ヨロコビ) | 10 | gray tracksuit resembling gym … | 胸/脚 | `#8B9BAC` | Sub |
| 量産型 777(ヨロコビ) | 11 | navy leather shoes | 足 | `#504695` | Secondary |

## 2. 未登録の実測色との対応

エントリの色が `ColorPalette` に無いもの。**その HEX を追加**したうえで、
`AppliesTo` にそのエントリの `BodyPart` を入れる形になる。

| キャラ | # | 記述 | 部位 | 追加する HEX | 面積比 | 根拠 |
|---|---|---|---|---|---|---|
| 7(ナナ) | 1 | white area on the front-left c… | 胸 | `#4245A3` | 52.9% | 球体の前左胸部分にある数字7は濃紺色で描かれている。 |
| 8(ワカツ) | 4 | red eyes | 目・瞳 | `#FF6574` | 2.1% | 赤い目が確認できる。 |
| 9(チカ) | 4 | silver gray long hair with whi… | 髪 | `#9FA7BE` | 41.8% | 銀の灰色の髪と白いアクセントの色は画像で確認できます。 |
| 16(ソロク) | 6 | white cape | 肩/首 | `#F4FAE8` | 26.0% | ケープの色は白。 |
| 16(ソロク) | 8 | pink casual wear with heart an… | 胸 | `#F9BBC0` | 6.6% | ピンクのカジュアルウェアの色。 |
| 20(ハツカ) | 8 | long white open coat | 胸 | `#F4FAE8` | 7.6% | 長い白いコートは全体的に白っぽい色合いになっている。 |
| 21(ハツヒ) | 1 | the white area on the front le… | 胸 | `#F3F1EE` | 5.0% | 前面左胸の白い領域は淡い灰色で、数字は暗い色で記されています。 |
| 23(ツグミ) | 1 | the right side of the light gr… | 腰 | `#8DC0AB` | 2.0% | 球体上のパターンと数字「23」の色は #8DC0AB です。 |
| 23(ツグミ) | 2 | the right side of the area wit… | 胸 | `#8DC0AB` | 2.0% | フーデッドトップの数字「23」の色は #8DC0AB です。 |
| 23(ツグミ) | 3 | #EarShapeType_Fox | 耳 | `#EFF5ED` | 8.7% | 耳の色はフォックスを連想させる #EFF5ED です。 |
| 26(ニロク) | 7 | long rose-pink maxi skirt | 脚 | `#FABBC0` | 45.1% | ロングローズピンクマキシスカートに使われている色です。 |
| 35(サトコ) 35(ミコ) | 10 | white robe with orange hakama … | 胸/腰/脚 | `#FAF9E8` | 4.1% | 白の衣がこの色に近く見えるため。 |
| 41(ヨソイチ) | 4 | blue-gray eyes with light blue… | 目・瞳 | `#80A8CC` | 3.2% | 目の色は青灰色で、まつげは薄い青です。 |
| 41(ヨソイチ) | 6 | short blue-gray hair | 髪 | `#80A8CC` | 3.2% | 髪の色は青灰色です。 |
| 41(ヨソイチ) | 9 | blue-gray shorts | 脚 | `#80A8CC` | 3.2% | ショーツは青灰色です。 |
| 48(シハチ) | 11 | brown boots | 足 | `#848A6F` | 2.4% | 茶色のブーツは#848A6Fに塗られている。 |
| 52(イツギ) | 4 | long silver-gray hair tied at … | 髪 | `#D3DBDC` | 6.9% | 髪は銀灰色に見え、おくれ毛の部分が薄灰色。 |
| 53(イツゾウ) | 6 | white collared shirt | 首 | `#FAF9E8` | 6.6% | 襟付きのシャツが白色です。 |
| 53(イツゾウ) | 10 | white leg warmers / orange sho… | 足 | `#FAF9E8` | 6.6% | レッグウォーマーが白色で、靴がオレンジ色です。 |
| 56(イソロク) | 1 | On the gray area of the left c… | 胸 | `#67D488` | 3.3% | 緑色は漢字の色で使用されている。 |
| 56(イソロク) | 4 | short light gray two-tone hair | 髪 | `#CECCC5` | 42.8% | 髪の主要な色は淡いグレーで表現されている。 |
| 57(イズナ) | 2 | On the armband attached to the… | 腕 | `#FFFF6B` | 2.1% | 右肩と上腕に付いた腕章のアラビア数字57が黄色緑ではない色で描かれてい |
| 57(イズナ) | 11 | armband with number on right s… | 肩/腕 | `#FFFF6B` | 2.1% | 右肩の腕章に数字が描かれているが、色は黄色緑ではない。 |
| 60(ムソウ) | 9 | white wide color bib (usual ou… | 胸 | `#FFF1F0` | 8.3% | 白いビブの色です。 |
| 61(ロクイチ) 61(ロイ) | 5 | heart and key motif | 付け替え可能 | `#E85764` | 18.0% | 心と鍵のモチーフは該当する色で確認できる。 |
| 61(ロクイチ) 61(ロイ) | 6 | heart and key motif charm hair… | 髪 | `#E85764` | 18.0% | 髪飾りのチャームも同じモチーフの色が使われている。 |
| 61(ロクイチ) 61(ロイ) | 8 | roundly shaved red eyebrows | フェイスメイク | `#E85764` | 18.0% | 眉毛は赤で示されている。 |
| 61(ロクイチ) 61(ロイ) | 9 | light pink vest with heart and… | 胸 | `#F9BBC0` | 6.2% | ベストは薄いピンク色に見える。 |
| 61(ロクイチ) 61(ロイ) | 11 | red uniform with number and wh… | 胸/腰/脚 | `#E85764` | 18.0% | 赤い制服はこの色がより目立っている。 |
| 61(ロクイチ) 61(ロイ) | 15 | white inner shirt | 胸 | `#F4FAE8` | 2.8% | インナーシャツは白っぽい色で確認できる。 |
| 69(ロック) | 5 | light pink cape-like collar | 首 | `#EDD2DA` | 9.0% | 薄桃色のケープのような襟が薄いピンクで塗られています。 |
| 74(ナナヨ) | 3 | translucent white shawl/cape w… | 肩/首/背中 | `#E9F2FB` | 3.8% | 透明な白のショール/ケープが使用されている。 |
| 74(ナナヨ) | 8 | translucent white shawl/cape w… | 肩/首 | `#E9F2FB` | 3.8% | 透明な白のショール/ケープが使用されている（番号付き）。 |
| 74(ナナヨ) | 9 | gray geta sandals | 足 | `#ABB4BC` | 2.2% | 灰色の下駄サンダルを履いている。 |
| 76(シチロク) | 11 | white knee-high socks | 足 | `#E1E4E6` | 6.6% | 白いニーハイソックスを履いている |
| 81(ヤイチ) | 3 | #EarShapeType_Fox | 耳 | `#612C26` | 2.5% | 狐の耳にこの色が使われています。 |
| 88(ヤソハチ) | 7 | piano-keyboard holographic rin… | — | `#FFE8D7` | 4.7% | フォログラフィックリングには白のFFE8D7が使用されている。 |
| 92(コトジ) | 2 | short pale-blue hair | 髪 | `#8398C1` | 3.2% | Hair is short and pale blue, matchi |
| 92(コトジ) | 3 | lavender-gray eyes | 目・瞳 | `#8398C1` | 3.2% | Lavender-gray eyes match the measur |
| 444(シテン) | 6 | light blue cheek pattern accen… | フェイスメイク | `#A4DAEF` | 6.3% | 頬の模様にこの色が使用されています。 |
| 444(シテン) | 12 | light blue leggings | 脚 | `#A4DAEF` | 6.3% | レギンス全体にこの色が使用されています。 |
| 量産型 444(シテン) | 3 | lot mark on the left cheek / d… | フェイスメイク | `#A4DAEF` | 6.3% | 左頬のロットマークは暗いシアンで確認できる。 |
| 量産型 444(シテン) | 5 | dark cyan eyes with gray speci… | 目・瞳 | `#A4DAEF` | 6.3% | 目は暗いシアンで塗られている。 |
| 量産型 444(シテン) | 7 | light blue cheek pattern accen… | フェイスメイク | `#A4DAEF` | 6.3% | 頬の模様はライトブルーで塗られている。 |
| 量産型 444(シテン) | 13 | light blue leggings | 脚 | `#A4DAEF` | 6.3% | レギンスはライトブルーで塗られている。 |

---

*色の対応づけは AI が公式画像から判断した推定です。DB へ反映する前に確認してください。*
*候補に無い色・画像で確認できない要素は表から除いてあります（推測で埋めていません）。*

自動生成: `python -m src.tools.verify_appearance_detail --all --check hexmap` (100BeautiesLab_GeneratorsAI)
