#!/usr/bin/env bash
# setup_gce_vm.sh — GCE VM（Debian 13）に 100BeautiesLab_GeneratorsAI の
# SSH/CLI 実行基盤を作る。VM 上で `bash setup_gce_vm.sh` として実行（sudo 可の自分のユーザー。配置先の所有者もこのユーザー）。
# 何度実行しても壊れない（clone 済みなら pull、venv 済みなら再利用）。
# .env は作らない: 別途 `gcloud compute scp` で /opt/100beautieslab/.env を置く（docs/usage-mcp-multi-llm-gce.md §7.3）。
set -euo pipefail

APP_DIR=/opt/100beautieslab
REPO=https://github.com/radiann-kswg/100BeautiesLab_GeneratorsAI

echo "[1/5] apt: git / python3-venv"
sudo apt-get update -qq
sudo apt-get install -y -qq git python3 python3-venv python3-pip >/dev/null

echo "[2/5] clone or pull -> $APP_DIR (owner: $USER)"
if [ ! -d "$APP_DIR/.git" ]; then
  sudo mkdir -p "$APP_DIR" && sudo chown "$USER:$USER" "$APP_DIR"
  git clone --recurse-submodules --shallow-submodules "$REPO" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only
  git -C "$APP_DIR" submodule update --init --recursive
fi

echo "[3/5] venv + requirements-mcp.txt（Cloud Run と同じ依存セット。Drive シンク含む）"
[ -x "$APP_DIR/.venv/bin/python" ] || python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements-mcp.txt"

echo "[4/5] .env の状態"
if [ -f "$APP_DIR/.env" ]; then
  chmod 600 "$APP_DIR/.env"
  echo "  .env あり（600）。キー名のみ表示:"; grep -o '^[A-Z_]*=' "$APP_DIR/.env" | tr -d '=' | tr '\n' ' '; echo
else
  echo "  .env なし。§7.3 で scp してから再実行すると自己チェックまで通る"
fi

echo "[5/5] 自己チェック（API 未呼び出し・課金ゼロ）"
cd "$APP_DIR"
.venv/bin/python -c "import google.genai, openai, mcp, googleapiclient, dotenv; print('  imports OK')"
.venv/bin/python -m src.pipeline.image_pipeline --help >/dev/null
echo "  image_pipeline --help OK"
.venv/bin/python -m src.pipeline.stage_cli --help >/dev/null
echo "  stage_cli --help OK"
df -h / | tail -1 | awk '{print "  disk used " $3 " / " $2 " (" $5 ")"}'
echo "done. 次: docs/usage-mcp-multi-llm-gce.md §7.3（.env 配置）→ §7.4（dry-run）"
