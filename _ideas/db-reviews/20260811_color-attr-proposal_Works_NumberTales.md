## `AppearanceDetail[].Attrs` 色情報の補完案（自動生成・画像根拠）

再検査日: 2026-08-11 / 対象 111 件

### BodyPart 補完の効果

- BodyPart 欠落: **71 件 → 16 件**（49 キャラ → 14 キャラ）

残っているものは装飾・アクセント系（`four white buttons` / `orange accents` など）が中心で、
部位を 1 つに決めにくいものが多い。末尾に一覧を置いた。

### 色の根拠について

**色語は公式画像から読み取っている。** `ColorPalette` の HEX は配色検知ツールが画像から
起こした出力であり、いま補完しようとしている対象そのもの。HEX から色語を逆引きすると
不完全な値を根拠に記述を書くことになるため、根拠は typedef `$palette.source` 宣言画像
（設定原画・設定資料・コアフォルダ画像）に置いた。
読み取りには `gpt-4o` を使用し、配色検知ツールが認識できる色語のみを選ばせている。

### 補完案（275 件）

色情報が入っていないエントリについて、画像から読み取った色。
各行の `#` は `AppearanceDetail[]` のインデックス（1 始まり）。
「読めた色」の先頭語を使って、そのエントリの `Attrs` へ次を足すと `AppliesTo` へ転記されるようになる。

```json
{ "AttrLabel": "#DesignAttr_Color", "value_JP": "<日本語>", "value_EN": "<色語>" }
```

| キャラ | # | 記述 | 読めた色 | 根拠 |
|---|---|---|---|---|
| 1(ハジメ) | 4 | #EarShapeType_Fox | `orange` (橙) | 耳はオレンジ色です。 |
| 1(ハジメ) | 5 | energetic open smile | `orange` (橙) | 口元がオレンジ色です。 |
| 1(ハジメ) | 6 | arrow-shaped chest zipper | `red`, `orange` (赤・橙) | ジッパーは赤とオレンジの中間色です。 |
| 1(ハジメ) | 9 | casual outfit | `orange`, `red` (橙・赤) | 服装全体はオレンジと赤のトーンで構成されています。 |
| 2(ツグ) | 4 | #EarShapeType_Fox | `orange` (橙) | スカーフはオレンジ色で塗られています。 |
| 3(ナオ) | 2 | the front-left chest of the top / dark / Arabic numeral | `black` (黒) | 胸の左肩にある数字'3'は黒で描かれているため |
| 3(ナオ) | 4 | #EarShapeType_Fox | `yellow`, `white` (黄・白) | 耳は黄色と白の2色で構成されているため |
| 4(モチ) | 3 | #EarShapeType_Fox | `cyan` (水色) | 耳はシアン色に塗られているため。 |
| 4(モチ) | 9 | skirt | `cyan` (水色) | スカートはシアン色に塗られているため。 |
| 5(イズ) | 9 | tape wristbands (wrapped around the head and ponytail) | `white` (白) | テープリストバンドは白で描かれている。 |
| 5(イズ) | 11 | tape wristbands (wrapped around the head and right arm) | `white` (白) | テープリストバンドは白で描かれている。 |
| 6(ムイ) | 2 | #EarShapeType_Fox | `pink`, `white` (桃・白) | 耳はピンクと白に塗られている。 |
| 6(ムイ) | 6 | hexagonal brooch | `blue` (青) | ブローチは青色に塗られている。 |
| 6(ムイ) | 7 | lace trim | `white` (白) | レース部分は白色に塗られている。 |
| 6(ムイ) | 8 | Victorian dress | `purple` (紫) | ドレスは紫色に塗られている。 |
| 7(ナナ) | 2 | front left chest of the hakama / dark / Arabic numeral  | `black` (黒) | 胸元の数字は黒で描かれている |
| 7(ナナ) | 3 | #EarShapeType_Fox | `white` (白) | 耳は白で塗られている |
| 7(ナナ) | 7 | prayer beads necklace | `blue` (青) | 数珠は青色で描かれている |
| 7(ナナ) | 8 | Far-Easten style coat | `purple` (紫) | コートは紺と紫の色合い |
| 8(ワカツ) | 3 | #EarShapeType_Fox | `orange` (橙) | 耳のベースの色が橙色です。 |
| 8(ワカツ) | 8 | mechanic style | `orange`, `brown` (橙・茶) | メカニック風の服が橙色と茶色です。 |
| 8(ワカツ) | 9 | tactical vest | `brown` (茶) | 戦術ベストが茶色です。 |
| 8(ワカツ) | 10 | tool pouches | `orange` (橙) | ツールポーチが橙色です。 |
| 9(チカ) | 2 | the left chest of the robe outfit / dark / Arabic numer | `black` (黒) | ローブの左胸の「9」は黒色です。 |
| 9(チカ) | 3 | #EarShapeType_Fox | `white` (白) | 耳の内側は白色です。 |
| 9(チカ) | 6 | tails in ring arrangement | `blue`, `white` (青・白) | 尻尾は青と白の縞模様です。 |
| 9(チカ) | 7 | composed mysterious smile | `cyan` (水色) | 顔に微笑が浮かんでいますが、色は確認できません。 |
| 9(チカ) | 8 | large dark cape | `blue` (青) | マントは大きく暗い青色です。 |
| 10(ミツル) | 2 | the left chest of the top (slightly inconspicuous due t | `red` (赤) | 『10』の数字は赤で描かれています。 |
| 10(ミツル) | 3 | #EarShapeType_Fox | `red`, `white` (赤・白) | 狐耳は赤と白で塗られています。 |
| 10(ミツル) | 8 | Chinese-style mandarin-collar jacket | `red` (赤) | ジャケットは赤で描かれています。 |
| 10(ミツル) | 9 | wide-leg pants | `pink`, `white` (桃・白) | ワイドパンツはピンクと白で描かれています。 |
| 11(トウイチ) | 2 | #EarShapeType_Cat | `gray` (灰) | 耳が灰色で塗られています。 |
| 11(トウイチ) | 3 | two arrow-shaped hair pins | `red orange` (朱) | ヘアピンが朱色で塗られています。 |
| 11(トウイチ) | 6 | long hooded coat | `blue`, `gray` (青・灰) | コートが青と灰色で塗られています。 |
| 12(トウジ) | 1 | on left shoulder, around right just below the edge of t | `orange` (橙) | 数字「12」は橙色で記載されています。 |
| 12(トウジ) | 3 | bangs covering the left eye | `orange` (橙) | 前髪は橙色で左目を隠しています。 |
| 12(トウジ) | 4 | #EarShapeType_Fox | `orange` (橙) | 耳は橙色でキツネのような形状をしています。 |
| 12(トウジ) | 5 | poncho cape / large cloak | `orange` (橙) | ポンチョケープや大きなマントは橙色です。 |
| 13(トミ) | 3 | #EarShapeType_Fox | `white`, `cyan` (白・水色) | 耳は主に白色で内側が水色に塗られているため。 |
| 13(トミ) | 5 | wide enthusiastic smile | `red`, `pink` (赤・桃) | 口元や頬の部分に赤系の色が使用されているため。 |
| 13(トミ) | 6 | sporty jersey | `blue` (青) | スポーティなジャージは青色に塗られているため。 |
| 13(トミ) | 7 | multi-color stripe | `blue`, `yellow`, `white` (青・黄・白) | ストライプには青、黄、白が使われているため。 |
| 14(トヨ) | 3 | #EarShapeType_Fox | `blue` (青) | 耳の内側が水色に近い青色に塗られています。 |
| 14(トヨ) | 12 | tri-color outfit | `pink`, `red`, `blue` (桃・赤・青) | 服はピンク、赤、青の三色に分かれています。 |
| 15(トウゴ) | 3 | #EarShapeType_Fox | `pink` (桃) | 耳はピンクに塗られています。 |
| 15(トウゴ) | 7 | harness equipped with safety device on the back | `green` (緑) | 安全装置のハーネスは緑色です。 |
| 15(トウゴ) | 8 | casual private outfit | `green`, `red`, `white` (緑・赤・白) | 服装は緑、赤、白のカジュアルな配色です。 |
| 15(トウゴ) | 9 | pale-colored jacket | `green` (緑) | ジャケットは緑色です。 |
| 15(トウゴ) | 10 | burn mark on right eye and ear | `orange` (橙) | 右目と耳の火傷はオレンジ色で表現されています。 |
| 16(ソロク) | 1 | around the brim of the hat, on the right side / dark /  | `white`, `blue` (白・青) | 帽子の縁に描かれた '16' の色は白地に青で書かれています。 |
| 16(ソロク) | 2 | #EarShapeType_Fox | `pink` (桃) | 耳はピンク色に塗られており形状がキツネ耳です。 |
| 16(ソロク) | 7 | heart and key motif | `pink`, `white` (桃・白) | モチーフはピンクと白を基調にしています。 |
| 16(ソロク) | 9 | voluminous feminine silhouette | `pink`, `blue` (桃・青) | シルエット全体的にピンクと青が主要な色です。 |
| 17(トナ) | 3 | #EarShapeType_Fox | `yellow` (黄) | 耳の内側が黄色に塗られています |
| 17(トナ) | 5 | calm composed look | `blue` (青) | 落ち着いた印象の青色が服に使用されています |
| 17(トナ) | 8 | androgynous | `gray`, `blue` (灰・青) | エンドロジナスな印象を与える灰色と青色が用いられています |
| 17(トナ) | 9 | casual study outfit | `blue`, `red` (青・赤) | カジュアルな印象の青と赤の組み合わせが服装に使用されています |
| 18(トウヤ) | 3 | #EarShapeType_Fox | `brown` (茶) | 耳は茶色で塗られているため。 |
| 18(トウヤ) | 6 | blazer over shirt | `orange`, `pink` (橙・桃) | ブレザーは橙色、シャツは桃色で塗られているため。 |
| 18(トウヤ) | 7 | skirt | `orange` (橙) | スカートは橙色で塗られているため。 |
| 19(トク) | 3 | #EarShapeType_Fox | `white`, `pink` (白・桃) | 耳は外側が白で内側がピンクに塗られている。 |
| 20(ハツカ) | 1 | the buckle part of the choker / dark / Arabic numeral ' | `black` (黒) | 首輪の留め具は黒色です。 |
| 20(ハツカ) | 2 | the buckle part of the belt on the waist / dark / Arabi | `black` (黒) | 腰のベルトのバックルは黒色です。 |
| 20(ハツカ) | 3 | #EarShapeType_Fox | `white`, `gray` (白・灰) | 耳は白と灰色で描かれています。 |
| 20(ハツカ) | 4 | choker with a number | `orange` (橙) | 首輪にある数の部分はオレンジ色です。 |
| 20(ハツカ) | 6 | serene gentle smile/worried expression | `pink` (桃) | 笑顔、心配顔には頬が桃色です。 |
| 20(ハツカ) | 10 | belt with a number | `orange` (橙) | ベルトにある数の部分はオレンジ色です。 |
| 20(ハツカ) | 11 | casual private outfit | `orange`, `gray`, `white` (橙・灰・白) | カジュアルな服はオレンジと灰色、白色が使われています。 |
| 21(ハツヒ) | 2 | small on the left collar and left shoulder of the basew | `black` (黒) | アラビア数字 '21' は黒色で描かれています。 |
| 22(フジ) | 3 | #EarShapeType_Fox | `yellow` (黄) | キツネ耳の色は黄色です。 |
| 22(フジ) | 5 | earrings | `yellow` (黄) | イヤリングの色は黄色です。 |
| 22(フジ) | 6 | two scorpion-type segmented tails (freely movable like  | `yellow` (黄) | 尻尾の色は黄色です。 |
| 22(フジ) | 11 | holograms resembling the moon and sun on a head modeled | `orange`, `yellow` (橙・黄) | ホログラムの色はオレンジと黄色です。 |
| 22(フジ) | 14 | ribbon sash at waist | `yellow` (黄) | 腰のリボンの色は黄色です。 |
| 23(ツグミ) | 5 | adventurous smile | `yellow` (黄) | ワイドレッグパンツは黄色です。 |
| 24(フトシ) | 1 | the clasp of the neck scarf / dark color / Arabic numer | `blue` (青) | 首のスカーフの留め具に青が使用されている。 |
| 24(フトシ) | 8 | casual private outfit | `pink`, `blue`, `white` (桃・青・白) | 服装の色としてピンク、青、白が使われている。 |
| 25(フィズ) | 9 | casual private outfit | `green`, `blue` (緑・青) | 私服のカジュアルな色が緑と青の色合いです。 |
| 26(ニロク) | 2 | small area from the center of the sweater collar to the | `pink` (桃) | セーターの襟から胸元の中央部にかけて明るいピンク色のアラビア数字『26』が見られます。 |
| 26(ニロク) | 3 | #EarShapeType_Fox | `pink` (桃) | 耳は濃いピンク色で塗られており、狐の耳の形をしています。 |
| 27(ツギナ) | 5 | erected fox ears | `cyan`, `white` (水色・白) | 耳が水色で内側が白色に見えるため |
| 27(ツギナ) | 11 | casual private outfit | `purple`, `white` (紫・白) | 服は紫で装飾が白色のため |
| 28(ニハチ) | 6 | Somewhat large as body paint on the left shoulder's bar | `black` (黒) | 画像の28の描かれた肩のタトゥーは黒色です。 |
| 28(ニハチ) | 7 | Somewhat large as body paint on the right shoulder's ba | `black` (黒) | 画像の右肩のタトゥーは黒色です。 |
| 28(ニハチ) | 8 | #EarShapeType_Fox | `orange` (橙) | 耳はオレンジ色です。 |
| 28(ニハチ) | 10 | dangling earrings | `orange` (橙) | 画像にはオレンジ色のぶら下がりイヤリングがあります。 |
| 28(ニハチ) | 11 | mathematical body tattoo | `black` (黒) | 画像の数学的タトゥーは黒色です。 |
| 29(ニトク) | 1 | #EarShapeType_Fox | `blue` (青) | 耳は青系の色で塗られている |
| 29(ニトク) | 3 | anxious expression | `purple` (紫) | 表情の色は紫系で塗られている |
| 29(ニトク) | 7 | medium-large bust | `purple` (紫) | バスト周辺は紫系の色で塗られている |
| 30(ミツト) | 4 | #EarShapeType_Fox | `yellow` (黄) | 画像の耳は黄色い色で描かれている。 |
| 30(ミツト) | 6 | warm cheerful smile | `yellow` (黄) | キャラクター全体的に暖かく明るい色調（黄色）が使われている。 |
| 31(ミツイ) | 4 | on the bare skin of the left shoulder as body paint, sl | `black` (黒) | 左肩のボディペイントは黒で描かれている。 |
| 31(ミツイ) | 5 | #EarShapeType_Fox | `cyan`, `white` (水色・白) | 耳は水色と白で描かれている。 |
| 31(ミツイ) | 9 | athletic outfit | `blue`, `white`, `yellow` (青・白・黄) | 運動着は青と白、黄色で描かれている。 |
| 31(ミツイ) | 11 | thigh-high socks with boots | `cyan`, `white`, `blue` (水色・白・青) | 靴下は水色と白、ブーツは青で描かれている。 |
| 31(ミツイ) | 14 | mathematical body paint | `black` (黒) | 数学のボディペイントは黒で描かれている。 |
| 32(ミツギ) | 2 | the right side of the area with a pale stripe pattern f | `black` (黒) | アラビア数字の'32'は黒で描かれています。 |
| 32(ミツギ) | 4 | #EarShapeType_Fox | `yellow`, `green` (黄・緑) | 耳は黄緑色で塗られていますが、基部は白です。 |
| 32(ミツギ) | 8 | casual open-collar jacket | `cyan` (水色) | 開襟ジャケットはシアン色で塗られています。 |
| 33(ミサ) | 1 | Slightly small from the left chest to the left shoulder | `red`, `orange` (赤・橙) | 画像のケープの色が赤橙色に見えるため。 |
| 33(ミサ) | 2 | On the back of each glove / dark / Arabic numeral '33' | `red`, `orange` (赤・橙) | 画像の手袋の色が赤橙色に見えるため。 |
| 33(ミサ) | 3 | #EarShapeType_Fox | `orange` (橙) | 画像の耳の色が橙色に見えるため。 |
| 33(ミサ) | 9 | ear-covering maid cap | `red`, `orange` (赤・橙) | 画像のメイドキャップの色が赤橙色に見えるため。 |
| 34(サトシ) サンジ | 2 | Slightly large on the chest area of the apron / dark /  | `black` (黒) | エプロンの数字は黒色で描かれているため。 |
| 34(サトシ) サンジ | 3 | #EarShapeType_Fox | `blue` (青) | キツネ耳は青色で描かれているため。 |
| 35(サトコ) 35(ミコ) | 3 | #EarShapeType_Fox | `orange` (橙) | キツネ耳の色はオレンジです。 |
| 35(サトコ) 35(ミコ) | 9 | necktie (usual) | `orange` (橙) | ネクタイの色はオレンジです。 |
| 35(サトコ) 35(ミコ) | 11 | gohei stick (miko) | `white` (白) | 御幣の色は白です。 |
| 36(ミトム) | 2 | Slightly large on the entire chest area of the base wea | `black` (黒) | アラビア数字「36」は黒で描かれています。 |
| 36(ミトム) | 3 | #EarShapeType_Fox | `orange` (橙) | 耳はオレンジ色で描かれています。 |
| 36(ミトム) | 6 | Victorian-lolita dress | `yellow`, `purple`, `pink` (黄・紫・桃) | ビクトリアン・ロリータ風ドレスは黄色、紫、ピンクで構成されています。 |
| 36(ミトム) | 10 | bow ribbon at chest | `pink` (桃) | 胸のリボンはピンク色で描かれています。 |
| 37(サナ) | 2 | #EarShapeType_Fox | `white` (白) | 耳の内側は白です。 |
| 37(サナ) | 9 | casual private outfit | `red`, `blue`, `yellow` (赤・青・黄) | カジュアルな私服は、赤と青、黄色の要素を持っています。 |
| 39(サク) | 1 | Slightly large, centered on the front of the sphere at  | `black` (黒) | 数字は濃い色で黒に見えます。 |
| 39(サク) | 2 | Prominently across the entire supporter visible from th | `black` (黒) | 数字は濃い色で黒に見えます。 |
| 39(サク) | 9 | belt supporter with number design at waist | `black` (黒) | 数字部分は黒に見えます。 |
| 40(ヨソ) | 2 | #EarShapeType_Fox | `cyan` (水色) | 耳は水色で塗られています。 |
| 40(ヨソ) | 8 | mystical genie aesthetic | `blue`, `cyan` (青・水色) | 衣装全体が青と水色でミスティックな印象を与えます。 |
| 40(ヨソ) | 9 | pattern inspired by '40' | `cyan`, `blue` (水色・青) | 数字「40」のデザインが水色と青で描かれています。 |
| 41(ヨソイチ) | 3 | #EarShapeType_Fox | `blue` (青) | 耳は青色で塗られています。 |
| 42(ヨツグ) | 2 | on the left collar, near the edge of the fabric, somewh | `red`, `orange` (赤・橙) | 左襟の端にある「42」の色は赤と橙の中間です。 |
| 42(ヨツグ) | 3 | #EarShapeType_Fox | `white` (白) | 耳の内側の色は白です。 |
| 43(シトミ) | 3 | #EarShapeType_Fox | `blue` (青) | 耳はブルーに塗られています。 |
| 43(シトミ) | 10 | often holding a game controller | `yellow`, `gray` (黄・灰) | 手に持っているゲームコントローラーは黄と灰の色が使われています。 |
| 44(シトシ) | 2 | on the left chest of the vest, slightly above the butto | `black` (黒) | 数字『44』は黒で描かれています。 |
| 44(シトシ) | 3 | #EarShapeType_Fox | `white` (白) | 耳の内側は白で塗られています。 |
| 45(シゴ) | 3 | #EarShapeType_Fox | `blue` (青) | 耳は青色で描かれています。 |
| 46(シロー) | 2 | on the left collar, near the edge of the fabric, small  | `black` (黒) | 数字「46」は黒で描かれている |
| 46(シロー) | 3 | #EarShapeType_Fox | `blue` (青) | 耳は青で塗られている |
| 47(シナ) | 3 | #EarShapeType_Fox | `gray`, `blue` (灰・青) | 耳が灰色と青に塗られている。 |
| 48(シハチ) | 2 | on the left collar, near the neck, small / dark / Arabi | `black` (黒) | 襟の左側にあるアラビア数字'48'の色は黒です。 |
| 48(シハチ) | 3 | #EarShapeType_Fox | `gray`, `white` (灰・白) | キツネ型の耳は灰色と白色です。 |
| 49(ヨチカ) | 3 | #EarShapeType_Fox | `white` (白) | 耳の内側は白で塗られています。 |
| 49(ヨチカ) | 6 | a slightly unsociable, boyish face | `blue` (青) | 顔のほとんどが青で構成されています。 |
| 49(ヨチカ) | 7 | a smile that looks dead in the eyes (expression when tr | `blue` (青) | 顔のほとんどが青で構成されています。 |
| 50(ナカバ) | 3 | cat whiskers | `black` (黒) | 髭の色は黒に見えます。 |
| 50(ナカバ) | 4 | mint-colored hooded top wrapped around the body | `cyan`, `green` (水色・緑) | トップは水色と緑に見えます。 |
| 50(ナカバ) | 5 | large cat ears | `cyan` (水色) | 猫耳の色は水色に見えます。 |
| 50(ナカバ) | 8 | mint-colored hooded top wrapped around the waist | `cyan`, `green` (水色・緑) | 腰周りのトップは水色と緑に見えます。 |
| 51(イソイチ) | 2 | left collar, around the neck / light color / Roman nume | `green` (緑) | 襟周りが緑色に塗られている。 |
| 51(イソイチ) | 3 | #EarShapeType_Fox | `orange`, `white` (橙・白) | 耳がオレンジと白色に塗られている。 |
| 52(イツギ) | 3 | #EarShapeType_Fox | `white` (白) | 耳の内側は白色です。 |
| 53(イツゾウ) | 2 | #EarShapeType_Fox | `yellow`, `orange` (黄・橙) | 耳は黄色とオレンジで塗られている。 |
| 55(イソゴ) | 3 | #EarShapeType_Fox | `white` (白) | 耳が白く塗られています。 |
| 55(イソゴ) | 5 | #EarShapeType_Fox | `white` (白) | 耳が白く塗られています。 |
| 56(イソロク) | 3 | #EarShapeType_Fox | `gray` (灰) | 耳は灰色です。 |
| 57(イズナ) | 3 | #EarShapeType_Fox | `yellow` (黄) | 耳は黄色で塗られています。 |
| 57(イズナ) | 11 | armband with number on right shoulder | `yellow` (黄) | 右肩の腕章には黄色が使われています。 |
| 58(イソヤ) | 2 | #EarShapeType_Fox | `brown`, `white` (茶・白) | 耳は褐色と白色で塗られています。 |
| 60(ムソウ) | 2 | #EarShapeType_Fox | `white` (白) | 耳の内側は白く塗られているため |
| 60(ムソウ) | 5 | elegant and beautiful face / emotional and straightforw | `pink` (桃) | 顔全体に桃色が使用されているため |
| 61(ロクイチ) 61(ロイ) | 3 | #EarShapeType_Fox | `pink` (桃) | 耳の色はピンクに塗られているため |
| 61(ロクイチ) 61(ロイ) | 5 | heart and key motif | `cyan`, `pink` (水色・桃) | ハートとキーのモチーフは水色とピンクで構成されているため |
| 61(ロクイチ) 61(ロイ) | 6 | heart and key motif charm hairpin (idol outfit) | `cyan`, `pink` (水色・桃) | アイドル衣装のチャーム付きヘアピンは水色とピンクで構成されているため |
| 62(ロジ) | 2 | #EarShapeType_Fox | `white` (白) | 狐の耳の内側は白色です。 |
| 62(ロジ) | 7 | light-colored boots | `orange` (橙) | ブーツはオレンジ色です。 |
| 62(ロジ) | 8 | armband (with number on left shoulder) | `orange`, `white` (橙・白) | 腕章はオレンジ色で、文字が白色です。 |
| 63(ムツミ) | 2 | Center of the belt on the base wear / dark / Arabic num | `black` (黒) | ベースウェアのベルト中央の数字は黒色。 |
| 63(ムツミ) | 3 | #EarShapeType_Fox | `orange` (橙) | 狐耳はオレンジ色で描かれている。 |
| 63(ムツミ) | 6 | victorian lolita dress | `orange`, `pink`, `white` (橙・桃・白) | ビクトリアン・ロリータドレスは主にオレンジ、ピンク、白色が使われている。 |
| 63(ムツミ) | 10 | gentle, maternal smile | `pink` (桃) | 優しく母性的な微笑みがピンク色のチークで表現されている。 |
| 64(ムトシ) | 2 | on the left collar, near the edge of the fabric, small  | `black` (黒) | 左側襟の付近に『64』のアラビア数字が黒で小さく描かれているため。 |
| 64(ムトシ) | 3 | #EarShapeType_Fox | `pink` (桃) | 耳の形状はキツネのようで、ピンクの色が主体のため。 |
| 64(ムトシ) | 6 | inviting smile | `pink` (桃) | キャラクターの微笑む表情がピンクの頬と組み合わさり、招待するような印象を与えるため。 |
| 65(ロクゴ) | 3 | #EarShapeType_Fox | `white`, `gray` (白・灰) | 耳は白と灰色で塗られている。 |
| 66(ムロク) | 1 | On the yoke bib, one digit on each side / dark color /  | `red` (赤) | ヨーク部分の数字は赤で描かれています。 |
| 66(ムロク) | 2 | On the collar, one digit on each side / dark color / Ar | `red` (赤) | 襟部分の数字は赤で描かれています。 |
| 66(ムロク) | 3 | #EarShapeType_Fox | `yellow` (黄) | 耳部分は黄色で描かれています。 |
| 67(ムナ) | 3 | #EarShapeType_Fox | `blue` (青) | 耳が青色に見えるため。 |
| 67(ムナ) | 3 | #EarShapeType_Fox | `blue` (青) | 耳が青色に見えるため。 |
| 67(ムナ) | 9 | slightly darker skin tone | `brown` (茶) | 肌の色が茶色に見えるため。 |
| 67(ムナ) | 10 | muscular physique (in Muscle Mode) | `brown` (茶) | 筋肉モードの肌の色が茶色に見えるため。 |
| 68(ロクヤ) | 1 | on the right side of the bandana / dark / Arabic numera | `black` (黒) | バンダナの右側にある '68' の数字は黒で描かれています。 |
| 68(ロクヤ) | 2 | on the right side of the bandana (normal outfit) / dark | `black` (黒) | 通常の服装のバンダナにある '68' の数字は黒で描かれています。 |
| 68(ロクヤ) | 3 | #EarShapeType_Fox | `green` (緑) | 耳は緑色で描かれています。 |
| 69(ロック) | 3 | On the center of the forehead of the mask, slightly sma | `pink` (桃) | マスクの中央にある数字はピンク色です。 |
| 69(ロック) | 4 | #EarShapeType_Fox | `pink` (桃) | キツネの耳はピンク色です。 |
| 69(ロック) | 6 | earrings | `pink` (桃) | イヤリングはピンク色です。 |
| 69(ロック) | 13 | mask with number markings (sometimes worn) | `pink` (桃) | マスクの数字マーキングはピンク色です。 |
| 70(ナナト) | 3 | #EarShapeType_Fox | `purple`, `white` (紫・白) | 耳は紫と白に塗られている。 |
| 71(ナナヒ) | 2 | #EarShapeType_Fox | `white`, `blue` (白・青) | 耳の外側は青で内側は白色です。 |
| 72(ナフタ) | 3 | #EarShapeType_Fox | `white` (白) | 耳の内側が白色で塗られています。 |
| 72(ナフタ) | 9 | '研修' (trainee) name tag | `black` (黒) | 名札の文字が黒色で塗られています。 |
| 72(ナフタ) | 10 | barcode-style numbered tag | `black` (黒) | バーコードのデザインが黒色で塗られています。 |
| 73(ナトミ) | 2 | #EarShapeType_Fox | `white` (白) | 狼の耳形状は画像で白に塗られている |
| 74(ナナヨ) | 2 | #EarShapeType_Fox | `gray` (灰) | 狐耳の部分は灰色で塗られています |
| 75(シチゴ) | 3 | #EarShapeType_Fox | `yellow` (黄) | 耳が黄色に塗られています。 |
| 75(シチゴ) | 11 | left shoulder armband | `yellow` (黄) | 左肩のアームバンドが黄色です。 |
| 76(シチロク) | 4 | #EarShapeType_Fox | `white` (白) | 耳の内側が白色に塗られている。 |
| 77(ナヅナ) | 3 | #EarShapeType_Fox | `white`, `cyan` (白・水色) | 耳の外側が白で、内側が水色です。 |
| 78(ナナハ) | 1 | The heart pattern on the ears is inspired by Arabic num | `pink` (桃) | 耳のハート模様は桃色です。 |
| 78(ナナハ) | 3 | diamond and heart-patterned ear markings | `pink` (桃) | 耳のダイヤとハート模様は桃色です。 |
| 80(ヤソ) | 3 | #EarShapeType_Fox | `orange`, `white` (橙・白) | 耳は橙色と白で塗られています。 |
| 80(ヤソ) | 6 | curl bob hair with a figure-eight-shaped outline | `orange`, `yellow` (橙・黄) | 髪はオレンジと黄色で色付けされています。 |
| 80(ヤソ) | 7 | restless, hysterical expression | `orange` (橙) | 表情はイラスト全体の色調に溶け込んでおり、オレンジ主体です。 |
| 80(ヤソ) | 8 | subcontractor engineer style | `orange`, `brown` (橙・茶) | エンジニアスタイルはオレンジと茶色の服装から感じ取れます。 |
| 81(ヤイチ) | 3 | #EarShapeType_Fox | `white` (白) | 耳が白く塗られています。 |
| 81(ヤイチ) | 7 | horizontal line pattern on the cheeks | `red orange` (朱) | 頬のラインが朱色です。 |
| 84(ヤツヨ) | 3 | #EarShapeType_Fox | `black`, `white` (黒・白) | 耳は黒と白で塗られています。 |
| 84(ヤツヨ) | 4 | left ear accessory | `yellow` (黄) | 左耳のアクセサリーは黄色です。 |
| 85(ハッコ) 85(パコ) | 2 | #EarShapeType_Fox | `brown`, `white` (茶・白) | 耳が特徴的な形をしており、主に茶色と白で塗られています。 |
| 86(ハチロ) | 1 | on the top area of the bandana worn on the right ear /  | `red` (赤) | 右耳に着用されたバンダナの上部に赤で'86'と書かれています。 |
| 86(ハチロ) | 2 | on the top area of the bandana worn on the right ear (n | `red` (赤) | 右耳に着用された通常の衣装バンダナの上部に赤で'86'と書かれています。 |
| 86(ハチロ) | 3 | #EarShapeType_Fox | `green` (緑) | 耳は緑色で、キツネの形をしています。 |
| 87(ヤシナ) 87(ハナ) | 1 | The heart pattern on the ears is inspired by Arabic num | `blue`, `pink` (青・桃) | 耳のハートパターンは青とピンクで塗られている。 |
| 87(ヤシナ) 87(ハナ) | 2 | #EarShapeType_Fox | `pink`, `white` (桃・白) | 狐の耳はピンクと白の組み合わせで描かれている。 |
| 87(ヤシナ) 87(ハナ) | 3 | diamond and heart-patterned ear markings | `blue`, `pink` (青・桃) | 耳のダイヤとハートの模様は青とピンクで塗られている。 |
| 87(ヤシナ) 87(ハナ) | 8 | heart-shaped diamond pendant necklace | `blue`, `orange` (青・橙) | ハート型のダイヤモンドペンダントは青とオレンジで描かれている。 |
| 88(ヤソハチ) | 2 | #EarShapeType_Fox | `white` (白) | 耳が白色で塗られているため |
| 88(ヤソハチ) | 3 | left ear accessory | `red`, `white` (赤・白) | 左耳のアクセサリーが赤と白で構成されているため |
| 88(ヤソハチ) | 7 | piano-keyboard holographic ring | `white`, `blue` (白・青) | ピアノキーボードのホログラムが白と青で塗られているため |
| 89(ヤスモ) | 3 | #EarShapeType_Fox | `white` (白) | 耳の内側が白で塗られています。 |
| 92(コトジ) | 1 | #EarShapeType_Fox | `blue` (青) | 画像の耳は青色です |
| 93(クミ) | 1 | Slightly large, centered on the front of the sphere at  | `black` (黒) | 数字'93'は黒で表示されています。 |
| 93(クミ) | 2 | Prominently across the entire supporter visible from th | `black` (黒) | 数字'93'は黒で表示されています。 |
| 93(クミ) | 7 | belt supporter with number design at the waist | `yellow`, `white` (黄・白) | サポーターは黄色と白で構成されています。 |
| 94(ツクシ) | 3 | #EarShapeType_Fox | `white` (白) | 耳の内側が白く塗られています。 |
| 96(クルリ) | 2 | On the center of the forehead of the mask, slightly sma | `pink` (桃) | マスクの中央にある '96' の数字はピンクで描かれています。 |
| 96(クルリ) | 3 | #EarShapeType_Fox | `white` (白) | 耳が白く描かれています。 |
| 96(クルリ) | 10 | high heels (casual wear) | `red` (赤) | ハイヒールが赤色で描かれています。 |
| 97(ココナ) | 3 | #EarShapeType_Fox | `white` (白) | 耳は白く塗られています。 |
| 98(キュウヤ) | 3 | #EarShapeType_Fox | `white` (白) | 耳の内側が白色で塗られています。 |
| 99(ツクモ) | 3 | #EarShapeType_Fox | `red`, `white` (赤・白) | 耳は赤と白で構成されています。 |
| 99(ツクモ) | 7 | fox-like ears and tail-tufts pattern | `gray`, `red`, `white` (灰・赤・白) | 狐の尾は灰色、赤、白で描かれています。 |
| 99(ツクモ) | 9 | choker with kanji numerals | `pink`, `purple` (桃・紫) | チョーカーの漢数字はピンクがかった紫で描かれています。 |
| バイナ 2(ツギ) | 2 | on the left collar, slightly smaller / dark / Arabic nu | `black` (黒) | 左の襟にあるアラビア数字の『2』は黒で書かれている。 |
| バイナ 2(ツギ) | 3 | #EarShapeType_Fox | `gray`, `white` (灰・白) | 耳は灰色と白色で狐のような形をしている。 |
| バイナ 2(ツギ) | 10 | holographic body (prototype state) | `gray`, `white`, `orange` (灰・白・橙) | ホログラフィックの体は灰色と白色で、プロトタイプ状態であることを示すオレンジのアクセントが |
| ディケ 10(ツナイ) | 1 | On the left chest of the front of the full-body cover o | `yellow` (黄) | 警告ラベルの色が黄色である |
| ディケ 10(ツナイ) | 2 | #EarShapeType_Fox | `brown` (茶) | 耳の色が茶色である |
| ディケ 10(ツナイ) | 10 | '取扱注意' (handle with care) caution label (on base) | `yellow` (黄) | 警告ラベルの色が黄色である |
| 000(チトセ) | 3 | #EarShapeType_Cat | `white`, `gray` (白・灰) | 耳は白と灰色に塗られています。 |
| 零 零 | 3 | cat ear accessories | `yellow`, `white` (黄・白) | 猫耳アクセサリーは黄色と内側に白が使われている。 |
| 零 百 | 3 | cat ear accessories | `cyan` (水色) | 猫耳アクセサリーがシアン色に塗られています。 |
| 100(モモ) | 2 | #EarShapeType_Fox | `white` (白) | 耳が白く塗られている。 |
| 100(モモ) | 5 | An expression like that of a head nurse who has support | `red` (赤) | 目が赤く塗られている。 |
| 111(アイズ) | 2 | #EarShapeType_Cat | `yellow` (黄) | 耳が黄色に塗られています。 |
| 222(ペルゲン) | 2 | #EarShapeType_Fox | `orange`, `pink` (橙・桃) | 耳の内側が明るい橙色と桃色で塗られているため。 |
| 222(ペルゲン) | 5 | long pale-colored twin-tail hairstyle | `white`, `gray` (白・灰) | 髪が白っぽいグレーで塗られているため。 |
| 222(ペルゲン) | 6 | pale-colored collar | `white`, `gray` (白・灰) | 襟が淡い色合いの白と灰色で塗られているため。 |
| 222(ペルゲン) | 7 | pendant featuring three '2's and a heart motif | `pink`, `red` (桃・赤) | ペンダントが桃色と赤で塗られているため。 |
| 222(ドッペル) | 2 | #EarShapeType_Fox | `white` (白) | 耳は白色に見えるため。 |
| 222(ドッペル) | 5 | long pale-colored twin-tail hairstyle | `white` (白) | 髪は白色に見えるため。 |
| 222(ドッペル) | 6 | pale-colored collar | `white` (白) | 襟は白色に見えるため。 |
| 222(ドッペル) | 7 | pendant featuring three '2's and a heart motif | `orange`, `yellow` (橙・黄) | ペンダントのハート部分はオレンジと黄色の組み合わせに見えるため。 |
| 444(シテン) | 3 | #EarShapeType_Fox | `white`, `cyan` (白・水色) | 耳は白と水色が基調です。 |
| 444(シテン) | 7 | halo consisting of three squares/diamonds | `yellow`, `orange` (黄・橙) | ハローは黄色とオレンジで構成されています。 |
| 666(リリス) | 2 | #EarShapeType_Fox | `pink` (桃) | 耳はピンクに塗られています。 |
| 666(リリス) | 5 | halo with three '6's arranged in rotational symmetry (w | `pink` (桃) | 光輪はピンクに塗られています。 |
| 666(リリス) | 6 | wings inspired by the motif of '666' (with heart-shaped | `pink` (桃) | 翼はピンクに塗られています。 |
| 666(リリス) | 8 | brooch with three '6's arranged in rotational symmetry  | `pink` (桃) | ブローチはピンクに塗られています。 |
| 666(リリス) | 10 | brooch with three '6's arranged in rotational symmetry  | `pink` (桃) | ブローチはピンクに塗られています。 |
| 777(ヨロコビ) | 2 | #EarShapeType_Cat | `white` (白) | 耳は白色に塗られている。 |
| 777(ヨロコビ) | 4 | cheerful and bright expressions | `orange`, `blue` (橙・青) | 表情はオレンジと青の色調で表現されている。 |
| 777(ヨロコビ) | 5 | holding a cocoa cigarette bar in the mouth | `brown` (茶) | 口に加えられているココアシガレットバーは茶色である。 |
| 777(ヨロコビ) | 2 | #EarShapeType_Cat | `white` (白) | 耳は白色に塗られている。 |
| 777(ヨロコビ) | 4 | cheerful and bright expressions | `orange`, `blue` (橙・青) | 表情はオレンジと青の色調で表現されている。 |
| 777(ヨロコビ) | 5 | holding a cocoa cigarette bar in the mouth | `brown` (茶) | 口に加えられているココアシガレットバーは茶色である。 |
| 888(ムゲン) | 2 | EarShapeType_Wing | `orange` (橙) | 耳はオレンジ色で描かれています。 |
| トレッド 3×11(トリィレブン) | 1 | around the edge of the fabric on the left hem of the ca | `cyan` (水色) | ケープの左裾にあるアラビア数字 '33'は明るいシアン色で書かれています。 |
| 量産型 111(アイズ) | 3 | #EarShapeType_Cat | `yellow` (黄) | 耳は淡い桃色で、猫の形をしているため。 |
| 量産型 444(シテン) | 4 | #EarShapeType_Fox | `white` (白) | 耳は白に塗られているため |
| 量産型 444(シテン) | 8 | halo consisting of three squares/diamonds | `blue`, `gray` (青・灰) | 三つの四角形の円環は青と灰色に塗られているため |
| 量産型 666(リリス) | 3 | #EarShapeType_Fox | `pink` (桃) | 耳はピンク色で塗られている。 |
| 量産型 666(リリス) | 6 | halo with three '6's arranged in rotational symmetry | `pink` (桃) | 輪の色はピンク色。 |
| 量産型 666(リリス) | 7 | wings inspired by the motif of '666' | `pink` (桃) | 翼の色はピンク色。 |
| 量産型 666(リリス) | 9 | brooch with three '6's arranged in rotational symmetry  | `purple`, `pink` (紫・桃) | ブローチは紫とピンク色で構成されている。 |
| 量産型 666(リリス) | 11 | brooch with three '6's arranged in rotational symmetry  | `purple`, `pink` (紫・桃) | ブローチは紫とピンク色で構成されている。 |
| 量産型 777(ヨロコビ) | 3 | #EarShapeType_Cat | `white` (白) | 耳が白に塗られているため。 |
| 量産型 777(ヨロコビ) | 6 | holding a cocoa cigarette bar in the mouth | `brown` (茶) | ココアシガレットバーが茶色に塗られているため。 |
| 量産型 777(ヨロコビ) | 3 | #EarShapeType_Cat | `white` (白) | 耳が白に塗られているため。 |
| 量産型 777(ヨロコビ) | 6 | holding a cocoa cigarette bar in the mouth | `brown` (茶) | ココアシガレットバーが茶色に塗られているため。 |

### 創作 DB に無い配色（実測 HEX・45 件）

公式の透過イラスト（`$palette.source: artwork`）から**実測**した色のうち、
`ColorPalette` のどの HEX とも一致しないもの（色距離 10 以内を同じ色とみなす）。
抽出条件は上流 `patch-colorpalette.mjs --from-artwork` と同じで、共通造形色は除外済み。
**部位と記述案は画像から読み取ったもの**で、`AppliesTo` と `Attrs` の両方へそのまま書ける。

| キャラ | 実測 HEX | 面積比 | 使用部位（画像から） | `Attrs` 記述案 | 根拠 |
|---|---|---|---|---|---|
| 2(ツグ) | `#F4C5A8` | 7.0% | `#BodyPart_Hair` (髪) | pale hair highlight | 髪のハイライト部分に使用されている色です。 |
| 8(ワカツ) | `#FF6574` | 2.1% | `#BodyPart_Tail` (尻尾) | pink fur highlight | 尻尾の色がこの色です。 |
| 16(ソロク) | `#F4FAE8` | 26.0% | `#BodyPart_FaceMaking` (フェイスメイク) | light shading on the face | 顔のハイライトやシェーディングに使われています。 |
| 16(ソロク) | `#FF7297` | 2.6% | `#BodyPart_Hair` (髪) | pink hair color | 髪の色として使われています。 |
| 17(トナ) | `#6B8CC5` | 2.3% | `#BodyPart_Hair` (髪) | blue hair color | 髪の色が青色に塗られています |
| 18(トウヤ) | `#612C26` | 2.5% | `#BodyPart_Tail` (尻尾), `#BodyPart_Ear` (耳) | dark brown on tail and ears | しっぽと耳に濃い茶色が使われている。 |
| 23(ツグミ) | `#EFF5ED` | 8.7% | `#BodyPart_Cheek` (頬) | cheek highlight | 頬のハイライト部分に使用されています。 |
| 23(ツグミ) | `#8DC0AB` | 2.0% | `#BodyPart_Hair` (髪) | hair color | 髪の色に使用されています。 |
| 26(ニロク) | `#DEA2A7` | 2.3% | `#BodyPart_Eye` (目・瞳) | eye color | ピンク色は目の色として使用されています。 |
| 28(ニハチ) | `#FFB879` | 2.3% | `#BodyPart_Tail` (尻尾) | bright orange tail | しっぽに明るいオレンジ色が使われています。 |
| 30(ミツト) | `#E4BC75` | 2.8% | `#BodyPart_Hair` (髪), `#BodyPart_Ear` (耳) | light brown hair and ear | 髪と耳に使用されている色。 |
| 32(ミツギ) | `#EFF5ED` | 11.1% | `#BodyPart_Ear` (耳) | inner ear highlight | 耳の内側のハイライトとして使われています。 |
| 32(ミツギ) | `#A7D9C4` | 2.8% | `#BodyPart_Hair` (髪), `#BodyPart_Tail` (尻尾) | mint color for hair and tail | 髪と尻尾にミント色として使用されています。 |
| 35(サトコ) 35(ミコ) | `#FAF9E8` | 4.1% | `#BodyPart_Hand` (手) | pale skin tone | 肌の淡い色合いです。 |
| 41(ヨソイチ) | `#80A8CC` | 3.2% | `#BodyPart_Tail` (尻尾) | tail color | 尻尾にこの色が使われています。 |
| 43(シトミ) | `#1D659C` | 2.4% | `#BodyPart_Hair` (髪) | dark blue hair | 髪の部分に暗い青色が使われています。 |
| 45(シゴ) | `#4E5C80` | 2.5% | `#BodyPart_Hair` (髪) | dark blue hair | 髪の暗い青色として使用されています。 |
| 45(シゴ) | `#273654` | 2.3% | `#BodyPart_Tail` (尻尾) | dark blue tail | 尻尾の暗い青色として使用されています。 |
| 47(シナ) | `#708292` | 2.4% | `#BodyPart_Hair` (髪) | grayish blue hair | 髪が青みがかった灰色に塗られている。 |
| 48(シハチ) | `#848A6F` | 2.4% | `#BodyPart_Hair` (髪) | grayish green hair | 髪の色がこの灰緑色に塗られています。 |
| 53(イツゾウ) | `#FAF9E8` | 6.6% | `#BodyPart_Ear` (耳) | inner ear | 耳の内側に使われている。 |
| 53(イツゾウ) | `#E4AD5C` | 2.2% | `#BodyPart_Hair` (髪) | main hair color | 髪のメインカラーに使われている。 |
| 57(イズナ) | `#FFFF6B` | 2.1% | `#BodyPart_Hair` (髪), `#BodyPart_Tail` (尻尾) | hair and tail color | 髪と尾に明るい黄色が使われています。 |
| 60(ムソウ) | `#E47693` | 2.3% | `#BodyPart_Cheek` (頬) | pink blush on the cheeks | 頬に桃色のチークが入っている |
| 61(ロクイチ) 61(ロイ) | `#E85764` | 18.0% | `#BodyPart_Hair` (髪) | hair accents | 髪の一部に使われている色 |
| 61(ロクイチ) 61(ロイ) | `#F4FAE8` | 2.8% | `#BodyPart_Neck` (首) | collar and neck area | 襟と首の部分に使われている色 |
| 61(ロクイチ) 61(ロイ) | `#FF769C` | 2.1% | `#BodyPart_Hair` (髪) | hair color | 髪全体に塗られている色 |
| 66(ムロク) | `#FCC7CC` | 3.6% | `#BodyPart_Hair` (髪) | pale pink hair color | 髪の色として使用されています。 |
| 66(ムロク) | `#FCCFD3` | 2.1% | `#BodyPart_Tail` (尻尾) | pale pink tail color | 尻尾の色として使用されています。 |
| 69(ロック) | `#EDD2DA` | 9.0% | `#BodyPart_FaceMaking` (フェイスメイク) | soft pink blush | 頬に使われている柔らかいピンク色のフェイスメイクです。 |
| 69(ロック) | `#C96C9C` | 2.3% | `#BodyPart_Hair` (髪) | vibrant pink hair | 髪に使われている鮮やかなピンク色です。 |
| 73(ナトミ) | `#E58E81` | 2.1% | `#BodyPart_Cheek` (頬) | cheek blush | 頬の部分に使われている |
| 74(ナナヨ) | `#ABB4BC` | 2.2% | `#BodyPart_Tail` (尻尾) | tail shading | 尻尾の影に使われています |
| 75(シチゴ) | `#E0D144` | 2.1% | `#BodyPart_Hair` (髪), `#BodyPart_Tail` (尻尾) | yellow hair and tail | 髪と尻尾がこの黄色に塗られています。 |
| 76(シチロク) | `#E1E4E6` | 6.6% | `#BodyPart_Ear` (耳) | inner ear color | 耳の内側の色として使用。 |
| 81(ヤイチ) | `#612C26` | 2.5% | `#BodyPart_Hair` (髪) | dark hair color | 髪の暗い部分に用いられています。 |
| 88(ヤソハチ) | `#FFE8D7` | 4.7% | `#BodyPart_Cheek` (頬) | light peach cheek | 頬の明るい桃色で使用されている |
| 92(コトジ) | `#8398C1` | 3.2% | `#BodyPart_Hair` (髪) | soft blue hair | 髪にこの色が使われています |
| 93(クミ) | `#FCFCE8` | 2.6% | `#BodyPart_Waist` (腰) | highlight on the waist | ウエスト部分に明るい色が使用されています。 |
| 000(チトセ) | `#9CA4A9` | 2.1% | `#BodyPart_Hair` (髪), `#BodyPart_Tail` (尻尾) | gray hair and tail | 髪と尻尾に灰色が使われています。 |
| 444(シテン) | `#A4DAEF` | 6.3% | `#BodyPart_Hair` (髪), `#BodyPart_Tail` (尻尾) | light blue hair and tail | 髪と尻尾にこの色が使われています。 |
| 444(シテン) | `#EDE8DE` | 4.7% | `#BodyPart_Ear` (耳) | pale inner ear | 耳の内側にこの色が使われています。 |
| 666(リリス) | `#BA5B81` | 2.8% | `#BodyPart_Hair` (髪) | hair colored in dark pink | 髪がこの色に塗られています。 |
| トレッド 3×11(トリィレブン) | `#FFFF82` | 2.9% | `#BodyPart_Foot` (足) | yellow shade on the foot | この色は足の部分の陰影に使われています。 |
| 量産型 444(シテン) | `#A4DAEF` | 6.3% | `#BodyPart_Hair` (髪), `#BodyPart_Tail` (尻尾) | light blue hair and tail | 髪と尻尾の色 |

### 実測はされたが配色ではないと判定した色（10 件）

画像照合で輪郭線・紙面・背景などと判定されたもの。上流の純黒除外は彩度条件付き
（濃い有彩色を守るため）なので `#010000` のような線画色がすり抜けることがある。
参考として残すので、`ColorPalette` へ入れる必要はないはず。

| キャラ | 実測 HEX | 面積比 | 判定理由 |
|---|---|---|---|
| 4(モチ) | `#010000` | 8.0% | 輪郭線の黒 |
| 5(イズ) | `#E6F2F1` | 6.4% | 背景色やハイライトに使用されている。 |
| 20(ハツカ) | `#F4FAE8` | 7.6% | これは背景や非特定の塗りつぶしに使用されています。 |
| 21(ハツヒ) | `#F3F1EE` | 5.0% | 背景の色です。 |
| 60(ムソウ) | `#FFF1F0` | 8.3% | 体の一部に白い色が使用されている |
| 66(ムロク) | `#FDDCDF` | 2.9% | 甲羅の色として使用されています。 |
| 72(ナフタ) | `#81A8CC` | 2.8% | キャラクターの体と尻尾は明るい青色で塗られています。 |
| 74(ナナヨ) | `#E9F2FB` | 3.8% | 衣装のアクセント部分に使用されています |
| 222(ペルゲン) | `#010000` | 7.1% | 輪郭線の黒のため。 |
| 量産型 444(シテン) | `#EDE8DE` | 4.7% | 背景色であるため |

### ColorPalette に見当たらない色（84 件）

画像から読み取れたのに、`ColorPalette` のどの HEX も該当しない色。
**配色検知の取りこぼし候補**（抽出漏れ、または面積比の下限で落ちたもの）。
共通造形色に該当する色（`red orange`, `white`）は設計上 `ColorPalette` へ載らないため除外済み。

| キャラ | 画像から読めた色 | 現在の ColorPalette |
|---|---|---|
| 1(ハジメ) | `orange` (橙) | `#ED5D47`, `#FF8682`, `#FFAC8F`, `#E55951`, `#C9CDCB`, `#CEC7B6`, `#FFBFA7` |
| 3(ナオ) | `black` (黒) | `#F8EC72`, `#FFCE2B`, `#FFEE60`, `#F7FFB9`, `#FFBC08`, `#FFBE0E` |
| 7(ナナ) | `black` (黒) | `#5E7AA9`, `#457AC4`, `#C6C4DD`, `#515271`, `#4447A4` |
| 7(ナナ) | `purple` (紫) | `#5E7AA9`, `#457AC4`, `#C6C4DD`, `#515271`, `#4447A4` |
| 8(ワカツ) | `brown` (茶) | `#E85764`, `#FF9E68`, `#FFA9A8`, `#FC6932`, `#BC4655` |
| 9(チカ) | `black` (黒) | `#A1A9BF`, `#484551`, `#5F676F`, `#767B7D`, `#D2D7E7`, `#445465`, `#B2AFCF`, `#A5ADC2` |
| 9(チカ) | `cyan` (水色) | `#A1A9BF`, `#484551`, `#5F676F`, `#767B7D`, `#D2D7E7`, `#445465`, `#B2AFCF`, `#A5ADC2` |
| 10(ミツル) | `pink` (桃) | `#E85764`, `#81494A`, `#F3DCDF`, `#BB3E45`, `#BE4C5A`, `#BD4756` |
| 11(トウイチ) | `blue` (青) | `#BBC6CB`, `#8B9BAC`, `#BB3E45`, `#C2CCD0`, `#FFAC8F`, `#C6CCD8`, `#E7ECE9` |
| 13(トミ) | `pink` (桃) | `#99D0D7`, `#B7DEEC`, `#F76D67`, `#94CDD5`, `#FFF13A`, `#5C9ABC` |
| 14(トヨ) | `pink` (桃) | `#9BC1E6`, `#FFC5BC`, `#4CD9E8`, `#E75E5A`, `#00939F` |
| 15(トウゴ) | `orange` (橙) | `#FFB1AB`, `#589D74`, `#FFC4A6`, `#E8EDBE`, `#E85764`, `#FFD7C9` |
| 15(トウゴ) | `pink` (桃) | `#FFB1AB`, `#589D74`, `#FFC4A6`, `#E8EDBE`, `#E85764`, `#FFD7C9` |
| 16(ソロク) | `pink` (桃) | `#F26383`, `#6A88C2`, `#A4A2C3`, `#F9BBC1`, `#E25970` |
| 17(トナ) | `gray` (灰) | `#9DB0DB`, `#5B77A8`, `#F76D67`, `#938FAD`, `#B2B0CF` |
| 17(トナ) | `yellow` (黄) | `#9DB0DB`, `#5B77A8`, `#F76D67`, `#938FAD`, `#B2B0CF` |
| 18(トウヤ) | `brown` (茶) | `#7C4540`, `#ED5D47`, `#D46E87`, `#FFAC8F`, `#F9642D` |
| 18(トウヤ) | `orange` (橙) | `#7C4540`, `#ED5D47`, `#D46E87`, `#FFAC8F`, `#F9642D` |
| 18(トウヤ) | `pink` (桃) | `#7C4540`, `#ED5D47`, `#D46E87`, `#FFAC8F`, `#F9642D` |
| 20(ハツカ) | `black` (黒) | `#FFA457`, `#AEB4B4`, `#FFC4A3`, `#FFDCAE`, `#B3B9B9`, `#EAE5D6`, `#CBCECD`, `#E9EBE5` |
| 20(ハツカ) | `pink` (桃) | `#FFA457`, `#AEB4B4`, `#FFC4A3`, `#FFDCAE`, `#B3B9B9`, `#EAE5D6`, `#CBCECD`, `#E9EBE5` |
| 21(ハツヒ) | `black` (黒) | `#FFAC8F`, `#FFEFE3`, `#FFD7C2`, `#FEF3D9`, `#FECF7D` |
| 22(フジ) | `yellow` (黄) | `#FFC879`, `#ABB1B1`, `#FFD07D`, `#CACDCB`, `#FFB42B`, `#FFCD86`, `#FFF4E3` |
| 25(フィズ) | `blue` (青) | `#A2AFB8`, `#175D7E`, `#7EAEAB`, `#688B8A`, `#D3DBDC`, `#628786` |
| 25(フィズ) | `green` (緑) | `#A2AFB8`, `#175D7E`, `#7EAEAB`, `#688B8A`, `#D3DBDC`, `#628786` |
| 27(ツギナ) | `cyan` (水色) | `#E2EBEF`, `#9BC1E6`, `#736E9A`, `#A4A2C3`, `#EFEFEE` |
| 27(ツギナ) | `purple` (紫) | `#E2EBEF`, `#9BC1E6`, `#736E9A`, `#A4A2C3`, `#EFEFEE` |
| 28(ニハチ) | `black` (黒) | `#DB653F`, `#F4F1E5`, `#FF9E68`, `#FFD59B`, `#FFC4A3` |
| 29(ニトク) | `purple` (紫) | `#E1DBCC`, `#9DB0DB`, `#B2B0CE`, `#CEC7B6`, `#D9D8E6` |
| 31(ミツイ) | `black` (黒) | `#94CDD5`, `#F56D67`, `#5C9ABC`, `#B7DEEC`, `#FFF13A` |
| 32(ミツギ) | `black` (黒) | `#C2F2DE`, `#B2DDA7`, `#7BDEC1`, `#FAFE9D`, `#FFF000` |
| 32(ミツギ) | `cyan` (水色) | `#C2F2DE`, `#B2DDA7`, `#7BDEC1`, `#FAFE9D`, `#FFF000` |
| 33(ミサ) | `orange` (橙) | `#FFA79B`, `#FFD5BD`, `#FFBDA7`, `#FFDECA`, `#FFD9C4`, `#FFE5CE`, `#FFF7F3`, `#FF8FAD` |
| 34(サトシ) サンジ | `black` (黒) | `#387EB6`, `#405AB9`, `#A5AFB5`, `#FFCE2B`, `#CACDCC`, `#A4DAEF`, `#4989BC` |
| 36(ミトム) | `black` (黒) | `#FFD58F`, `#FFA79B`, `#FFC4A3`, `#A95C8D`, `#FFA634` |
| 36(ミトム) | `purple` (紫) | `#FFD58F`, `#FFA79B`, `#FFC4A3`, `#A95C8D`, `#FFA634` |
| 36(ミトム) | `yellow` (黄) | `#FFD58F`, `#FFA79B`, `#FFC4A3`, `#A95C8D`, `#FFA634` |
| 37(サナ) | `yellow` (黄) | `#FFA79B`, `#9DB0DB`, `#FF8682`, `#E75E5A`, `#FFD47A` |
| 39(サク) | `black` (黒) | `#C1A072`, `#9A6A4E`, `#FFF4DF`, `#FFD07D`, `#F6FFD2` |
| 42(ヨツグ) | `orange` (橙) | `#E8AFD8`, `#AEB8DB`, `#FCE8EC`, `#EAB5DB`, `#C77FAF`, `#0097C9` |
| 42(ヨツグ) | `red` (赤) | `#E8AFD8`, `#AEB8DB`, `#FCE8EC`, `#EAB5DB`, `#C77FAF`, `#0097C9` |
| 44(シトシ) | `black` (黒) | `#B1AA6B`, `#F1E8D4`, `#EEC694`, `#7EAEAB`, `#A4DAEF`, `#FFA457`, `#B3AD70` |
| 46(シロー) | `black` (黒) | `#387EB6`, `#6AA6D7`, `#CACDCC`, `#B8507C`, `#E55951`, `#F26383` |
| 47(シナ) | `gray` (灰) | `#387EB6`, `#6AA6D7`, `#185EBD`, `#C7CDD8`, `#8B9BAC` |
| 48(シハチ) | `black` (黒) | `#9EA388`, `#7EAEAB`, `#EF9D46`, `#FFBC08`, `#CACDCB`, `#FFD07D` |
| 50(ナカバ) | `black` (黒) | `#3DD4CF`, `#7BDEC1`, `#C2F2DE`, `#009489`, `#DCF8F3` |
| 51(イソイチ) | `orange` (橙) | `#E85764`, `#FFB1AB`, `#E8EDBE`, `#FFD7C9`, `#589D74` |
| 58(イソヤ) | `brown` (茶) | `#CACDCB`, `#85E6EA`, `#EF9D46`, `#C48455`, `#02A1C8`, `#00BACB` |
| 61(ロクイチ) 61(ロイ) | `cyan` (水色) | `#F26383`, `#6A88C2`, `#A4A2C3`, `#F9BBC1`, `#DC576C` |
| 61(ロクイチ) 61(ロイ) | `pink` (桃) | `#F26383`, `#6A88C2`, `#A4A2C3`, `#F9BBC1`, `#DC576C` |
| 62(ロジ) | `orange` (橙) | `#F9BCC1`, `#F4ABB4`, `#DD7C9C`, `#FFA79B`, `#FFE2E9` |
| 63(ムツミ) | `black` (黒) | `#FFD998`, `#FFA79B`, `#FFC4A3`, `#A95C8D`, `#FFD07D`, `#FFA634` |
| 64(ムトシ) | `black` (黒) | `#B8507C`, `#6AA6D7`, `#F26383`, `#387EB6`, `#E55951` |
| 66(ムロク) | `red` (赤) | `#6D7880`, `#FFA634`, `#FFC046`, `#F9BBC0`, `#CC8C8C`, `#FF8FAD` |
| 66(ムロク) | `yellow` (黄) | `#6D7880`, `#FFA634`, `#FFC046`, `#F9BBC0`, `#CC8C8C`, `#FF8FAD` |
| 67(ムナ) | `brown` (茶) | `#FF76A2`, `#9DB0DB`, `#5B77A8`, `#B494A2`, `#0097C9` |
| 67(ムナ) | `brown` (茶) | `#FE76A2`, `#9DB0DB`, `#5B77A8`, `#0097C9`, `#B494A2`, `#AEBEE1` |
| 68(ロクヤ) | `black` (黒) | `#6CBA4B`, `#F1617D`, `#614D4F`, `#B5AD9B`, `#70BC50`, `#5E5E41` |
| 70(ナナト) | `purple` (紫) | `#6B658C`, `#5D6E94`, `#9995B0`, `#5B77A8`, `#504695`, `#9FA7BE` |
| 72(ナフタ) | `black` (黒) | `#9BC1E6`, `#A4A2C3`, `#736F9A`, `#E2EBEE`, `#EFEEEE` |
| 74(ナナヨ) | `gray` (灰) | `#C7CDD8`, `#387EB6`, `#8B9BAC`, `#6AA6D7`, `#185EBD` |
| 80(ヤソ) | `brown` (茶) | `#FF9048`, `#C48455`, `#EEC694`, `#FFC5A3`, `#FC6932`, `#EF9D46` |
| 80(ヤソ) | `yellow` (黄) | `#FF9048`, `#C48455`, `#EEC694`, `#FFC5A3`, `#FC6932`, `#EF9D46` |
| 84(ヤツヨ) | `black` (黒) | `#9EA388`, `#EF9D45`, `#FFD07D`, `#FFBC08`, `#7EAEAB` |
| 85(ハッコ) 85(パコ) | `brown` (茶) | `#EF9D46`, `#85E6EA`, `#00BACB`, `#01A1C8`, `#C48455` |
| 93(クミ) | `black` (黒) | `#FFD07D`, `#FFF5E1`, `#9A6A4E`, `#C1A072`, `#F7FFD3`, `#FFD486`, `#FFD995` |
| 93(クミ) | `yellow` (黄) | `#FFD07D`, `#FFF5E1`, `#9A6A4E`, `#C1A072`, `#F7FFD3`, `#FFD486`, `#FFD995` |
| 99(ツクモ) | `purple` (紫) | `#D1A8CD`, `#4F506F`, `#E3C2DE`, `#6D7881`, `#CACDCC`, `#959A9D`, `#727D85`, `#C84557` |
| バイナ 2(ツギ) | `black` (黒) | `#FFA558`, `#ADB2B2`, `#FFC4A3`, `#FFDCAE`, `#C9CDCB`, `#EBE5D6`, `#E7E9E4` |
| ディケ 10(ツナイ) | `brown` (茶) | `#5F676F`, `#81494A`, `#293B3A`, `#FFCE2B`, `#E85764`, `#F3D8DB` |
| 零 零 | `yellow` (黄) | `#E1DCCD`, `#FF8682`, `#FFD184`, `#ECAC42`, `#E16355`, `#F1F3EE`, `#CEC7B6`, `#FFB0AA` |
| 111(アイズ) | `yellow` (黄) | `#BB3E45`, `#FFAC8F`, `#E7E9E4`, `#CDCCC6`, `#FCBD47`, `#FFD58F` |
| 222(ペルゲン) | `gray` (灰) | `#FFA79B`, `#FFC4B8`, `#EAE5D6`, `#FFF4E6`, `#FFE1C7`, `#F3F1EA`, `#E8E9E3` |
| 222(ペルゲン) | `orange` (橙) | `#FFA79B`, `#FFC4B8`, `#EAE5D6`, `#FFF4E6`, `#FFE1C7`, `#F3F1EA`, `#E8E9E3` |
| 222(ペルゲン) | `pink` (桃) | `#FFA79B`, `#FFC4B8`, `#EAE5D6`, `#FFF4E6`, `#FFE1C7`, `#F3F1EA`, `#E8E9E3` |
| 222(ドッペル) | `yellow` (黄) | `#FFD07D`, `#EAE5D6`, `#FFE2C7`, `#FFF4E4`, `#F7F5EA`, `#E8E9E3` |
| 444(シテン) | `yellow` (黄) | `#FFD47A`, `#94CDD5`, `#ECAC43`, `#C1A072`, `#C9CDCB`, `#020202` |
| 777(ヨロコビ) | `brown` (茶) | `#C1A072`, `#504695`, `#FFA634`, `#8B9BAC`, `#FFD47A`, `#D0B897` |
| 777(ヨロコビ) | `brown` (茶) | `#C1A072`, `#504695`, `#FFA634`, `#8B9BAC`, `#FFD47A` |
| 量産型 111(アイズ) | `yellow` (黄) | `#D75341`, `#FFAC8F`, `#CDCBC5`, `#E7E9E3`, `#FCBD47`, `#FFD58F` |
| 量産型 444(シテン) | `blue` (青) | `#FFD47A`, `#94CDD5`, `#B5AD9C`, `#C1A072`, `#C9CDCB`, `#020202` |
| 量産型 666(リリス) | `purple` (紫) | `#E0B0BC`, `#F26383`, `#C84557`, `#A95D8D`, `#BC8797` |
| 量産型 777(ヨロコビ) | `brown` (茶) | `#C1A072`, `#504695`, `#ECAC42`, `#8B9BAC`, `#FFD47A` |
| 量産型 777(ヨロコビ) | `brown` (茶) | `#C1A072`, `#504695`, `#ECAC42`, `#8B9BAC`, `#FFD47A` |

### 残っている BodyPart 欠落

| キャラ | # | DesignElement | 記述 | 色語 |
|---|---|---|---|---|
| 27(ツギナ) | 9 | `#Element_Motif` | four white buttons | white |
| 47(シナ) | 6 | `#Element_Motif` | navy miko outfit with number | blue |
| 51(イソイチ) | 6 | `#Element_Emblem` | original green casual wear with diagonal patterns | green |
| 55(イソゴ) | 11 | `#Element_Motif` | white inner collar | white |
| 63(ムツミ) | 9 | `#Element_Motif` | orange accents | orange |
| 66(ムロク) | 11 | `#Element_Motif` | yellow trim accents | yellow |
| 67(ムナ) | 6 | `#Element_Motif` | pale reddish-purple trainer wear | purple, red |
| 67(ムナ) | 6 | `#Element_Motif` | pale reddish-purple trainer wear | purple, red |
| 68(ロクヤ) | 10 | `#Element_Motif` | light brown workwear (work outfit) | brown |
| 69(ロック) | 11 | `#Element_Motif` | white buttons | white |
| バイナ 2(ツギ) | 6 | `#Element_Tag` | orange '試用' (trial / test) label | orange |
| バイナ 2(ツギ) | 9 | `#Element_Motif` | amber-orange eyes | orange, yellow |
| ディケ 10(ツナイ) | 9 | `#Element_Motif` | red support pillar (base) | red |
| 000(チトセ) | 10 | `#Element_CostumeItem` | casual suit resembling a white coat | white |
| 777(ヨロコビ) | 7 | `#Element_CostumeItem` | wearing a dark yellow slot machine-type addon and functioning like a slot machine | yellow |
| 量産型 777(ヨロコビ) | 8 | `#Element_CostumeItem` | wearing a dark yellow slot machine-type addon and functioning like a slot machine | yellow |

---

*色語は AI が公式画像から読み取った推定です。DB へ反映する前に確認してください。*
*個別キャラの部位候補は `--num <N> --check coverage` で画像から提案できます。*

自動生成: `python -m src.tools.verify_appearance_detail --all --check coverage --comment 20` (100BeautiesLab_GeneratorsAI)
