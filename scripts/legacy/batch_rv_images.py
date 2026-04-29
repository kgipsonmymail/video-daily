"""批量生成房车主题图片 - 探索不同风格与情绪"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.minimax_client import MiniMaxClient
from src.image_tasks import run_t2i_task


# 定义房车主题图片：风格 x 情绪 x 细节
RV_IMAGE_PROMPTS = [
    # --- 像素风格 ---
    {
        "variant": "pixel_cozy_evening",
        "prompt": (
            "Pixel art RV interior, retro gaming corner with CRT TV showing 8-bit adventure game, "
            "warm string lights, plush carpet, small plant on windowsill, cozy evening atmosphere, "
            "soft amber lighting, nostalgic and peaceful, detailed pixel art style"
        ),
        "style": "pixel",
        "emotion": "relaxed",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "pixel_apocalypse",
        "prompt": (
            "Pixel art RV stranded in apocalyptic wasteland, dark storm clouds overhead, "
            "flickering fluorescent interior light, dust particles floating, "
            "broken road stretching to horizon, tense and ominous mood, isolated, detailed pixel art"
        ),
        "style": "pixel",
        "emotion": "tense",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "pixel_forest_camp",
        "prompt": (
            "Pixel art RV parked in enchanted forest clearing, mushrooms glowing softly, "
            "fireflies around, friendly forest creatures peeking, moonlight filtering through canopy, "
            "whimsical and adventurous mood, detailed pixel art with vibrant colors"
        ),
        "style": "pixel",
        "emotion": "fun",
        "aspect_ratio": "16:9",
    },

    # --- 游戏/3D风格 ---
    {
        "variant": "game_cyberpunk_rain",
        "prompt": (
            "Unreal Engine 5 rendered RV parked in cyberpunk alley, neon reflections on wet asphalt, "
            "rain dripping from awning, holographic sign glowing above, moody cinematic lighting, "
            "mysterious and intriguing atmosphere, volumetric fog, hyper-detailed 3D game art"
        ),
        "style": "game",
        "emotion": "tense",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "game_roadtrip",
        "prompt": (
            "Stylized 3D cartoon RV driving on endless sunset highway, convertible car alongside, "
            "cactus and desert landscape, adventure vibes, vibrant sunset gradient sky, "
            "playful and exciting mood, Pixar-inspired rendering"
        ),
        "style": "game",
        "emotion": "fun",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "game_coffee_corner",
        "prompt": (
            "3D game engine render of cozy RV kitchen corner, morning sunlight streaming through window, "
            "espresso machine with steam rising, wooden countertop, fresh pastries on plate, "
            "peaceful and inviting, warm color palette, cozy game aesthetic"
        ),
        "style": "game",
        "emotion": "relaxed",
        "aspect_ratio": "9:16",
    },

    # --- 写实风格 ---
    {
        "variant": "real_storm_dashboard",
        "prompt": (
            "Photorealistic RV dashboard view during severe thunderstorm, dramatic lightning illuminating cabin, "
            "rain streaking across windshield, GPS screen glowing blue, hands gripping steering wheel, "
            "intense and tense atmosphere, cinematic nature documentary style"
        ),
        "style": "realistic",
        "emotion": "tense",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "real_campfire_night",
        "prompt": (
            "Photorealistic cozy campsite at night, vintage RV parked beside crackling campfire, "
            "starry Milky Way sky overhead, folding chairs, marshmallows roasting, warm fire glow, "
            "laughter and friendship in the air, nostalgic summer memories"
        ),
        "style": "realistic",
        "emotion": "fun",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "real_mountain_morning",
        "prompt": (
            "Photorealistic RV exterior at mountain meadow sunrise, golden hour light on snow peaks, "
            "mist rising from lake, folding table with breakfast, peaceful solitude, "
            "breathtaking landscape photography style, serene and grounding"
        ),
        "style": "realistic",
        "emotion": "relaxed",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "real_abandoned",
        "prompt": (
            "Photorealistic abandoned RV in overgrown forest, broken windows, nature reclaiming interior, "
            "vines through cracked walls, eerie morning fog, birds in dead trees, "
            "melancholic and abandoned atmosphere, horror movie establishing shot"
        ),
        "style": "realistic",
        "emotion": "tense",
        "aspect_ratio": "16:9",
    },

    # --- 暖心/插画风格 ---
    {
        "variant": "warm_fairy_lights",
        "prompt": (
            "Soft watercolor illustration of RV interior nook, fairy lights strung across ceiling, "
            "cozy knitted blanket on bean bag chair, steaming hot cocoa mug, small bookshelf, "
            "plants in hanging pots, golden hour warmth, ultimate comfort illustration style"
        ),
        "style": "warm",
        "emotion": "relaxed",
        "aspect_ratio": "9:16",
    },
    {
        "variant": "warm_family_journey",
        "prompt": (
            "Warm illustration of family inside RV at sunset, kids playing card games at table, "
            "parent driving and singing along to music, soft warm light through windows, "
            "happiness and togetherness, Studio Ghibli inspired art style, heartwarming scene"
        ),
        "style": "warm",
        "emotion": "fun",
        "aspect_ratio": "16:9",
    },
    {
        "variant": "warm_rainy_reading",
        "prompt": (
            "Cozy illustration of person reading book in RV nook during rainy afternoon, "
            "rain pattering on window, cat curled up nearby, warm lamp light, steaming tea, "
            "tranquil and introspective mood, soft watercolor and gouache painting style"
        ),
        "style": "warm",
        "emotion": "relaxed",
        "aspect_ratio": "9:16",
    },
    {
        "variant": "warm_mysterious",
        "prompt": (
            "Mysterious warm illustration of RV at crossroads desert road at dusk, "
            "signpost pointing different directions, warm lantern glowing inside RV window, "
            "coyote silhouette on horizon, anticipation of journey, cinematic composition"
        ),
        "style": "warm",
        "emotion": "tense",
        "aspect_ratio": "16:9",
    },

    # --- 极简/艺术风格 ---
    {
        "variant": "minimalist_roof_view",
        "prompt": (
            "Minimalist aerial view of RV roof top with solar panels and Starlink dish, "
            "clean geometric lines, matte white surface, blue sky gradient background, "
            "modern and peaceful, architectural illustration style"
        ),
        "style": "minimalist",
        "emotion": "relaxed",
        "aspect_ratio": "1:1",
    },
    {
        "variant": "abstract_interior",
        "prompt": (
            "Abstract art composition of RV interior angles and curves, geometric shapes, "
            "warm terracotta and teal color palette, dramatic shadows, Bauhaus-inspired design, "
            "intellectually intriguing mood, fine art print style"
        ),
        "style": "abstract",
        "emotion": "fun",
        "aspect_ratio": "1:1",
    },
]


def main():
    client = MiniMaxClient()
    print(f"Starting RV theme image generation: {len(RV_IMAGE_PROMPTS)} images")
    print("=" * 60)

    for i, img in enumerate(RV_IMAGE_PROMPTS, 1):
        print(f"\n[{i}/{len(RV_IMAGE_PROMPTS)}] Generating: {img['variant']}")
        print(f"    Style: {img['style']} | Emotion: {img['emotion']}")
        print(f"    Aspect: {img['aspect_ratio']}")

        try:
            paths, run_id = run_t2i_task(
                client=client,
                prompt=img["prompt"],
                variant=img["variant"],
                model="image-01",
                n=1,
                aspect_ratio=img["aspect_ratio"],
                theme="rv-themed",
                prompt_optimizer=False,
            )
            print(f"    SUCCESS: {paths[0]}")
        except Exception as e:
            print(f"    FAILED: {e}")

    print("\n" + "=" * 60)
    print("All generations complete!")


if __name__ == "__main__":
    main()
