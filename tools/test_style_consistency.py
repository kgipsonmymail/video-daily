"""
像素风格 vs 地牢风格 —— 6×6 画风统一性测试
目标: 同一风格列内，6个动物的画风完全一致

画风统一策略:
- 像素风格: 明确像素网格感、颜色数量、复古游戏引擎标识
- 地牢风格: 明确石材质感、光影氛围、黑暗奇幻标识
"""

from tools.client import MiniMaxClient
from tools.config import ensure_dirs, date_dir, assets_dir
from pathlib import Path
import json, random

# ── 6个动物 ───────────────────────────────────────────────────────────────────
SUBJECTS = [
    "A small cute frog with big eyes, bright green color",
    "A tiny round spider, eight eyes, brownish-red color",
    "A small dragon with small wings, purple and gold scales",
    "A little rabbit, long ears, fluffy white fur",
    "A small turtle, green shell with yellow patterns",
    "A cute mouse, pink nose, grey fur, holding a tiny item",
]

# ── 风格1: 像素风格 (Pixel Art) ───────────────────────────────────────────────
PIXEL_STYLE = (
    "pixel art style, 16-bit retro RPG, limited color palette of 16 colors, "
    "sharp square pixels on clear pixel grid, no anti-aliasing, no blur, "
    "flat shading with clear dithering patterns, retro game console look, "
    "NES/SNES era sprite aesthetic, clean edges, visible pixel boundaries"
)

# ── 风格2: 地牢风格 (Dark Dungeon Fantasy) ───────────────────────────────────
DUNGEON_STYLE = (
    "dark fantasy dungeon illustration, hand-painted texture, stone wall background, "
    "moody atmospheric lighting with single torch light source, "
    "rich stone textures, wet floor reflection, medieval RPG game art style, "
    "Warcraft III / Baldur's Gate style, detailed but stylized, "
    "dramatic rim lighting from torch, deep shadows, warm orange and cool blue contrast"
)

STYLES = [
    {"abbr": "像素", "full": PIXEL_STYLE},
    {"abbr": "地牢", "full": DUNGEON_STYLE},
]

# ── 质量预设 ──────────────────────────────────────────────────────────────────
QUALITY_PIXEL = (
    "sharp focus, centered subject, empty dark background for sprite isolation, "
    "classic 16-bit RPG sprite sheet style, clean silhouette readable at small size"
)
QUALITY_DUNGEON = (
    "cinematic composition, subject centered, stone dungeon environment, "
    "moody torch light, highly detailed fantasy art, epic scene"
)


def build_prompt(subject: str, style: dict, quality_extra: str) -> str:
    return f"{subject}, {style['full']}, {quality_extra}"


def save_result(category: str, style_name: str, results: list, prompts: list):
    """保存生成结果到目录"""
    out = assets_dir() / category / style_name
    out.mkdir(parents=True, exist_ok=True)
    (out / "prompts.json").write_text(
        json.dumps({i: p for i, p in enumerate(prompts)}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    for i, url in enumerate(results):
        (out / f"cell_{i:02d}.png").write_text(url + "\n", encoding="utf-8")


def generate_style(client: MiniMaxClient, style: dict, subjects: list,
                   quality_extra: str, category: str) -> list:
    """生成某一风格的6张图（6个动物）"""
    prompts = [build_prompt(s, style, quality_extra) for s in subjects]
    results = []

    print(f"\n{'='*60}")
    print(f"风格: {style['abbr']} — 生成 {len(subjects)} 张")
    print(f"{'='*60}")

    for i, prompt in enumerate(prompts):
        # 截断到1500字符
        prompt = prompt[:1500]
        print(f"  [{i+1}/6] {prompt[:80]}...")

        resp = client.create_image_task(
            model="image-01",
            prompt=prompt,
            aspect_ratio="1:1",
            n=1,
            response_format="url",
        )

        urls = resp.get("data", {}).get("image_urls", [])
        if urls:
            results.append(urls[0])
            print(f"         ✓ {urls[0][:60]}...")
        else:
            print(f"         ✗ Failed: {resp}")
            results.append("")

        # 避免限流
        import time
        time.sleep(2)

    return results


def main():
    ensure_dirs()
    client = MiniMaxClient()
    category = date_dir().name  # e.g. "2026-04-30"

    print("=" * 60)
    print("画风统一性测试 — 像素风格 vs 地牢风格")
    print("6动物 × 2风格 = 12张（先生成像素风格的6张验证统一性）")
    print("=" * 60)

    # Step 1: 先生成像素风格的6张，验证统一性
    pixel_results = generate_style(
        client, STYLES[0], SUBJECTS, QUALITY_PIXEL, category
    )
    save_result(category, "pixel_style_test", pixel_results,
                [build_prompt(s, STYLES[0], QUALITY_PIXEL) for s in SUBJECTS])

    print("\n" + "=" * 60)
    print("像素风格 6 张生成完毕，请检查统一性:")
    print("  → works/{}/pixel_style_test/".format(category))
    print("  → 验收标准: 6张图都是清晰像素风，颜色统一，动物轮廓一致")
    print("=" * 60)

    # Step 2: 生成地牢风格6张
    dungeon_results = generate_style(
        client, STYLES[1], SUBJECTS, QUALITY_DUNGEON, category
    )
    save_result(category, "dungeon_style_test", dungeon_results,
                [build_prompt(s, STYLES[1], QUALITY_DUNGEON) for s in SUBJECTS])

    print("\n" + "=" * 60)
    print("全部12张生成完毕!")
    print("  → works/{}/dungeon_style_test/".format(category))
    print("=" * 60)


if __name__ == "__main__":
    main()