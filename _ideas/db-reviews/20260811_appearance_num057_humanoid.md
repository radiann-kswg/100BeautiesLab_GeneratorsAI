# AppearanceDetail 照合レビュー — 57(イズナ) / humanoid

- 判定日: 2026-08-11
- 解析モデル: `gpt-4o` (画像解析のみ / 生成は行っていません)
- 参照した公式画像: `cnsp_imgNTS-57.png`, `chr-dsgn_catalogNTS-57.png`
- 画像の選定: typedef `$palette.source` 宣言画像
- 結果: match 9 / **mismatch 0** / unclear 1 (全 10 件)

## 要確認 (mismatch)

なし。画像から確認できた範囲では仕様と矛盾しませんでした。

## 全判定

| # | 判定 | 仕様 (DB) | 所見 |
|---|---|---|---|
| 1 | match | [Arm(Right)] NumberMark: Position=On the armband attached to the right shoulder and upper arm / Color=yellow-green / Notation=Arabic numeral '57' | 右肩と上腕の腕章にアラビア数字の'57'が黄緑色で書かれているのが見える。 |
| 2 | match | [Ear(Both)] Ear: Ear=Fox | 両耳がキツネの耳の形状をしているのが確認できる。 |
| 3 | match | [Hair] Motif: Overview=blonde ponytail | 髪型が金髪のポニーテールであることが確認できる。 |
| 4 | match | [Eye(Both)] Motif: Overview=amber eyes | 目が琥珀色であることが確認できる。 |
| 5 | match | [-] Motif: Overview=yellow blazer | 黄色のブレザーを着用しているのが確認できる。 |
| 6 | unclear | [Leg] CostumeItem: Overview=orange shorts | 画像でショートパンツが判別できない。 |
| 7 | match | [Foot] CostumeItem: Overview=yellow boots | 黄色のブーツを履いているのが確認できる。 |
| 8 | match | [-] Motif: Overview=yellow sailor-collar uniform with white stripes | 白いストライプが入った黄色のセーラー衿の制服を着ていることが確認できる。 |
| 9 | match | [Chest] CostumeItem: Overview=blue inner shirt | 青色のインナーシャツを着ていることが確認できる。 |
| 10 | match | [Shoulder/Arm(Right)] Motif: Overview=armband with number on right shoulder | 右肩に数字が入った腕章が存在することが確認できる。 |

---

*本レビューは AI による画像解析の推定であり、`unclear` は「DB が誤り」ではなく「参照画像からは確認できない」の意味です。最終判断は原典設定を優先してください。*

自動生成: `python -m src.tools.verify_appearance_detail --num 57 --form humanoid` (100BeautiesLab_GeneratorsAI)
