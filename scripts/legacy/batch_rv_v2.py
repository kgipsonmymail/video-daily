"""重新生成效果不好的房车主题图片 - 简化版 prompt"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.minimax_client import MiniMaxClient
from src.image_tasks import run_t2i_task


REDO_PROMPTS = [
    {
        "variant": "pixel_cozy_v2",
        "prompt": "Pixel art cozy RV interior at night, retro CRT TV glowing blue, string lights, bean bag chair, plants, warm and peaceful",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "pixel_apocalypse_v2",
        "prompt": "Pixel art RV in dark wasteland, storm clouds, cracked road, abandoned buildings, tense atmosphere, dramatic sky",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "cyberpunk_rv_v2",
        "prompt": "RV parked in neon-lit cyberpunk alley at night, rain on ground reflecting neon signs, moody cinematic lighting",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "storm_dashboard_v2",
        "prompt": "Realistic dashboard inside RV during thunderstorm, lightning flash through windshield, rain drops, intense mood",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "minimal_roof_v2",
        "prompt": "Clean minimalist top-down view of RV roof, solar panels, white surface, blue sky, modern design aesthetic",
        "aspect_ratio": "1:1",
    },
    {
        "variant": "coffee_morning_v2",
        "prompt": "Cozy RV kitchen corner in morning light, espresso machine, wooden counter, fresh flowers, warm golden hour sun",
        "aspect_ratio": "9:16",
    },
    {
        "variant": "starry_camp_v2",
        "prompt": "Vintage RV at night beside campfire, star-filled sky with Milky Way, warm fire glow, marshmallows, peaceful",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "forest_rv_v2",
        "prompt": "Colorful pixel art RV in magical forest, glowing mushrooms, fireflies, enchanted atmosphere, whimsical",
        "aspect_ratio": "16:9",
    },
]


def main():
    client = MiniMaxClient()
    print(f"Redoing {len(REDO_PROMPTS)} images with simplified prompts")
    print("=" * 60)

    for i, img in enumerate(REDO_PROMPTS, 1):
        print(f"\n[{i}/{len(REDO_PROMPTS)}] {img['variant']}")
        try:
            paths, run_id = run_t2i_task(
                client=client,
                prompt=img["prompt"],
                variant=img["variant"],
                model="image-01",
                n=1,
                aspect_ratio=img["aspect_ratio"],
                theme="rv-themed",
            )
            print(f"    OK: {paths[0].name}")
        except Exception as e:
            print(f"    FAILED: {e}")

    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
