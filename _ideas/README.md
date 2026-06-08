# \_ideas ディレクトリ

ここにプロンプト草案や生成アイデアを保存します。

例:

- `prompt-draft-57-corefolder.md` — 57(イズナ) コアフォルダ形態のプロンプト草案
- `scene-ideas.md` — 生成したいシーンのアイデア
- `form_common_datasets/Works_NumberTales.json` — 作品別の形態共通特徴データセット（プロンプト組み立て時に自動読込）

## 形態共通データセットの追加

新しい作品を対象にしたい場合は、`form_common_datasets/Works_{作品名}.json` を作成してください。
読込ロジックは `src/utils/dataset.py` の `_load_form_common_dataset(work_key)` にあり、
`FORM_COMMON_DATASET_PATH` (環境変数) → 作品別ファイルの順で解決されます。
