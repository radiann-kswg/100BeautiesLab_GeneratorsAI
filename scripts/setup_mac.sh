#!/usr/bin/env bash
# =============================================================================
# setup_mac.sh — 100BeautiesLab_GeneratorsAI macOS セットアップスクリプト
# Copyright © RadianN_kswg — CC BY-NC 4.0
#
# このMacBookで生成ツールを動かせる状態にするための一発セットアップ。
#   - Python / venv の用意
#   - 依存パッケージのインストール (requirements.txt)
#   - サブモジュール取得 (_creations-ai / _creations-db)
#   - .env の存在チェック (★ .env は作成・上書きしない。鍵は手動設定)
#   - dry-run による動作確認 (API 未呼び出し・課金ゼロ)
#
# 使い方:
#   chmod +x scripts/setup_mac.sh   # 初回のみ
#   ./scripts/setup_mac.sh
#
# オプション:
#   --skip-submodule   サブモジュール取得をスキップ
#   --skip-verify      末尾の dry-run 動作確認をスキップ
#   --recreate-venv    既存 .venv を削除して作り直す
# =============================================================================
set -euo pipefail

# ---- 引数 -------------------------------------------------------------------
SKIP_SUBMODULE=0
SKIP_VERIFY=0
RECREATE_VENV=0
for arg in "$@"; do
  case "$arg" in
    --skip-submodule) SKIP_SUBMODULE=1 ;;
    --skip-verify)    SKIP_VERIFY=1 ;;
    --recreate-venv)  RECREATE_VENV=1 ;;
    -h|--help)
      sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "[WARN] 不明なオプション: $arg" ;;
  esac
done

# ---- 色付きログ -------------------------------------------------------------
c_info()  { printf '\033[36m[INFO]\033[0m %s\n' "$*"; }
c_ok()    { printf '\033[32m[OK]\033[0m %s\n'   "$*"; }
c_warn()  { printf '\033[33m[WARN]\033[0m %s\n' "$*"; }
c_err()   { printf '\033[31m[ERROR]\033[0m %s\n' "$*" >&2; }

# ---- リポジトリルートへ移動 -------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
c_info "リポジトリルート: $REPO_ROOT"

# ---- 0. macOS 前提チェック --------------------------------------------------
if [[ "$(uname)" != "Darwin" ]]; then
  c_warn "macOS 以外で実行されています ($(uname))。基本動作は同じですが本スクリプトは macOS 前提です。"
fi

# ---- 1. Python 検出 ---------------------------------------------------------
PY_BIN=""
for cand in python3.12 python3.11 python3.10 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    ver="$("$cand" -c 'import sys; print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo "0.0")"
    major="${ver%%.*}"; minor="${ver##*.}"
    if [[ "$major" -eq 3 && "$minor" -ge 10 ]]; then
      PY_BIN="$cand"; break
    fi
  fi
done

if [[ -z "$PY_BIN" ]]; then
  c_err "Python 3.10 以上が見つかりません。"
  echo "   Homebrew で導入する例:"
  echo "     /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  echo "     brew install python@3.12"
  exit 1
fi
c_ok "Python 検出: $($PY_BIN --version) ($PY_BIN)"

# ---- 2. venv 作成 -----------------------------------------------------------
if [[ "$RECREATE_VENV" -eq 1 && -d .venv ]]; then
  c_info "--recreate-venv: 既存 .venv を削除します"
  rm -rf .venv
fi
if [[ ! -d .venv ]]; then
  c_info ".venv を作成します"
  "$PY_BIN" -m venv .venv
else
  c_info ".venv は既に存在します (再利用)"
fi
# shellcheck disable=SC1091
source .venv/bin/activate
c_ok "venv 有効化: $(python --version)"

# ---- 3. 依存インストール ----------------------------------------------------
c_info "pip / 依存パッケージを更新します"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
c_ok "依存インストール完了 (requirements.txt)"

# ---- 4. サブモジュール ------------------------------------------------------
if [[ "$SKIP_SUBMODULE" -eq 0 ]]; then
  if [[ -f .gitmodules ]]; then
    c_info "サブモジュールを取得します (_creations-ai / _creations-db)"
    git submodule update --init --recursive || c_warn "サブモジュール取得で警告が出ました。ネットワーク/権限を確認してください。"
    c_ok "サブモジュール処理完了"
  else
    c_warn ".gitmodules が無いためサブモジュール取得をスキップします"
  fi
else
  c_info "--skip-submodule: サブモジュール取得をスキップ"
fi

# ---- 5. .env チェック (★作成・上書きしない) ---------------------------------
# .env は API キーを含む重要ファイル。本スクリプトは絶対に内容を読まず・作らず・上書きしません。
if [[ -f .env ]]; then
  c_ok ".env を検出しました (内容は確認しません)"
else
  c_warn ".env が見つかりません。生成APIを使うには手動で作成が必要です。"
  echo "   雛形をコピーして鍵を埋めてください:"
  echo "     cp .env.example .env"
  echo "   その後 .env を編集し、利用するプロバイダの鍵を設定してください。"
fi

# ---- 6. 動作確認 (dry-run / API 未呼び出し) ---------------------------------
if [[ "$SKIP_VERIFY" -eq 0 ]]; then
  c_info "import チェック"
  python -c "import google.genai, openai, dotenv, requests, PIL; print('  imports OK')"

  c_info "キャラクターレコード読み込みチェック (#57)"
  python -c "from src.utils import find_character; r=find_character(57,'#Works_NumberTales'); print('  Name =', (r or {}).get('data',{}).get('Name','(not found)'))" \
    || c_warn "レコード読み込みに失敗。サブモジュール (_creations-ai/ai-dataset) を確認してください。"

  c_info "batch dry-run (#57 / 課金ゼロ)"
  python -m src.batch_generate --nums 57 --forms both --provider both --dry-run || c_warn "dry-run で警告が出ました。"
  c_ok "動作確認完了"
else
  c_info "--skip-verify: 動作確認をスキップ"
fi

echo ""
c_ok "セットアップ完了！"
echo "  次のステップ:"
echo "    1) source .venv/bin/activate"
echo "    2) .env に API キーを設定 (未設定なら cp .env.example .env)"
echo "    3) python -m src.gemini.generate --num 57 --form corefolder --count 1"
