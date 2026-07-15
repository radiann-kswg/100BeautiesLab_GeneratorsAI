# lora-refs/corefolder-v1 — 作風LoRA参照画像（A案ワークフロー用）

`--iterate-from` の起点として使う、コアフォルダ作風LoRA (v1) のサンプル出力置き場。

## 出典・生成条件

- 生成元: `NumberTales-GeneratorsAI/assets/lora/samples/ep000004/`（2026-07-14 生成）
- LoRA重み: `nt-corefolder-v1-000004.safetensors`（**エポック4 / 1,784ステップ** — 比較レビューで最良判定）
- ベースモデル: Illustrious-XL v0.1（SDXL系 / Fair AI Public License 1.0-SD）
- 学習データ: `manifest-training.jsonl`（`ai_training.allowed = true` のみ）由来の一次創作コアフォルダ画像178枚。オプトアウト対象は不含。
- 生成プロンプト: `NumberTales-GeneratorsAI/assets/lora/samples/prompts.txt`（トリガーワード `nt-corefolder`）

| ファイル | プロンプト概要 |
|---|---|
| `im_20260714132141_000_478163327.png` | fox ears / multiple tails / smile / white background |
| `im_20260714132149_000_107420369.png` | 1girl / open mouth (:d) / flat color / white background |
| `im_20260714132157_000_1181241943.png` | animal hat / halftone / blue eyes / simple background |

## 使い方

詳細は [`docs/usage-iterate.md`](../../../docs/usage-iterate.md) の「作風LoRA参照画像を起点にする」節を参照。

```powershell
python -m src.pipeline.image_pipeline --num 57 --form corefolder `
    --iterate-from "_ideas/lora-refs/corefolder-v1/im_20260714132141_000_478163327.png" `
    --revisions "扇状に分離した尻尾のシルエットと太い主線・フラットカラーの作風を維持; 番号マーキングは57に" `
    --skip-canva
```

## grayscale/ — 配色引きずり対策版（推奨）

カラー版を参照に使うと、**サンプルの配色（57の定義色ではない）に生成結果が引きずられる**ことが
2026-07-15 の初回運用で確認された。`grayscale/` には彩度を落とした参照画像を置いてあり、
**線の太さ・フラット塗りの質感・尻尾シルエットだけ**を引き継ぎたい場合はこちらを起点にする。

```powershell
python -m src.pipeline.image_pipeline --num 57 --form corefolder `
    --scene "白背景で正面を向いて微笑んでいる" `
    --iterate-from "_ideas/lora-refs/corefolder-v1/grayscale/im_20260714132141_000_478163327_gray.png" `
    --revisions "参照画像からは線の太さ・フラット塗り・扇状の尻尾シルエットのみ引き継ぐ; 配色はDB参照画像([参照画像])の定義に従う; 尻尾は上2束5本+下1束2本の構成で左右反転しない" `
    --skip-canva
```

運用メモ:

- `--scene` は必ず明示する（未指定だと revisions がシーン扱いに流用され、プロンプトの文脈が痩せる）。
- revisions には「引き継ぐもの」と「引き継がないもの」を両方書いて分離を明示する。
- 左右非対称の要素（尻尾の束構成など）は revisions で構成を明記し、Stage 4 の違反修正に拾わせる。

## 注意（ライセンス・遵守）

- 用途は CC BY-NC 4.0 の範囲内（非商用・本人の創作補助）に限る。
- LoRA本体・LoRA出力画像を**公開する場合**は Fair AI Public License 1.0-SD の条項を再確認すること。
- 参照画像はあくまで「作風・シルエットの手掛かり」。キャラクター正確性（不変特徴: 耳・尻尾数・髪色・瞳色）はパイプラインの Stage 2（DB参照）+ Stage 4（違反修正）が担保する。
- 新しい参照画像を追加する場合は、この README の出典対応表に追記すること。
