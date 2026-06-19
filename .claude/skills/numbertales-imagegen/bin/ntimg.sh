#!/usr/bin/env bash
# ntimg.sh — numbertales-imagegen launcher (bash / macOS / Cowork サンドボックス)
#
# 役割: パーソナルスキルが任意の cwd から呼ばれても、リポジトリルートを
#       自動解決して image_pipeline などを実行できるようにするラッパー。
#
# リポジトリルート解決順:
#   1. 環境変数 NUMBERTALES_REPO（明示指定。最優先）
#   2. スキル直下 repo_path.txt
#   3. このスクリプト位置から 4 階層上（in-repo / シンボリックリンク配置時）
#   検証: src/pipeline/image_pipeline.py を含むディレクトリのみ採用。
#
# 使い方（例）:
#   ./ntimg.sh --num 57 --form corefolder --skip-canva
#   ./ntimg.sh --natural "コアフォルダ姿の57が図書館で本を読んでいる絵"
#   NT_MODULE=src.batch_generate ./ntimg.sh --nums 15,57 --forms both --dry-run
#
# 既定モジュールは src.pipeline.image_pipeline。環境変数 NT_MODULE で切替可能。
set -euo pipefail

MODULE="${NT_MODULE:-src.pipeline.image_pipeline}"

# スクリプトの絶対ディレクトリ（bin/）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

is_repo() { [ -n "${1:-}" ] && [ -f "$1/src/pipeline/image_pipeline.py" ]; }

REPO=""
# 1) 環境変数
if is_repo "${NUMBERTALES_REPO:-}"; then
    REPO="$(cd "$NUMBERTALES_REPO" && pwd)"
fi
# 2) repo_path.txt
if [ -z "$REPO" ] && [ -f "$SKILL_ROOT/repo_path.txt" ]; then
    CAND="$(tr -d '\r\n' < "$SKILL_ROOT/repo_path.txt")"
    if is_repo "$CAND"; then REPO="$(cd "$CAND" && pwd)"; fi
fi
# 3) スクリプト位置から 4 階層上（bin -> skill -> skills -> .claude -> repo）
if [ -z "$REPO" ]; then
    CAND="$(cd "$SCRIPT_DIR/../../../.." 2>/dev/null && pwd || true)"
    if is_repo "$CAND"; then REPO="$CAND"; fi
fi

if [ -z "$REPO" ]; then
    echo "リポジトリルートを解決できませんでした。次のいずれかで指定してください:" >&2
    echo "  - 環境変数 NUMBERTALES_REPO にリポジトリの絶対パスを設定" >&2
    echo "  - スキル直下に repo_path.txt を作成" >&2
    echo "検証条件: 指定パスの src/pipeline/image_pipeline.py が存在すること。" >&2
    exit 2
fi

# Python 選択（python3 優先）
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "python が見つかりません。" >&2; exit 3; fi

export PROJECT_ROOT="$REPO"
export PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"

echo "[ntimg] repo   = $REPO"
echo "[ntimg] module = $MODULE"
cd "$REPO"
exec "$PY" -m "$MODULE" "$@"
