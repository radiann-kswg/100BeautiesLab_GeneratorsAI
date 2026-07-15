"""
scripts/sdxl_vm/infer_sdxl_lora.py — GCE VM 上で実行する SDXL+LoRA 推論スクリプト
Copyright © RadianN_kswg — CC BY-NC 4.0

src/sdxl/client.py が scp で VM (lora-l4-trial) へ転送して実行する。
ローカルでは実行しない (diffusers + CUDA 前提)。

VM 側の前提 (初回のみ):
    pip install diffusers transformers accelerate safetensors
    # kohya 環境 (02_setup-kohya.sh) と同居可。torch は既存の CUDA 版を使う。

使用法:
    python3 infer_sdxl_lora.py --params sdxl_params.json
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", required=True, help="パラメータ JSON のパス")
    args = parser.parse_args()

    params = json.loads(Path(args.params).read_text(encoding="utf-8"))
    prompt: str = params["prompt"]
    negative: str = params.get("negative", "")
    count: int = int(params.get("count", 3))
    seed = params.get("seed")
    base_model: str = params["base_model"]
    lora: str = params["lora"]
    lora_scale: float = float(params.get("lora_scale", 0.8))
    out_dir = Path(params.get("out", "./out"))
    out_dir.mkdir(parents=True, exist_ok=True)

    import torch
    from diffusers import StableDiffusionXLPipeline

    print(f"[infer] base={base_model}")
    print(f"[infer] lora={lora} (scale={lora_scale})")
    pipe = StableDiffusionXLPipeline.from_single_file(
        base_model, torch_dtype=torch.float16
    ).to("cuda")
    pipe.load_lora_weights(lora)

    generator = None
    if seed is not None:
        generator = torch.Generator(device="cuda").manual_seed(int(seed))

    for i in range(count):
        t0 = time.time()
        image = pipe(
            prompt=prompt,
            negative_prompt=negative,
            num_inference_steps=28,
            guidance_scale=6.0,
            width=1024,
            height=1024,
            cross_attention_kwargs={"scale": lora_scale},
            generator=generator,
        ).images[0]
        dest = out_dir / f"sdxl_rough_{i + 1:02d}.png"
        image.save(dest)
        print(f"[infer] {dest.name} ({time.time() - t0:.1f}s)")

    print(f"[infer] done - {count} 枚を {out_dir} へ保存")


if __name__ == "__main__":
    main()
