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

### 補完案（257 件）

色情報が入っていないエントリについて、画像から読み取った色。
各行の `#` は `AppearanceDetail[]` のインデックス（1 始まり）。
「読めた色」の先頭語を使って、そのエントリの `Attrs` へ次を足すと `AppliesTo` へ転記されるようになる。

```json
{ "AttrLabel": "#DesignAttr_Color", "value_JP": "<日本語>", "value_EN": "<色語>" }
```

| キャラ | # | 記述 | 読めた色 | 根拠 |
|---|---|---|---|---|
| 1(ハジメ) | 4 | #EarShapeType_Fox | `red orange` (朱) | 狐の耳は朱色に塗られています。 |
| 1(ハジメ) | 6 | arrow-shaped chest zipper | `red orange` (朱) | 胸のファスナーは朱色に塗られています。 |
| 1(ハジメ) | 10 | shorts | `gray` (灰) | ショートパンツは灰色に塗られています。 |
| 2(ツグ) | 4 | #EarShapeType_Fox | `orange` (橙) | 耳はオレンジ色に塗られているため。 |
| 2(ツグ) | 5 | rectangular glasses | `orange` (橙) | 眼鏡のフレームがオレンジ色に塗られているため。 |
| 2(ツグ) | 7 | double-knotted scarf | `orange` (橙) | スカーフがオレンジ色に塗られているため。 |
| 3(ナオ) | 2 | the front-left chest of the top / dark / Arabic numeral | `black` (黒) | 胸の左前部にある'3'の数字は黒色であるため。 |
| 3(ナオ) | 4 | #EarShapeType_Fox | `yellow` (黄) | 耳は狐の形状をしており、全体が黄色で塗られているため。 |
| 4(モチ) | 3 | #EarShapeType_Fox | `white` (白) | 耳の内側の色は白です。 |
| 4(モチ) | 9 | skirt | `green`, `cyan` (緑・水色) | スカートの色は緑と水色の中間です。 |
| 5(イズ) | 3 | #EarShapeType_Fox | `green` (緑) | 耳は緑色です。 |
| 5(イズ) | 9 | tape wristbands (wrapped around the head and ponytail) | `gray` (灰) | 頭とポニーテールに巻かれたテープの色は灰色です。 |
| 5(イズ) | 11 | tape wristbands (wrapped around the head and right arm) | `gray` (灰) | 頭と右腕に巻かれたテープの色は灰色です。 |
| 6(ムイ) | 2 | #EarShapeType_Fox | `pink`, `white` (桃・白) | 耳の内側はピンクで、外側は白です。 |
| 6(ムイ) | 6 | hexagonal brooch | `blue` (青) | ブローチは青です。 |
| 6(ムイ) | 7 | lace trim | `white` (白) | レースの縁飾りは白です。 |
| 6(ムイ) | 8 | Victorian dress | `purple` (紫) | ヴィクトリア風ドレスは紫です。 |
| 7(ナナ) | 2 | front left chest of the hakama / dark / Arabic numeral  | `black` (黒) | ハカマの左胸の数字 '7' は黒で描かれています。 |
| 7(ナナ) | 3 | #EarShapeType_Fox | `blue`, `cyan` (青・水色) | 耳は青と水色の組み合わせです。 |
| 7(ナナ) | 7 | prayer beads necklace | `blue` (青) | 数珠のネックレスは青のビーズでできています。 |
| 7(ナナ) | 8 | Far-Easten style coat | `blue` (青) | 上着は青色で描かれています。 |
| 7(ナナ) | 10 | wide-leg dark pants | `blue` (青) | ズボンは青色で描かれています。 |
| 7(ナナ) | 11 | Japanese-style casual outfit | `blue` (青) | 全体的な服装は青の和風カジュアルな装いです。 |
| 8(ワカツ) | 3 | #EarShapeType_Fox | `orange` (橙) | フォックスの耳は画像でオレンジに塗られています。 |
| 8(ワカツ) | 9 | tactical vest | `orange`, `red` (橙・赤) | タクティカルベストは画像でオレンジと赤の組み合わせになっています。 |
| 8(ワカツ) | 10 | tool pouches | `orange` (橙) | ツールポーチは画像でオレンジに塗られています。 |
| 9(チカ) | 2 | the left chest of the robe outfit / dark / Arabic numer | `black` (黒) | ローブの左胸のアラビア数字 '9' は黒色で描かれています。 |
| 9(チカ) | 6 | tails in ring arrangement | `blue`, `white` (青・白) | 尻尾の輪は青と白で構成されています。 |
| 9(チカ) | 8 | large dark cape | `blue`, `black` (青・黒) | 大きなマントは青と黒で描かれています。 |
| 10(ミツル) | 2 | the left chest of the top (slightly inconspicuous due t | `red` (赤) | 左胸のアラビア数字は赤色で描かれているため。 |
| 10(ミツル) | 8 | Chinese-style mandarin-collar jacket | `red` (赤) | 中華風の詰襟ジャケットは赤色で描かれているため。 |
| 10(ミツル) | 9 | wide-leg pants | `pink` (桃) | ワイドレッグパンツは桃色で描かれているため。 |
| 11(トウイチ) | 2 | #EarShapeType_Cat | `gray` (灰) | 耳は灰色に見えます。 |
| 11(トウイチ) | 3 | two arrow-shaped hair pins | `orange` (橙) | 髪留めが橙色に塗られています。 |
| 11(トウイチ) | 6 | long hooded coat | `blue`, `gray` (青・灰) | フード付きコートは青と灰色で構成されています。 |
| 12(トウジ) | 1 | on left shoulder, around right just below the edge of t | `orange` (橙) | 数字12はオレンジ色で表示されています。 |
| 12(トウジ) | 3 | bangs covering the left eye | `orange` (橙) | 前髪はオレンジ色で左目を覆っています。 |
| 12(トウジ) | 4 | #EarShapeType_Fox | `orange`, `white` (橙・白) | 狐耳はオレンジと白色でできています。 |
| 12(トウジ) | 5 | poncho cape / large cloak | `orange` (橙) | ポンチョケープと大きなクロークはオレンジとクリーム色です。 |
| 12(トウジ) | 8 | casual private outfit | `orange` (橙) | カジュアルな私服はオレンジとクリーム色です。 |
| 13(トミ) | 3 | #EarShapeType_Fox | `cyan` (水色) | 耳はシアン色の塗りです。 |
| 13(トミ) | 6 | sporty jersey | `blue` (青) | スポーティなジャージは青色です。 |
| 13(トミ) | 7 | multi-color stripe | `cyan`, `white` (水色・白) | 上衣にマルチカラーのストライプが見えます。 |
| 14(トヨ) | 3 | #EarShapeType_Fox | `cyan`, `white` (水色・白) | 耳の外側が水色で内側が白です。 |
| 14(トヨ) | 12 | tri-color outfit | `red orange`, `cyan`, `white` (朱・水色・白) | 服は朱色のスカート、水色のジャケット、白いシャツの三色です。 |
| 15(トウゴ) | 3 | #EarShapeType_Fox | `pink` (桃) | 耳がピンク色に塗られているため、狐の耳の形状に該当する部分の色です。 |
| 15(トウゴ) | 5 | right-side ponytail | `pink` (桃) | 髪がピンク色で右側にポニーテールがあるため、髪の色です。 |
| 15(トウゴ) | 7 | harness equipped with safety device on the back | `green` (緑) | 背中のハーネスが緑色に塗られています。 |
| 15(トウゴ) | 9 | pale-colored jacket | `green`, `white` (緑・白) | ジャケットは緑と白の色合いです。 |
| 15(トウゴ) | 10 | burn mark on right eye and ear | `orange` (橙) | 右目と耳の火傷はオレンジ色に塗られています。 |
| 16(ソロク) | 1 | around the brim of the hat, on the right side / dark /  | `black` (黒) | 帽子の右側に書かれたアラビア数字の '16' は黒です。 |
| 16(ソロク) | 2 | #EarShapeType_Fox | `pink` (桃) | 画像で確認できる耳はピンクです。 |
| 16(ソロク) | 7 | heart and key motif | `red`, `pink` (赤・桃) | 鍵とハートのモチーフは赤とピンクで構成されています。 |
| 17(トナ) | 3 | #EarShapeType_Fox | `blue` (青) | 耳は青色に塗られています。 |
| 18(トウヤ) | 3 | #EarShapeType_Fox | `black`, `pink` (黒・桃) | 耳の部分は黒と桃色が使用されています。 |
| 18(トウヤ) | 5 | horizontal line pattern on cheeks | `red` (赤) | 頬の線パターンは赤色です。 |
| 18(トウヤ) | 6 | blazer over shirt | `pink`, `orange` (桃・橙) | ブレザーとシャツは桃色と橙色です。 |
| 18(トウヤ) | 7 | skirt | `orange` (橙) | スカートは橙色です。 |
| 19(トク) | 3 | #EarShapeType_Fox | `white`, `brown` (白・茶) | 耳の外側は白で内側は茶色です。 |
| 20(ハツカ) | 1 | the buckle part of the choker / dark / Arabic numeral ' | `orange` (橙) | チョーカーのバックル部分はオレンジ色に見えます。 |
| 20(ハツカ) | 2 | the buckle part of the belt on the waist / dark / Arabi | `gray` (灰) | 腰のベルトのバックル部分は灰色に見えます。 |
| 21(ハツヒ) | 2 | small on the left collar and left shoulder of the basew | `black` (黒) | 襟と肩にある '21' は黒色で表示されています。 |
| 21(ハツヒ) | 3 | #EarShapeType_Fox | `orange`, `white` (橙・白) | フォックス型の耳はオレンジと白の組み合わせです。 |
| 22(フジ) | 3 | #EarShapeType_Fox | `yellow`, `white` (黄・白) | 狐型の耳は黄色が主で内側が白色です。 |
| 22(フジ) | 5 | earrings | `yellow` (黄) | イヤリングが黄色です。 |
| 22(フジ) | 6 | two scorpion-type segmented tails (freely movable like  | `yellow` (黄) | 蠍のような尾は黄色です。 |
| 22(フジ) | 11 | holograms resembling the moon and sun on a head modeled | `orange` (橙) | 星と太陽を表すホログラムは橙色です。 |
| 22(フジ) | 14 | ribbon sash at waist | `orange` (橙) | 腰のリボンは橙色です。 |
| 23(ツグミ) | 2 | the right side of the area with a pale stripe pattern f | `black` (黒) | フードトップにあるアラビア数字の'23'は黒で描かれています。 |
| 24(フトシ) | 1 | the clasp of the neck scarf / dark color / Arabic numer | `black` (黒) | 首元のスカーフ留めは黒で描かれています。 |
| 25(フィズ) | 3 | #EarShapeType_Fox | `gray`, `white` (灰・白) | 耳は灰色と白で塗られています。 |
| 25(フィズ) | 9 | casual private outfit | `cyan`, `blue`, `gray` (水色・青・灰) | 服装は水色、青、灰色で構成されています。 |
| 26(ニロク) | 2 | small area from the center of the sweater collar to the | `black` (黒) | アラビア数字 '26' は黒で描かれている。 |
| 26(ニロク) | 3 | #EarShapeType_Fox | `pink` (桃) | 狐の耳はピンクで塗られている。 |
| 27(ツギナ) | 5 | erected fox ears | `white` (白) | 耳の内側は白色です。 |
| 27(ツギナ) | 11 | casual private outfit | `purple` (紫) | 私服のスカートは紫色です。 |
| 28(ニハチ) | 6 | Somewhat large as body paint on the left shoulder's bar | `black` (黒) | 左肩の '28' の色が黒に見えるため。 |
| 28(ニハチ) | 7 | Somewhat large as body paint on the right shoulder's ba | `black` (黒) | 右肩のシグマ表記の色が黒に見えるため。 |
| 28(ニハチ) | 8 | #EarShapeType_Fox | `orange` (橙) | 耳の色がオレンジに見えるため。 |
| 28(ニハチ) | 10 | dangling earrings | `yellow`, `white` (黄・白) | イヤリングが黄色と白に見えるため。 |
| 29(ニトク) | 1 | #EarShapeType_Fox | `blue`, `white` (青・白) | 耳は青と白に塗られています。 |
| 30(ミツト) | 4 | #EarShapeType_Fox | `yellow` (黄) | 耳は黄色に色づけされています。 |
| 31(ミツイ) | 4 | on the bare skin of the left shoulder as body paint, sl | `black` (黒) | 左肩の体のペイントが黒で描かれているためです。 |
| 31(ミツイ) | 5 | #EarShapeType_Fox | `cyan` (水色) | 耳が水色で塗られているためです。 |
| 31(ミツイ) | 9 | athletic outfit | `blue`, `yellow` (青・黄) | 運動服が青と黄色で構成されているためです。 |
| 31(ミツイ) | 11 | thigh-high socks with boots | `cyan`, `blue` (水色・青) | 膝までの靴下とブーツが水色と青で塗られているためです。 |
| 31(ミツイ) | 14 | mathematical body paint | `black` (黒) | 体のペイントが黒で描かれているためです。 |
| 32(ミツギ) | 2 | the right side of the area with a pale stripe pattern f | `cyan` (水色) | 数字の '32' はサイドの暗い色の上に描かれている。 |
| 32(ミツギ) | 4 | #EarShapeType_Fox | `cyan`, `white` (水色・白) | 耳は主に水色で内側が白い。 |
| 32(ミツギ) | 7 | number marking and stripe pattern | `cyan`, `white` (水色・白) | ストライプパターンは水色と白。 |
| 32(ミツギ) | 8 | casual open-collar jacket | `cyan` (水色) | オープンカラージャケットは水色。 |
| 33(ミサ) | 1 | Slightly small from the left chest to the left shoulder | `black` (黒) | 左肩のケープにあるアラビア数字「33」は黒で描かれている。 |
| 33(ミサ) | 2 | On the back of each glove / dark / Arabic numeral '33' | `black` (黒) | 各手袋の背にあるアラビア数字「33」は黒で描かれている。 |
| 33(ミサ) | 3 | #EarShapeType_Fox | `orange`, `yellow` (橙・黄) | 耳の部分はオレンジと黄色の中間色。 |
| 33(ミサ) | 9 | ear-covering maid cap | `red orange` (朱) | 耳を覆うメイドキャップは朱色に塗られている。 |
| 34(サトシ) サンジ | 2 | Slightly large on the chest area of the apron / dark /  | `black` (黒) | エプロンに描かれたアラビア数字'34'は黒色です。 |
| 35(サトコ) 35(ミコ) | 3 | #EarShapeType_Fox | `orange`, `yellow` (橙・黄) | 狐の耳がオレンジと黄色で塗られているため。 |
| 35(サトコ) 35(ミコ) | 9 | necktie (usual) | `orange` (橙) | ネクタイがオレンジ色に塗られているため。 |
| 35(サトコ) 35(ミコ) | 11 | gohei stick (miko) | `white` (白) | 御幣が白色で描かれているため。 |
| 36(ミトム) | 2 | Slightly large on the entire chest area of the base wea | `black` (黒) | 数字'36'は黒色で描かれています。 |
| 36(ミトム) | 3 | #EarShapeType_Fox | `orange`, `white` (橙・白) | 耳はオレンジと白の組み合わせです。 |
| 36(ミトム) | 6 | Victorian-lolita dress | `purple`, `orange`, `white` (紫・橙・白) | 服は紫、オレンジ、白の配色です。 |
| 36(ミトム) | 9 | ruffle and lace details | `white` (白) | フリルとレースの部分は白色です。 |
| 36(ミトム) | 10 | bow ribbon at chest | `pink` (桃) | 胸のリボンはピンク色です。 |
| 37(サナ) | 2 | #EarShapeType_Fox | `pink`, `white` (桃・白) | 耳はピンク色で、内側が白です。 |
| 37(サナ) | 9 | casual private outfit | `red`, `blue`, `yellow`, `white` (赤・青・黄・白) | 外観は赤いコート、青いシャツ、黄色のネクタイ、白いパンツです。 |
| 39(サク) | 1 | Slightly large, centered on the front of the sphere at  | `black` (黒) | 胸部の球体にあるアラビア数字の'39'は黒で描かれています。 |
| 39(サク) | 2 | Prominently across the entire supporter visible from th | `black` (黒) | 腰のサポーターにあるアラビア数字の'39'は黒で描かれています。 |
| 40(ヨソ) | 2 | #EarShapeType_Fox | `white`, `cyan` (白・水色) | 耳は白と水色で塗られています。 |
| 40(ヨソ) | 9 | pattern inspired by '40' | `cyan`, `blue` (水色・青) | 服のパターンやエンブレムが水色と青で構成されています。 |
| 41(ヨソイチ) | 3 | #EarShapeType_Fox | `cyan`, `blue` (水色・青) | 耳は画像で水色と青色に塗られています。 |
| 42(ヨツグ) | 2 | on the left collar, near the edge of the fabric, somewh | `black` (黒) | 左襟の縁付近にあるアラビア数字『42』は黒色で表示されています。 |
| 42(ヨツグ) | 3 | #EarShapeType_Fox | `pink`, `white` (桃・白) | 耳は狐の形で、ピンクと白で色付けされています。 |
| 43(シトミ) | 3 | #EarShapeType_Fox | `blue`, `white` (青・白) | 耳は外側が青、内側が白に塗られています。 |
| 43(シトミ) | 10 | often holding a game controller | `yellow`, `black`, `blue` (黄・黒・青) | ゲームコントローラーは黄色、黒、青で色付けされています。 |
| 44(シトシ) | 2 | on the left chest of the vest, slightly above the butto | `black` (黒) | アラビア数字「44」は黒色で描かれている。 |
| 44(シトシ) | 3 | #EarShapeType_Fox | `green`, `yellow` (緑・黄) | 狐の耳は緑と黄色で塗られている。 |
| 45(シゴ) | 3 | #EarShapeType_Fox | `blue`, `white` (青・白) | 耳の外側は青色で内側は白色です。 |
| 47(シナ) | 3 | #EarShapeType_Fox | `gray`, `white` (灰・白) | 耳は灰色と内側が白色で塗られています。 |
| 48(シハチ) | 2 | on the left collar, near the neck, small / dark / Arabi | `black` (黒) | 数字 '48' は黒で描かれています。 |
| 48(シハチ) | 3 | #EarShapeType_Fox | `gray`, `white` (灰・白) | 耳は灰色と白色で表現されています。 |
| 49(ヨチカ) | 3 | #EarShapeType_Fox | `blue`, `white` (青・白) | 狐の耳は青と白で塗られています。 |
| 49(ヨチカ) | 6 | a slightly unsociable, boyish face | `cyan` (水色) | 顔の輪郭線が水色で描かれています。 |
| 49(ヨチカ) | 7 | a smile that looks dead in the eyes (expression when tr | `blue` (青) | 笑った時の目は青で表現されています。 |
| 50(ナカバ) | 3 | cat whiskers | `black` (黒) | ヒゲが黒く描かれているため |
| 50(ナカバ) | 4 | mint-colored hooded top wrapped around the body | `cyan` (水色) | 身に巻かれたフードが水色であるため |
| 50(ナカバ) | 5 | large cat ears | `cyan` (水色) | 大きな猫耳が水色であるため |
| 50(ナカバ) | 8 | mint-colored hooded top wrapped around the waist | `cyan` (水色) | 腰に巻かれたフードが水色であるため |
| 51(イソイチ) | 2 | left collar, around the neck / light color / Roman nume | `green` (緑) | 襟の周りが緑色で描かれています。 |
| 52(イツギ) | 3 | #EarShapeType_Fox | `white`, `gray` (白・灰) | 耳の内部が白、外側が灰色に見えます。 |
| 53(イツゾウ) | 2 | #EarShapeType_Fox | `orange`, `white` (橙・白) | 耳が橙色と白で塗られています。 |
| 55(イソゴ) | 3 | #EarShapeType_Fox | `green`, `white` (緑・白) | 耳の部分は緑と白で塗られています。 |
| 55(イソゴ) | 5 | #EarShapeType_Fox | `green`, `white` (緑・白) | 耳の部分は緑と白で塗られています。 |
| 56(イソロク) | 3 | #EarShapeType_Fox | `gray` (灰) | 耳は灰色で塗られている。 |
| 57(イズナ) | 3 | #EarShapeType_Fox | `yellow`, `white` (黄・白) | 耳は黄色と白で塗られています。 |
| 57(イズナ) | 11 | armband with number on right shoulder | `yellow`, `white` (黄・白) | 腕章は黄色と白で塗られています。 |
| 58(イソヤ) | 2 | #EarShapeType_Fox | `brown`, `white` (茶・白) | 耳の外側は茶色、内側は白色で塗られています。 |
| 60(ムソウ) | 2 | #EarShapeType_Fox | `pink`, `white` (桃・白) | 耳はピンクと白で塗られています。 |
| 61(ロクイチ) 61(ロイ) | 3 | #EarShapeType_Fox | `pink` (桃) | 耳はヒツジの耳から変形しており、ピンクに塗られています。 |
| 61(ロクイチ) 61(ロイ) | 5 | heart and key motif | `pink` (桃) | ハートと鍵のモチーフはピンク色です。 |
| 61(ロクイチ) 61(ロイ) | 6 | heart and key motif charm hairpin (idol outfit) | `pink` (桃) | アイドル衣装のハートと鍵のモチーフのヘアピンはピンク色です。 |
| 62(ロジ) | 2 | #EarShapeType_Fox | `pink` (桃) | 耳がピンクに塗られているため。 |
| 62(ロジ) | 7 | light-colored boots | `orange`, `red orange` (橙・朱) | ブーツがオレンジと赤橙の中間色に塗られているため。 |
| 62(ロジ) | 8 | armband (with number on left shoulder) | `pink` (桃) | 腕章がピンクに塗られているため。 |
| 63(ムツミ) | 2 | Center of the belt on the base wear / dark / Arabic num | `black` (黒) | ベースウェアの中心にある数字 '63' は黒で描かれている。 |
| 64(ムトシ) | 2 | on the left collar, near the edge of the fabric, small  | `black` (黒) | 左襟の切れ目付近にある '64' の数字は黒色で表されています。 |
| 64(ムトシ) | 3 | #EarShapeType_Fox | `red`, `pink` (赤・桃) | 耳は狐のような形をしており、赤と桃色の色合いです。 |
| 65(ロクゴ) | 3 | #EarShapeType_Fox | `gray` (灰) | 耳は灰色に塗られている。 |
| 66(ムロク) | 1 | On the yoke bib, one digit on each side / dark color /  | `black` (黒) | 数字'66'は暗い色で描かれている。 |
| 66(ムロク) | 2 | On the collar, one digit on each side / dark color / Ar | `black` (黒) | 襟の数字'66'は暗い色で描かれている。 |
| 66(ムロク) | 3 | #EarShapeType_Fox | `pink` (桃) | 耳はピンク色で描かれている。 |
| 67(ムナ) | 3 | #EarShapeType_Fox | `blue` (青) | 耳は青色で描かれています。 |
| 67(ムナ) | 3 | #EarShapeType_Fox | `blue` (青) | 耳は青色で描かれています。 |
| 67(ムナ) | 9 | slightly darker skin tone | `pink` (桃) | 肌の色が少し暗いピンクで描かれています。 |
| 67(ムナ) | 10 | muscular physique (in Muscle Mode) | `pink` (桃) | マッスルモード時の肌の色はピンクです。 |
| 68(ロクヤ) | 1 | on the right side of the bandana / dark / Arabic numera | `red` (赤) | バンダナの右側にある '68' のアラビア数字は赤色で表示されています。 |
| 68(ロクヤ) | 2 | on the right side of the bandana (normal outfit) / dark | `red` (赤) | バンダナの右側にある '68' のアラビア数字は赤色で表示されています。 |
| 68(ロクヤ) | 3 | #EarShapeType_Fox | `green` (緑) | 耳は緑色で表現されており、キツネの形をしています。 |
| 69(ロック) | 3 | On the center of the forehead of the mask, slightly sma | `red` (赤) | 仮面の額部分には赤色の数字デザインがある |
| 69(ロック) | 4 | #EarShapeType_Fox | `pink` (桃) | 耳は狐の耳で、ピンク色で描かれている |
| 69(ロック) | 6 | earrings | `pink` (桃) | ピンク色のイヤリングが確認できる |
| 69(ロック) | 13 | mask with number markings (sometimes worn) | `pink` (桃) | 仮面全体がピンク色で、数字の表示がある |
| 70(ナナト) | 3 | #EarShapeType_Fox | `purple`, `white` (紫・白) | 外形部は紫で内側は白です。 |
| 71(ナナヒ) | 2 | #EarShapeType_Fox | `blue`, `white` (青・白) | 狐耳は青と白で塗られています。 |
| 72(ナフタ) | 3 | #EarShapeType_Fox | `blue`, `white` (青・白) | 耳の内側が白で外側が青です。 |
| 72(ナフタ) | 9 | '研修' (trainee) name tag | `white`, `black` (白・黒) | 名札は白地に黒文字です。 |
| 72(ナフタ) | 10 | barcode-style numbered tag | `black` (黒) | バーコードは黒で縞模様です。 |
| 73(ナトミ) | 2 | #EarShapeType_Fox | `white`, `pink` (白・桃) | 耳の外側は白、内側は桃色で塗られているため。 |
| 74(ナナヨ) | 2 | #EarShapeType_Fox | `gray`, `white` (灰・白) | 耳の外側は灰色で内側は白です。 |
| 75(シチゴ) | 3 | #EarShapeType_Fox | `yellow`, `white` (黄・白) | 耳は外側が黄で内側が白です |
| 75(シチゴ) | 11 | left shoulder armband | `yellow`, `blue` (黄・青) | 左肩の腕章は黄地に青い文字です |
| 76(シチロク) | 4 | #EarShapeType_Fox | `blue`, `white` (青・白) | 耳は青と白で塗られています。 |
| 77(ナヅナ) | 3 | #EarShapeType_Fox | `white`, `cyan` (白・水色) | 耳は白と水色で塗られている。 |
| 78(ナナハ) | 1 | The heart pattern on the ears is inspired by Arabic num | `pink` (桃) | 耳のハート模様はピンク色です。 |
| 78(ナナハ) | 3 | diamond and heart-patterned ear markings | `pink`, `purple` (桃・紫) | 耳のダイヤとハート模様はピンクと紫色です。 |
| 80(ヤソ) | 3 | #EarShapeType_Fox | `orange`, `white` (橙・白) | 耳がオレンジと白に塗られているため |
| 80(ヤソ) | 6 | curl bob hair with a figure-eight-shaped outline | `orange` (橙) | 髪がオレンジに塗られているため |
| 80(ヤソ) | 9 | Cannot feel at ease without an information terminal to  | `white` (白) | 手に持っている情報端末が白に塗られているため |
| 81(ヤイチ) | 3 | #EarShapeType_Fox | `white`, `pink` (白・桃) | 耳が白とピンクに塗られているため。 |
| 81(ヤイチ) | 7 | horizontal line pattern on the cheeks | `black` (黒) | 頬の横線が黒に塗られているため。 |
| 84(ヤツヨ) | 3 | #EarShapeType_Fox | `gray`, `white` (灰・白) | 耳が灰色で内側が白色に塗られているため。 |
| 84(ヤツヨ) | 4 | left ear accessory | `orange`, `cyan` (橙・水色) | 耳のアクセサリーはオレンジと水色に塗られているため。 |
| 85(ハッコ) 85(パコ) | 2 | #EarShapeType_Fox | `brown`, `orange` (茶・橙) | 耳の内側はオレンジ色で、外側は茶色に見えます。 |
| 86(ハチロ) | 1 | on the top area of the bandana worn on the right ear /  | `red` (赤) | バンダナの上部にある数字は赤で塗られています。 |
| 86(ハチロ) | 2 | on the top area of the bandana worn on the right ear (n | `red` (赤) | バンダナの上部にある数字は赤で塗られています。 |
| 86(ハチロ) | 3 | #EarShapeType_Fox | `green` (緑) | 耳は緑色で描かれています。 |
| 87(ヤシナ) 87(ハナ) | 1 | The heart pattern on the ears is inspired by Arabic num | `pink`, `blue`, `orange` (桃・青・橙) | 耳のハート模様はピンク、青、橙の配色です。 |
| 87(ヤシナ) 87(ハナ) | 3 | diamond and heart-patterned ear markings | `pink`, `blue`, `orange` (桃・青・橙) | 耳のダイアモンドとハート模様はピンク、青、橙です。 |
| 87(ヤシナ) 87(ハナ) | 8 | heart-shaped diamond pendant necklace | `blue`, `orange`, `white` (青・橙・白) | ペンダントは青と橙のハート形で、ダイアモンド型の白い部分があります。 |
| 88(ヤソハチ) | 2 | #EarShapeType_Fox | `orange` (橙) | 耳はオレンジである |
| 88(ヤソハチ) | 3 | left ear accessory | `red`, `gray` (赤・灰) | 耳のアクセサリーは赤と灰色で縁取られている |
| 88(ヤソハチ) | 7 | piano-keyboard holographic ring | `white`, `black` (白・黒) | ピアノのホログラフィックリングは白と黒の鍵盤で構成されている |
| 89(ヤスモ) | 3 | #EarShapeType_Fox | `white`, `pink` (白・桃) | 耳の内側は白で、外側は桃色です。 |
| 92(コトジ) | 1 | #EarShapeType_Fox | `blue`, `white` (青・白) | 耳の外側が青、内側が白に塗られています。 |
| 93(クミ) | 1 | Slightly large, centered on the front of the sphere at  | `black` (黒) | 胸部の球体の前面にある '93' は黒色で表示されているため。 |
| 93(クミ) | 2 | Prominently across the entire supporter visible from th | `black` (黒) | 腰のサポーターにある '93' は黒色で表示されているため。 |
| 93(クミ) | 3 | #EarShapeType_Fox | `yellow`, `white` (黄・白) | 耳は黄色と白で示されているため。 |
| 93(クミ) | 7 | belt supporter with number design at the waist | `brown` (茶) | 腰のベルトサポーターは茶色で表示されているため。 |
| 94(ツクシ) | 3 | #EarShapeType_Fox | `blue`, `white` (青・白) | 耳の外部は青で、内部は白です。 |
| 96(クルリ) | 2 | On the center of the forehead of the mask, slightly sma | `pink` (桃) | マスクの中央にある数字の色はピンクです。 |
| 96(クルリ) | 3 | #EarShapeType_Fox | `pink` (桃) | 顔や耳がピンク色になっています。 |
| 96(クルリ) | 10 | high heels (casual wear) | `pink` (桃) | ハイヒールはカジュアルウェアおよびピンク色です。 |
| 97(ココナ) | 3 | #EarShapeType_Fox | `white`, `blue` (白・青) | 耳は外側が白、内側が青です。 |
| 98(キュウヤ) | 3 | #EarShapeType_Fox | `white` (白) | 狐の耳の内側が白色に塗られているため |
| 99(ツクモ) | 3 | #EarShapeType_Fox | `white`, `red` (白・赤) | 耳は白地で内側が赤色です。 |
| 99(ツクモ) | 7 | fox-like ears and tail-tufts pattern | `red`, `gray`, `black` (赤・灰・黒) | 尻尾の先端に赤と灰色、黒の模様があります。 |
| 99(ツクモ) | 9 | choker with kanji numerals | `pink` (桃) | チョーカーがピンク色で漢数字が書かれています。 |
| バイナ 2(ツギ) | 2 | on the left collar, slightly smaller / dark / Arabic nu | `black` (黒) | 左襟のアラビア数字「2」は黒で塗られているため。 |
| バイナ 2(ツギ) | 3 | #EarShapeType_Fox | `gray`, `white` (灰・白) | 耳は灰色と白で構成されているため。 |
| バイナ 2(ツギ) | 10 | holographic body (prototype state) | `gray`, `white` (灰・白) | ホログラフィックな体は灰色と白で塗られているため。 |
| ディケ 10(ツナイ) | 1 | On the left chest of the front of the full-body cover o | `black` (黒) | ローマ数字 'X' は黒で記載されています。 |
| ディケ 10(ツナイ) | 2 | #EarShapeType_Fox | `brown`, `white` (茶・白) | 狐の耳は茶色と白で描かれています。 |
| ディケ 10(ツナイ) | 10 | '取扱注意' (handle with care) caution label (on base) | `yellow`, `black` (黄・黒) | 警告ラベル '取扱注意' は黄色の背景に黒字で書かれています。 |
| 000(チトセ) | 3 | #EarShapeType_Cat | `gray` (灰) | 耳の外側が灰色に塗られているため。 |
| 零 零 | 3 | cat ear accessories | `orange`, `white` (橙・白) | 猫耳アクセサリーはオレンジと白です |
| 零 百 | 2 | same humanoid form | `red` (赤) | 同じヒューマノイドの形式であるため色は指定されていません。 |
| 零 百 | 3 | cat ear accessories | `white` (白) | 猫耳アクセサリーは白で塗られています。 |
| 100(モモ) | 2 | #EarShapeType_Fox | `white`, `pink` (白・桃) | 耳の外側が白、内側が淡い桃色のため。 |
| 111(アイズ) | 2 | #EarShapeType_Cat | `yellow` (黄) | 猫耳の部分が黄色に塗られているため。 |
| 222(ペルゲン) | 2 | #EarShapeType_Fox | `white` (白) | 耳は白色に塗られています。 |
| 222(ペルゲン) | 5 | long pale-colored twin-tail hairstyle | `white` (白) | 髪は白色に塗られています。 |
| 222(ペルゲン) | 6 | pale-colored collar | `white` (白) | 襟は白色に塗られています。 |
| 222(ペルゲン) | 7 | pendant featuring three '2's and a heart motif | `pink`, `red` (桃・赤) | ペンダントはピンクと赤で塗られています。 |
| 222(ドッペル) | 2 | #EarShapeType_Fox | `white`, `gray` (白・灰) | 耳は白と灰色で構成されています。 |
| 222(ドッペル) | 5 | long pale-colored twin-tail hairstyle | `white`, `gray` (白・灰) | 髪は白と灰色で構成されています。 |
| 222(ドッペル) | 6 | pale-colored collar | `white`, `gray` (白・灰) | 襟は白と灰色で構成されています。 |
| 222(ドッペル) | 7 | pendant featuring three '2's and a heart motif | `yellow`, `white` (黄・白) | ペンダントは黄色と白で構成されています。 |
| 444(シテン) | 3 | #EarShapeType_Fox | `cyan`, `white` (水色・白) | 耳が水色で内側が白です。 |
| 444(シテン) | 7 | halo consisting of three squares/diamonds | `orange` (橙) | 3つの四角/ダイヤの後光は橙色です。 |
| 666(リリス) | 2 | #EarShapeType_Fox | `pink`, `white` (桃・白) | 耳は主に桃色で内側が白く塗られています。 |
| 666(リリス) | 5 | halo with three '6's arranged in rotational symmetry (w | `pink` (桃) | ハローとそこに描かれる '6's は桃色です。 |
| 666(リリス) | 6 | wings inspired by the motif of '666' (with heart-shaped | `pink` (桃) | 羽とその先の心形は桃色です。 |
| 666(リリス) | 8 | brooch with three '6's arranged in rotational symmetry  | `red` (赤) | ブローチは赤色です。 |
| 666(リリス) | 10 | brooch with three '6's arranged in rotational symmetry  | `red` (赤) | ブローチは赤色です。 |
| 777(ヨロコビ) | 2 | #EarShapeType_Cat | `white` (白) | 耳の内側が白で塗られているため。 |
| 777(ヨロコビ) | 5 | holding a cocoa cigarette bar in the mouth | `brown` (茶) | 口にくわえているココアシガレットバーが茶色で塗られているため。 |
| 777(ヨロコビ) | 2 | #EarShapeType_Cat | `white` (白) | 耳の内側が白で塗られているため。 |
| 777(ヨロコビ) | 5 | holding a cocoa cigarette bar in the mouth | `brown` (茶) | 口にくわえているココアシガレットバーが茶色で塗られているため。 |
| 888(ムゲン) | 2 | EarShapeType_Wing | `orange` (橙) | 耳の形状がオレンジ色に塗られているため。 |
| トレッド 3×11(トリィレブン) | 1 | around the edge of the fabric on the left hem of the ca | `black` (黒) | ケープの左裾にある数字『33(3×11)』は黒で描かれている。 |
| トレッド 3×11(トリィレブン) | 2 | #EarShapeType_Fox | `yellow` (黄) | 耳は狐の形で、黄色で描かれている。 |
| トレッド 3×11(トリィレブン) | 6 | three scorpion-type segmented tails (freely movable lik | `yellow` (黄) | 三つの尻尾（サソリ型の節）が黄色で描かれている。 |
| トレッド 3×11(トリィレブン) | 10 | two round brooches featuring a three-color motif | `pink`, `cyan`, `yellow` (桃・水色・黄) | 丸いブローチはピンク、水色、黄色で構成されている。 |
| トレッド 3×11(トリィレブン) | 11 | halo featuring heart shapes, a three-color motif, and s | `pink`, `cyan`, `yellow` (桃・水色・黄) | ハート形の輪の三色モチーフは、ピンク、水色、黄色で構成されている。 |
| トレッド 3×11(トリィレブン) | 13 | flashy Victorian Lolita dress in CMY primary colors | `cyan`, `yellow` (水色・黄) | ビクトリア風のロリータドレスは、CMYの色（シアン、マゼンタ、イエロー）が使われている。 |
| 量産型 111(アイズ) | 3 | #EarShapeType_Cat | `red orange` (朱) | 耳の部分が朱色に塗られています。 |
| 量産型 444(シテン) | 4 | #EarShapeType_Fox | `white` (白) | 耳の内側が白に塗られているため。 |
| 量産型 444(シテン) | 8 | halo consisting of three squares/diamonds | `gray` (灰) | 三つの菱形が灰色に塗られているため。 |
| 量産型 666(リリス) | 3 | #EarShapeType_Fox | `pink`, `white` (桃・白) | 耳が桃色と白色で塗られているため |
| 量産型 666(リリス) | 6 | halo with three '6's arranged in rotational symmetry | `purple`, `pink` (紫・桃) | 666の後光が紫色と桃色で塗られているため |
| 量産型 666(リリス) | 7 | wings inspired by the motif of '666' | `purple`, `pink` (紫・桃) | 翼の666のモチーフが紫色と桃色で塗られているため |
| 量産型 666(リリス) | 9 | brooch with three '6's arranged in rotational symmetry  | `purple` (紫) | ブローチが紫色で塗られているため |
| 量産型 666(リリス) | 11 | brooch with three '6's arranged in rotational symmetry  | `purple` (紫) | 同じブローチが紫色で塗られているため |
| 量産型 777(ヨロコビ) | 3 | #EarShapeType_Cat | `brown` (茶) | 猫耳が茶色で塗られています。 |
| 量産型 777(ヨロコビ) | 6 | holding a cocoa cigarette bar in the mouth | `brown` (茶) | 口にくわえたココアシガレットバーが茶色です。 |
| 量産型 777(ヨロコビ) | 3 | #EarShapeType_Cat | `brown` (茶) | 猫耳が茶色で塗られています。 |
| 量産型 777(ヨロコビ) | 6 | holding a cocoa cigarette bar in the mouth | `brown` (茶) | 口にくわえたココアシガレットバーが茶色です。 |

### 創作 DB に無い配色（実測 HEX・55 件）

公式の透過イラスト（`$palette.source: artwork`）から**実測**した色のうち、
`ColorPalette` のどの HEX とも一致しないもの（色距離 10 以内を同じ色とみなす）。
抽出条件は上流 `patch-colorpalette.mjs --from-artwork` と同じで、共通造形色は除外済み。

**確認してほしい点**: 純黒に近い色（`#010000` など）は輪郭線が彩度条件をすり抜けたもの、
白に近い色は紙面・ハイライトの可能性がある。面積比が大きくても配色とは限らないので、
`ColorPalette` へ入れる前に画像で確かめてほしい。

| キャラ | 実測 HEX | 面積比 | 現在の ColorPalette |
|---|---|---|---|
| 2(ツグ) | `#F4C5A8` | 7.0% | `#FFA073`, `#E9E9E9`, `#FFA579`, `#FFBD97`, `#FFCFAE`, `#FFE6D5` |
| 4(モチ) | `#010000` | 8.0% | `#00B7D9`, `#0097C9`, `#67BDBD`, `#7AD9ED`, `#8DE8ED` |
| 5(イズ) | `#E6F2F1` | 6.4% | `#61DAAC`, `#4CD9E8`, `#7FE2C5`, `#009489`, `#408784` |
| 8(ワカツ) | `#FF6574` | 2.1% | `#E85764`, `#FF9E68`, `#FFA9A8`, `#FC6932`, `#BC4655` |
| 16(ソロク) | `#F4FAE8` | 26.0% | `#F26383`, `#6A88C2`, `#A4A2C3`, `#F9BBC1`, `#E25970` |
| 16(ソロク) | `#FF7297` | 2.6% | `#F26383`, `#6A88C2`, `#A4A2C3`, `#F9BBC1`, `#E25970` |
| 17(トナ) | `#6B8CC5` | 2.3% | `#9DB0DB`, `#5B77A8`, `#F76D67`, `#938FAD`, `#B2B0CF` |
| 18(トウヤ) | `#612C26` | 2.5% | `#7C4540`, `#ED5D47`, `#D46E87`, `#FFAC8F`, `#F9642D` |
| 20(ハツカ) | `#F4FAE8` | 7.6% | `#FFA457`, `#AEB4B4`, `#FFC4A3`, `#FFDCAE`, `#B3B9B9`, `#EAE5D6`, `#CBCECD`, `#E9EBE5` |
| 21(ハツヒ) | `#F3F1EE` | 5.0% | `#FFAC8F`, `#FFEFE3`, `#FFD7C2`, `#FEF3D9`, `#FECF7D` |
| 23(ツグミ) | `#EFF5ED` | 8.7% | `#7BDEC1`, `#C2F2DE`, `#B1DDA6`, `#F9FF9C`, `#FFF007` |
| 23(ツグミ) | `#8DC0AB` | 2.0% | `#7BDEC1`, `#C2F2DE`, `#B1DDA6`, `#F9FF9C`, `#FFF007` |
| 26(ニロク) | `#DEA2A7` | 2.3% | `#F9BBC0`, `#F4ABB4`, `#DD7C9C`, `#FFA79B`, `#FFE1EA` |
| 28(ニハチ) | `#FFB879` | 2.3% | `#DB653F`, `#F4F1E5`, `#FF9E68`, `#FFD59B`, `#FFC4A3` |
| 30(ミツト) | `#E4BC75` | 2.8% | `#FFA634`, `#F2F1E7`, `#F9FF9C`, `#FFD58F`, `#FFF13A` |
| 32(ミツギ) | `#EFF5ED` | 11.1% | `#C2F2DE`, `#B2DDA7`, `#7BDEC1`, `#FAFE9D`, `#FFF000` |
| 32(ミツギ) | `#A7D9C4` | 2.8% | `#C2F2DE`, `#B2DDA7`, `#7BDEC1`, `#FAFE9D`, `#FFF000` |
| 35(サトコ) 35(ミコ) | `#FAF9E8` | 4.1% | `#E98D30`, `#FFA457`, `#C8D253`, `#F9F57F`, `#FFC675` |
| 41(ヨソイチ) | `#80A8CC` | 3.2% | `#9BC1E6`, `#FFC5BC`, `#5C9ABC`, `#37393C`, `#4CD9E8`, `#00939F`, `#000101` |
| 43(シトミ) | `#1D659C` | 2.4% | `#387EB6`, `#405AB9`, `#A2AFB8`, `#FCCD2F`, `#A4DAEF`, `#000001` |
| 45(シゴ) | `#4E5C80` | 2.5% | `#434F6F`, `#6B658C`, `#C8CECD`, `#54565A`, `#4A6B6A`, `#175D7E`, `#010102` |
| 45(シゴ) | `#273654` | 2.3% | `#434F6F`, `#6B658C`, `#C8CECD`, `#54565A`, `#4A6B6A`, `#175D7E`, `#010102` |
| 47(シナ) | `#708292` | 2.4% | `#387EB6`, `#6AA6D7`, `#185EBD`, `#C7CDD8`, `#8B9BAC` |
| 48(シハチ) | `#848A6F` | 2.4% | `#9EA388`, `#7EAEAB`, `#EF9D46`, `#FFBC08`, `#CACDCB`, `#FFD07D` |
| 53(イツゾウ) | `#FAF9E8` | 6.6% | `#FFC675`, `#C7D54C`, `#FFA457`, `#E98D30`, `#F9F57F` |
| 53(イツゾウ) | `#E4AD5C` | 2.2% | `#FFC675`, `#C7D54C`, `#FFA457`, `#E98D30`, `#F9F57F` |
| 57(イズナ) | `#FFFF6B` | 2.1% | `#E8F152`, `#FFEE62`, `#F7FFB9`, `#4B79BE`, `#A6BC40` |
| 60(ムソウ) | `#FFF1F0` | 8.3% | `#FFA79B`, `#CD4479`, `#FFE1EA`, `#FF8FAD`, `#F85DB3` |
| 60(ムソウ) | `#E47693` | 2.3% | `#FFA79B`, `#CD4479`, `#FFE1EA`, `#FF8FAD`, `#F85DB3` |
| 61(ロクイチ) 61(ロイ) | `#E85764` | 18.0% | `#F26383`, `#6A88C2`, `#A4A2C3`, `#F9BBC1`, `#DC576C` |
| 61(ロクイチ) 61(ロイ) | `#F4FAE8` | 2.8% | `#F26383`, `#6A88C2`, `#A4A2C3`, `#F9BBC1`, `#DC576C` |
| 61(ロクイチ) 61(ロイ) | `#FF769C` | 2.1% | `#F26383`, `#6A88C2`, `#A4A2C3`, `#F9BBC1`, `#DC576C` |
| 66(ムロク) | `#FCC7CC` | 3.6% | `#6D7880`, `#FFA634`, `#FFC046`, `#F9BBC0`, `#CC8C8C`, `#FF8FAD` |
| 66(ムロク) | `#FDDCDF` | 2.9% | `#6D7880`, `#FFA634`, `#FFC046`, `#F9BBC0`, `#CC8C8C`, `#FF8FAD` |
| 66(ムロク) | `#FCCFD3` | 2.1% | `#6D7880`, `#FFA634`, `#FFC046`, `#F9BBC0`, `#CC8C8C`, `#FF8FAD` |
| 69(ロック) | `#EDD2DA` | 9.0% | `#F9C9DE`, `#F26383`, `#EC9EB4`, `#E485B6`, `#B8507C` |
| 69(ロック) | `#C96C9C` | 2.3% | `#F9C9DE`, `#F26383`, `#EC9EB4`, `#E485B6`, `#B8507C` |
| 72(ナフタ) | `#81A8CC` | 2.8% | `#9BC1E6`, `#A4A2C3`, `#736F9A`, `#E2EBEE`, `#EFEEEE` |
| 73(ナトミ) | `#E58E81` | 2.1% | `#FFA79B`, `#9DB0DB`, `#FF8682`, `#E75E5A`, `#FFD47A` |
| 74(ナナヨ) | `#E9F2FB` | 3.8% | `#C7CDD8`, `#387EB6`, `#8B9BAC`, `#6AA6D7`, `#185EBD` |
| 74(ナナヨ) | `#ABB4BC` | 2.2% | `#C7CDD8`, `#387EB6`, `#8B9BAC`, `#6AA6D7`, `#185EBD` |
| 75(シチゴ) | `#E0D144` | 2.1% | `#FFEE62`, `#F8FFB9`, `#E8F152`, `#BDB949`, `#6F94C8` |
| 76(シチロク) | `#E1E4E6` | 6.6% | `#5B77A8`, `#FCE8EC`, `#FF76A2`, `#9DB0DB`, `#0097C9` |
| 81(ヤイチ) | `#612C26` | 2.5% | `#F9642D`, `#FDAB92`, `#7C4540`, `#D46E87`, `#ED5D47`, `#010000`, `#EE6854` |
| 88(ヤソハチ) | `#FFE8D7` | 4.7% | `#5B77A8`, `#4F506F`, `#FFBFA7`, `#F9642D`, `#E55A52`, `#FF8C36` |
| 92(コトジ) | `#8398C1` | 3.2% | `#9DB0DB`, `#B2AFCF`, `#ABBBDF`, `#CDC7B7`, `#E1DBCB`, `#D9D8E6` |
| 93(クミ) | `#FCFCE8` | 2.6% | `#FFD07D`, `#FFF5E1`, `#9A6A4E`, `#C1A072`, `#F7FFD3`, `#FFD486`, `#FFD995` |
| 000(チトセ) | `#9CA4A9` | 2.1% | `#93999B`, `#85929C`, `#E1DBCC`, `#FECA12`, `#F1F3EE`, `#CEC8B7`, `#D3CEC0` |
| 222(ペルゲン) | `#010000` | 7.1% | `#FFA79B`, `#FFC4B8`, `#EAE5D6`, `#FFF4E6`, `#FFE1C7`, `#F3F1EA`, `#E8E9E3` |
| 444(シテン) | `#A4DAEF` | 6.3% | `#FFD47A`, `#94CDD5`, `#ECAC43`, `#C1A072`, `#C9CDCB`, `#020202` |
| 444(シテン) | `#EDE8DE` | 4.7% | `#FFD47A`, `#94CDD5`, `#ECAC43`, `#C1A072`, `#C9CDCB`, `#020202` |
| 666(リリス) | `#BA5B81` | 2.8% | `#E0B0BD`, `#F26383`, `#C84557`, `#BC8797`, `#B8507C` |
| トレッド 3×11(トリィレブン) | `#FFFF82` | 2.9% | `#FFD58F`, `#F8EC72`, `#FFB1AB`, `#BD8AE6`, `#F85DB3`, `#48D1EC`, `#6AA6D7` |
| 量産型 444(シテン) | `#A4DAEF` | 6.3% | `#FFD47A`, `#94CDD5`, `#B5AD9C`, `#C1A072`, `#C9CDCB`, `#020202` |
| 量産型 444(シテン) | `#EDE8DE` | 4.7% | `#FFD47A`, `#94CDD5`, `#B5AD9C`, `#C1A072`, `#C9CDCB`, `#020202` |

### ColorPalette に見当たらない色（81 件）

画像から読み取れたのに、`ColorPalette` のどの HEX も該当しない色。
**配色検知の取りこぼし候補**（抽出漏れ、または面積比の下限で落ちたもの）。
共通造形色に該当する色（`red orange`, `white`）は設計上 `ColorPalette` へ載らないため除外済み。

| キャラ | 画像から読めた色 | 現在の ColorPalette |
|---|---|---|
| 3(ナオ) | `black` (黒) | `#F8EC72`, `#FFCE2B`, `#FFEE60`, `#F7FFB9`, `#FFBC08`, `#FFBE0E` |
| 4(モチ) | `green` (緑) | `#00B7D9`, `#0097C9`, `#67BDBD`, `#7AD9ED`, `#8DE8ED` |
| 5(イズ) | `gray` (灰) | `#61DAAC`, `#4CD9E8`, `#7FE2C5`, `#009489`, `#408784` |
| 7(ナナ) | `black` (黒) | `#5E7AA9`, `#457AC4`, `#C6C4DD`, `#515271`, `#4447A4` |
| 7(ナナ) | `cyan` (水色) | `#5E7AA9`, `#457AC4`, `#C6C4DD`, `#515271`, `#4447A4` |
| 9(チカ) | `black` (黒) | `#A1A9BF`, `#484551`, `#5F676F`, `#767B7D`, `#D2D7E7`, `#445465`, `#B2AFCF`, `#A5ADC2` |
| 10(ミツル) | `pink` (桃) | `#E85764`, `#81494A`, `#F3DCDF`, `#BB3E45`, `#BE4C5A`, `#BD4756` |
| 11(トウイチ) | `blue` (青) | `#BBC6CB`, `#8B9BAC`, `#BB3E45`, `#C2CCD0`, `#FFAC8F`, `#C6CCD8`, `#E7ECE9` |
| 11(トウイチ) | `orange` (橙) | `#BBC6CB`, `#8B9BAC`, `#BB3E45`, `#C2CCD0`, `#FFAC8F`, `#C6CCD8`, `#E7ECE9` |
| 15(トウゴ) | `orange` (橙) | `#FFB1AB`, `#589D74`, `#FFC4A6`, `#E8EDBE`, `#E85764`, `#FFD7C9` |
| 15(トウゴ) | `pink` (桃) | `#FFB1AB`, `#589D74`, `#FFC4A6`, `#E8EDBE`, `#E85764`, `#FFD7C9` |
| 16(ソロク) | `black` (黒) | `#F26383`, `#6A88C2`, `#A4A2C3`, `#F9BBC1`, `#E25970` |
| 16(ソロク) | `pink` (桃) | `#F26383`, `#6A88C2`, `#A4A2C3`, `#F9BBC1`, `#E25970` |
| 18(トウヤ) | `black` (黒) | `#7C4540`, `#ED5D47`, `#D46E87`, `#FFAC8F`, `#F9642D` |
| 18(トウヤ) | `orange` (橙) | `#7C4540`, `#ED5D47`, `#D46E87`, `#FFAC8F`, `#F9642D` |
| 18(トウヤ) | `pink` (桃) | `#7C4540`, `#ED5D47`, `#D46E87`, `#FFAC8F`, `#F9642D` |
| 19(トク) | `brown` (茶) | `#D07C95`, `#854F50`, `#FFB1AB`, `#423F3F`, `#BB3E45`, `#874545`, `#81494A` |
| 21(ハツヒ) | `black` (黒) | `#FFAC8F`, `#FFEFE3`, `#FFD7C2`, `#FEF3D9`, `#FECF7D` |
| 22(フジ) | `yellow` (黄) | `#FFC879`, `#ABB1B1`, `#FFD07D`, `#CACDCB`, `#FFB42B`, `#FFCD86`, `#FFF4E3` |
| 23(ツグミ) | `black` (黒) | `#7BDEC1`, `#C2F2DE`, `#B1DDA6`, `#F9FF9C`, `#FFF007` |
| 24(フトシ) | `black` (黒) | `#E8AFD8`, `#AEB8DB`, `#FCE8EC`, `#0097C9`, `#C680AF` |
| 25(フィズ) | `blue` (青) | `#A2AFB8`, `#175D7E`, `#7EAEAB`, `#688B8A`, `#D3DBDC`, `#628786` |
| 26(ニロク) | `black` (黒) | `#F9BBC0`, `#F4ABB4`, `#DD7C9C`, `#FFA79B`, `#FFE1EA` |
| 27(ツギナ) | `purple` (紫) | `#E2EBEF`, `#9BC1E6`, `#736E9A`, `#A4A2C3`, `#EFEFEE` |
| 28(ニハチ) | `black` (黒) | `#DB653F`, `#F4F1E5`, `#FF9E68`, `#FFD59B`, `#FFC4A3` |
| 28(ニハチ) | `yellow` (黄) | `#DB653F`, `#F4F1E5`, `#FF9E68`, `#FFD59B`, `#FFC4A3` |
| 31(ミツイ) | `black` (黒) | `#94CDD5`, `#F56D67`, `#5C9ABC`, `#B7DEEC`, `#FFF13A` |
| 32(ミツギ) | `cyan` (水色) | `#C2F2DE`, `#B2DDA7`, `#7BDEC1`, `#FAFE9D`, `#FFF000` |
| 33(ミサ) | `black` (黒) | `#FFA79B`, `#FFD5BD`, `#FFBDA7`, `#FFDECA`, `#FFD9C4`, `#FFE5CE`, `#FFF7F3`, `#FF8FAD` |
| 33(ミサ) | `orange` (橙) | `#FFA79B`, `#FFD5BD`, `#FFBDA7`, `#FFDECA`, `#FFD9C4`, `#FFE5CE`, `#FFF7F3`, `#FF8FAD` |
| 33(ミサ) | `yellow` (黄) | `#FFA79B`, `#FFD5BD`, `#FFBDA7`, `#FFDECA`, `#FFD9C4`, `#FFE5CE`, `#FFF7F3`, `#FF8FAD` |
| 34(サトシ) サンジ | `black` (黒) | `#387EB6`, `#405AB9`, `#A5AFB5`, `#FFCE2B`, `#CACDCC`, `#A4DAEF`, `#4989BC` |
| 36(ミトム) | `black` (黒) | `#FFD58F`, `#FFA79B`, `#FFC4A3`, `#A95C8D`, `#FFA634` |
| 36(ミトム) | `purple` (紫) | `#FFD58F`, `#FFA79B`, `#FFC4A3`, `#A95C8D`, `#FFA634` |
| 37(サナ) | `pink` (桃) | `#FFA79B`, `#9DB0DB`, `#FF8682`, `#E75E5A`, `#FFD47A` |
| 37(サナ) | `yellow` (黄) | `#FFA79B`, `#9DB0DB`, `#FF8682`, `#E75E5A`, `#FFD47A` |
| 39(サク) | `black` (黒) | `#C1A072`, `#9A6A4E`, `#FFF4DF`, `#FFD07D`, `#F6FFD2` |
| 42(ヨツグ) | `black` (黒) | `#E8AFD8`, `#AEB8DB`, `#FCE8EC`, `#EAB5DB`, `#C77FAF`, `#0097C9` |
| 43(シトミ) | `black` (黒) | `#387EB6`, `#405AB9`, `#A2AFB8`, `#FCCD2F`, `#A4DAEF`, `#000001` |
| 44(シトシ) | `black` (黒) | `#B1AA6B`, `#F1E8D4`, `#EEC694`, `#7EAEAB`, `#A4DAEF`, `#FFA457`, `#B3AD70` |
| 44(シトシ) | `green` (緑) | `#B1AA6B`, `#F1E8D4`, `#EEC694`, `#7EAEAB`, `#A4DAEF`, `#FFA457`, `#B3AD70` |
| 47(シナ) | `gray` (灰) | `#387EB6`, `#6AA6D7`, `#185EBD`, `#C7CDD8`, `#8B9BAC` |
| 48(シハチ) | `black` (黒) | `#9EA388`, `#7EAEAB`, `#EF9D46`, `#FFBC08`, `#CACDCB`, `#FFD07D` |
| 49(ヨチカ) | `cyan` (水色) | `#BD8AE6`, `#4378C3`, `#9BC1E6`, `#405AB9`, `#6AA6D7` |
| 50(ナカバ) | `black` (黒) | `#3DD4CF`, `#7BDEC1`, `#C2F2DE`, `#009489`, `#DCF8F3` |
| 58(イソヤ) | `brown` (茶) | `#CACDCB`, `#85E6EA`, `#EF9D46`, `#C48455`, `#02A1C8`, `#00BACB` |
| 61(ロクイチ) 61(ロイ) | `pink` (桃) | `#F26383`, `#6A88C2`, `#A4A2C3`, `#F9BBC1`, `#DC576C` |
| 62(ロジ) | `orange` (橙) | `#F9BCC1`, `#F4ABB4`, `#DD7C9C`, `#FFA79B`, `#FFE2E9` |
| 63(ムツミ) | `black` (黒) | `#FFD998`, `#FFA79B`, `#FFC4A3`, `#A95C8D`, `#FFD07D`, `#FFA634` |
| 64(ムトシ) | `black` (黒) | `#B8507C`, `#6AA6D7`, `#F26383`, `#387EB6`, `#E55951` |
| 66(ムロク) | `black` (黒) | `#6D7880`, `#FFA634`, `#FFC046`, `#F9BBC0`, `#CC8C8C`, `#FF8FAD` |
| 70(ナナト) | `purple` (紫) | `#6B658C`, `#5D6E94`, `#9995B0`, `#5B77A8`, `#504695`, `#9FA7BE` |
| 72(ナフタ) | `black` (黒) | `#9BC1E6`, `#A4A2C3`, `#736F9A`, `#E2EBEE`, `#EFEEEE` |
| 73(ナトミ) | `pink` (桃) | `#FFA79B`, `#9DB0DB`, `#FF8682`, `#E75E5A`, `#FFD47A` |
| 74(ナナヨ) | `gray` (灰) | `#C7CDD8`, `#387EB6`, `#8B9BAC`, `#6AA6D7`, `#185EBD` |
| 78(ナナハ) | `purple` (紫) | `#FF8FAD`, `#FFE1EA`, `#FF9E68`, `#746D9B`, `#FFA79B`, `#6A88C2` |
| 81(ヤイチ) | `black` (黒) | `#F9642D`, `#FDAB92`, `#7C4540`, `#D46E87`, `#ED5D47`, `#010000`, `#EE6854` |
| 81(ヤイチ) | `pink` (桃) | `#F9642D`, `#FDAB92`, `#7C4540`, `#D46E87`, `#ED5D47`, `#010000`, `#EE6854` |
| 84(ヤツヨ) | `gray` (灰) | `#9EA388`, `#EF9D45`, `#FFD07D`, `#FFBC08`, `#7EAEAB` |
| 85(ハッコ) 85(パコ) | `brown` (茶) | `#EF9D46`, `#85E6EA`, `#00BACB`, `#01A1C8`, `#C48455` |
| 88(ヤソハチ) | `black` (黒) | `#5B77A8`, `#4F506F`, `#FFBFA7`, `#F9642D`, `#E55A52`, `#FF8C36` |
| 88(ヤソハチ) | `gray` (灰) | `#5B77A8`, `#4F506F`, `#FFBFA7`, `#F9642D`, `#E55A52`, `#FF8C36` |
| 93(クミ) | `black` (黒) | `#FFD07D`, `#FFF5E1`, `#9A6A4E`, `#C1A072`, `#F7FFD3`, `#FFD486`, `#FFD995` |
| 93(クミ) | `brown` (茶) | `#FFD07D`, `#FFF5E1`, `#9A6A4E`, `#C1A072`, `#F7FFD3`, `#FFD486`, `#FFD995` |
| 93(クミ) | `yellow` (黄) | `#FFD07D`, `#FFF5E1`, `#9A6A4E`, `#C1A072`, `#F7FFD3`, `#FFD486`, `#FFD995` |
| 99(ツクモ) | `black` (黒) | `#D1A8CD`, `#4F506F`, `#E3C2DE`, `#6D7881`, `#CACDCC`, `#959A9D`, `#727D85`, `#C84557` |
| バイナ 2(ツギ) | `black` (黒) | `#FFA558`, `#ADB2B2`, `#FFC4A3`, `#FFDCAE`, `#C9CDCB`, `#EBE5D6`, `#E7E9E4` |
| ディケ 10(ツナイ) | `black` (黒) | `#5F676F`, `#81494A`, `#293B3A`, `#FFCE2B`, `#E85764`, `#F3D8DB` |
| ディケ 10(ツナイ) | `brown` (茶) | `#5F676F`, `#81494A`, `#293B3A`, `#FFCE2B`, `#E85764`, `#F3D8DB` |
| 零 百 | `red` (赤) | `#7EAEAB`, `#E0DBCE`, `#A1A198`, `#628786`, `#95AD72`, `#CDC7B7`, `#F1F3EE` |
| 100(モモ) | `pink` (桃) | `#81494A`, `#F3D8DB` |
| 111(アイズ) | `yellow` (黄) | `#BB3E45`, `#FFAC8F`, `#E7E9E4`, `#CDCCC6`, `#FCBD47`, `#FFD58F` |
| 222(ペルゲン) | `pink` (桃) | `#FFA79B`, `#FFC4B8`, `#EAE5D6`, `#FFF4E6`, `#FFE1C7`, `#F3F1EA`, `#E8E9E3` |
| 222(ドッペル) | `gray` (灰) | `#FFD07D`, `#EAE5D6`, `#FFE2C7`, `#FFF4E4`, `#F7F5EA`, `#E8E9E3` |
| 222(ドッペル) | `yellow` (黄) | `#FFD07D`, `#EAE5D6`, `#FFE2C7`, `#FFF4E4`, `#F7F5EA`, `#E8E9E3` |
| 777(ヨロコビ) | `brown` (茶) | `#C1A072`, `#504695`, `#FFA634`, `#8B9BAC`, `#FFD47A`, `#D0B897` |
| 777(ヨロコビ) | `brown` (茶) | `#C1A072`, `#504695`, `#FFA634`, `#8B9BAC`, `#FFD47A` |
| トレッド 3×11(トリィレブン) | `black` (黒) | `#FFD58F`, `#F8EC72`, `#FFB1AB`, `#BD8AE6`, `#F85DB3`, `#48D1EC`, `#6AA6D7` |
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
