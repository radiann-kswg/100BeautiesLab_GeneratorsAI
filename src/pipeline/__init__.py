"""
pipeline/ — マルチ LLM 画像・テキスト生成パイプライン
Copyright © RadianN_kswg — CC BY-NC 4.0

ワークフロー (画像):
  Stage 1: OpenAI (GPT-4o) + Gemini でプロンプト加工
  Stage 2: Gemini Imagen + Adobe Firefly でラフ画像生成
  Stage 3: Gemini i2i でキャラデザイン寄せ → Canva でフィニッシング

ワークフロー (テキスト):
  Step 1: OpenAI (GPT-4o) でプライマリ生成
  Step 2: Gemini でクロスレビュー・改善

使用方法:
    python -m src.pipeline.image_pipeline --num 57 --form corefolder
    python -m src.pipeline.text_pipeline  --num 57 --mode scene --prompt "..."
"""

__all__ = [
    "run_image_pipeline",
    "PipelineResult",
    "run_text_pipeline",
]


def __getattr__(name: str):
    if name in ("run_image_pipeline", "PipelineResult"):
        from .image_pipeline import run_image_pipeline, PipelineResult  # noqa: F401
        return {"run_image_pipeline": run_image_pipeline, "PipelineResult": PipelineResult}[name]
    if name == "run_text_pipeline":
        from .text_pipeline import run_text_pipeline  # noqa: F401
        return run_text_pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
