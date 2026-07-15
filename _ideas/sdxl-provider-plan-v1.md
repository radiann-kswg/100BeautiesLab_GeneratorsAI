# B案計画書 — SDXL+LoRA プロバイダ (`src/sdxl/`) 新設 v1

作成日: 2026-07-15 ／ 作成: 57(イズナ)
**ステータス: 承認済み・実装済み（2026-07-15）** — 先輩の選択: **B-1 (VM SSHバッチ) × 併走式**。
実装は `src/sdxl/` + `scripts/sdxl_vm/` + `--rough-provider {gemini|sdxl|both}`（docs/usage-generation.md §3-5-3 参照）。
併走式のため Stage 4 は Gemini / SDXL 両方のラフを受け取り、`--rough-provider` で切替も可能。
前提: A案（LoRA参照i2i）は運用開始済み。グレースケール参照で配色引きずりは解消、
左右整合はStage 3修正指示ブロック+Stage 4原典比較チェックで対策済み（2026-07-15実装）。

## 目的

Stage 3（ラフ生成）を Illustrious-XL v0.1 + コアフォルダ作風LoRA
（`nt-corefolder-v1-000004.safetensors`, エポック4）で直接実行できるようにし、
A案の「参照画像経由」より強く・安定して作風を乗せる。

- 配色: LoRA生成時に57の定義色（ブロンド・橙琥珀等）をプロンプト指定 → 色の綱引きが構造的に消える
- Stage 4/5（違反修正・仕上げ）は既存のまま流用 → キャラ正確性の担保は変わらず

## アーキテクチャ（共通部分）

```
src/sdxl/
  __init__.py
  generate.py      # 既存プロバイダと同じCLI/関数シグネチャ (--num/--form/--count/出力規則準拠)
  client.py        # 推論バックエンドへの接続層（方式により実装が変わる）
  prompt_map.py    # Stage 1プロンプト → WD14系タグ列 + trigger word (nt-corefolder) 変換
```

- パイプライン統合: `image_pipeline.py` に `--rough-provider {gemini|sdxl}` を追加し、
  Stage 3 のみ差し替え。Stage 1/2/4/5 は無変更。
- 出力規則: `output/{YYYYMMDD}/{ts}_sdxl_{form}_num{NNN}/` + `prompt.txt`/`run_meta.json`/`notes.md`（既存規約準拠）
- プロンプト変換: Stage 1 の自然文プロンプトをそのまま SDXL に渡すと効きが悪いため、
  `prompt_map.py` で「trigger word + 定義色タグ + シーンタグ」に変換する（LoRA学習時のタグ体系に合わせる）

## 推論バックエンド方式（要選択）

| | B-1: VM SSHバッチ（推奨） | B-2: VM常駐HTTP API | B-3: ローカルGPU |
|---|---|---|---|
| 概要 | 生成毎に `lora-l4-trial` を起動→gcloud sshで推論スクリプト実行→scp回収→停止 | VM上にFastAPI+diffusersを常駐、HTTPで生成要求 | 先輩のPCのGPUでdiffusers直実行 |
| 追加コスト | スポットL4 約$0.3〜0.45/時（使用時のみ） | 同左＋起動しっぱなしリスク | なし |
| レイテンシ | VM起動1〜2分＋生成数十秒 | 生成数十秒（VM起動済み時） | 生成数十秒〜 |
| 実装量 | 小（既存 `assets/lora/scripts` の延長） | 中（API+認証+ファイアウォール） | 小（ただしGPU要件: VRAM 10GB+目安） |
| リスク | gcloud on Windows の癖（PuTTY/クォート→Git Bash経由で回避済みノウハウあり）、スポット在庫 | 止め忘れ課金、公開ポートのセキュリティ | 環境構築・VRAM不足 |

**推奨: B-1 で v1 を作り、回す頻度が上がったら B-2 へ発展。**
（NumberTales側ワークログに VM 運用の落とし穴と対処が全部揃っていて、再現コストが最小のため）

## 実装ステップ（B-1 前提）

1. `src/sdxl/` スケルトン + `prompt_map.py`（タグ変換・定義色の自動注入）
2. VM側推論スクリプト `infer_sdxl_lora.py`（diffusers, LoRA読込, seed固定オプション）
3. `client.py`: VM起動→ssh実行→scp回収→VM停止（`--keep-vm` で停止スキップ）
4. `image_pipeline.py` に `--rough-provider` 追加（既定は gemini、完全後方互換）
5. docs 更新（usage-generation.md のフラグ表 / setup.md の gcloud 前提 / AGENTS.md クイックリファレンス）
6. 検証: 同一シーンで gemini ラフ vs sdxl ラフを Stage 4 通過率・作風で比較

## 課金の安全則

- VM起動を伴う実行は必ず事前に先輩へ RUN 予定を共有（既存の安全則に準拠）
- `client.py` は生成完了時に **必ず stop を試みる**（失敗時は警告を出して手動停止を促す）
- 1回のStage 3実行コスト目安: VM 5〜10分 ≒ 数円〜十数円（スポット時）

## 遵守事項（再確認）

- LoRA・学習データの権利状況は A案時と同一（一次創作・オプトアウト対象不含・CC BY-NC 4.0範囲内）
- 生成物・LoRA本体の公開時は Fair AI Public License 1.0-SD を再確認
- 不変特徴の担保は引き続き Stage 2/4 が担う（SDXLラフはあくまで作風の起点）
