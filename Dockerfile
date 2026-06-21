# ナンバーテールズ MCP サーバ (Cloud Run / ローカル共通)
FROM python:3.11-slim

# 画像処理(Pillow)・git submodule 参照に必要な最小限のシステム依存
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # Cloud Run は PORT を注入する。ローカルでは 8080 既定。
    PORT=8080 \
    HOST=0.0.0.0 \
    MCP_TRANSPORT=streamable-http \
    # リモート実行では出力をどこかへ返す必要がある（local は手元に届かない）
    OUTPUT_SINK=drive

WORKDIR /app

# 依存を先にインストール（レイヤキャッシュ最適化）
COPY requirements.txt requirements-mcp.txt ./
RUN pip install --upgrade pip && pip install -r requirements-mcp.txt

# アプリ本体
COPY src/ ./src/
COPY _ideas/ ./_ideas/
# 形態共通データセット等の参照に必要な範囲のみ同梱（_creations-ai は別途マウント/同梱）

EXPOSE 8080

# Streamable HTTP で MCP サーバを起動
CMD ["python", "-m", "src.mcp_server.server"]
