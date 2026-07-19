"""
roleplay/ — 上流生成済みロールプレイプロンプトのゲート付き消費。

上流 creations-db の build-roleplay-prompts.mjs が生成した ``roleplay_prompt.md`` を、
manifest レコードの ``roleplay_prompt.path`` から権利軸ゲート付きで読み込む。
src で組み立て直さない（上流の二重実装を避ける）。CLI は ``python -m src.roleplay.export``。
"""
from .resolve import (
    load_roleplay_prompt,
    resolve_roleplay_prompt_path,
)

__all__ = [
    "load_roleplay_prompt",
    "resolve_roleplay_prompt_path",
]
