"""ナンバーテールズ画像生成パイプラインの MCP サーバ。

`src.pipeline.image_pipeline` の各入口を MCP ツールとして公開し、
ローカル / Google Drive / GCS のいずれかへ生成画像を返す。

エントリポイント:
    python -m src.mcp_server.server
"""

__all__ = ["server", "jobs", "output_sink"]
