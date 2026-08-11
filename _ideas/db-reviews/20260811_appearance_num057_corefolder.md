# AppearanceDetail 照合レビュー — 57(イズナ) / corefolder

- 判定日: 2026-08-11
- 解析モデル: `gpt-4o` (画像解析のみ / 生成は行っていません)
- 参照した公式画像: `emstk_corefolderNTS-57-1.png`, `emstk_corefolderNTS-57-2.png`, `cnsp_imgNTS-57.png`
- 画像の選定: typedef `$palette.source` 宣言画像
- 結果: match 5 / **mismatch 0** / unclear 0 (全 5 件)

## 要確認 (mismatch)

なし。画像から確認できた範囲では仕様と矛盾しませんでした。

## 全判定

| # | 判定 | 仕様 (DB) | 所見 |
|---|---|---|---|
| 1 | match | [Arm(Right)] NumberMark: Position=On the armband attached to the right shoulder of the sphere / Color=yellow-green / Notation=Arabic numeral '57' | 右肩のアームバンドにアラビア数字の '57' が緑色で表示されている。 |
| 2 | match | [Ear(Both)] Ear: Ear=Fox | 両耳がキツネの耳の形状になっている。 |
| 3 | match | [Hair] Motif: Overview=blonde ponytail | 金髪のポニーテールが確認できる。 |
| 4 | match | [Eye(Both)] Motif: Overview=amber eyes | 琥珀色の目が確認できる。 |
| 5 | match | [Shoulder/Arm(Right)] Motif: Overview=armband with number on right shoulder | 右肩に番号の付いたアームバンドが確認できる。 |

---

*本レビューは AI による画像解析の推定であり、`unclear` は「DB が誤り」ではなく「参照画像からは確認できない」の意味です。最終判断は原典設定を優先してください。*

自動生成: `python -m src.tools.verify_appearance_detail --num 57 --form corefolder` (100BeautiesLab_GeneratorsAI)
