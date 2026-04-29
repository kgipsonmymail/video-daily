"""极简prompt重新生成房车图片"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.minimax_client import MiniMaxClient
from src.image_tasks import run_t2i_task


SIMPLE_PROMPTS = [
    {
        "variant": "rv_sunset_desert",
        "prompt": "A recreational vehicle parked on a desert road at sunset, orange sky, silhouettes of cacti",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "rv_kitchen_interior",
        "prompt": "Inside a small RV, small kitchen with stove and sink, wood panel walls, warm lighting",
        "aspect_ratio": "9:16",
    },
    {
        "variant": "rv_rainy_window",
        "prompt": "View from inside an RV window during rain, water droplets on glass, blurred forest outside",
        "aspect_ratio": "9:16",
    },
    {
        "variant": "rv_stars_camping",
        "prompt": "RV at night in forest campsite, bright stars overhead, campfire burning nearby",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "rv_mountain_lake",
        "prompt": "White RV parked by a clear mountain lake, pine trees, morning mist, peaceful scenery",
        "aspect_ratio": "16:9",
    },
]


def main():
    client = MiniMaxClient()
    print(f"Generating {len(SIMPLE_PROMPTS)} images with simple prompts")
    print("=" * 60)

    for i, img in enumerate(SIMPLE_PROMPTS, 1):
        print(f"\n[{i}/{len(SIMPLE_PROMPTS)}] {img['variant']}")
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
