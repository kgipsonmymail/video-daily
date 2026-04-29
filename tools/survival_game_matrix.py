"""
生存游戏素材矩阵测试
- 15种主体：动物、植物、昆虫、物资、地形、场景
- 4种画风：真实、像素、动画、简笔画
"""

import sys
sys.path.insert(0, ".")
from tools.matrix_brainstorm import MatrixBrainstormer

# ─── 自定义15种生存游戏主体 ───
SUBJECTS = [
    # 动物 (5)
    "Wild deer drinking at forest stream, alert and watchful",
    "Fierce wild boar charging through tall grass, aggressive pose",
    "Silent grey wolf with glowing eyes, moonlit night background",
    "Eagle soaring high above mountain cliffs, wings spread wide",
    "Rabbits huddling together near cave entrance, snowy winter",

    # 植物 (3)
    "Edible wild berries cluster on green shrub, red and purple",
    "Giant ancient oak tree with thick trunk, forest clearing",
    "Medicinal herbs growing near riverbank, soft green leaves",

    # 昆虫 (2)
    "Bees swarming around honeycomb in hollow tree trunk",
    "Glowing fireflies dancing in dark forest at night",

    # 物资 (2)
    "Wooden crafting materials: logs, stones, and plant fibers",
    "Survival kit with torch, rope, knife, and fishing net",

    # 地形 (2)
    "Dense jungle terrain with thick vines and muddy ground",
    "Rocky mountain cliff with narrow path and deep valley below",

    # 场景 (1)
    "Abandoned survivor camp with tent, dying campfire, foggy dawn",
]

# ─── 自定义4种生存游戏画风 ───
STYLES = [
    {
        "abbr": "写实",
        "full": "Photorealistic, ultra-detailed textures, cinematic natural lighting, wildlife photography style",
        "keywords": ["photorealistic", "cinematic", "natural"],
    },
    {
        "abbr": "像素",
        "full": "Pixel art, 16-bit retro game style, vibrant colors, nostalgic survival game atmosphere, isometric perspective",
        "keywords": ["pixel", "retro", "16-bit"],
    },
    {
        "abbr": "动画",
        "full": "Studio Ghibli anime cel-shading, expressive, warm and detailed background, soft color palette, whimsical",
        "keywords": ["anime", "cel-shading", "ghibli"],
    },
    {
        "abbr": "简笔",
        "full": "Simple line drawing illustration, minimalist ink sketch style, clean outlines, white background, sketchbook aesthetic",
        "keywords": ["sketch", "line", "minimalist"],
    },
]


def main():
    bm = MatrixBrainstormer()

    result = bm.brainstorm(
        theme="生存游戏素材测试",
        requirements="真实、沉浸、生存、荒野",
        n_subjects=15,
        n_styles=4,
        subjects=SUBJECTS,
        styles=STYLES,
        subjects_detail_level="rich",
        quality_preset="rich",
        emotion_weights={"relaxed": 1, "tense": 2, "fun": 1, "mysterious": 1},
        base_prompt="Survival game material asset, high quality game art, 2D illustration",
    )

    output_dir = "works/survival_game_matrix"
    result.save_to_files(output_dir)

    # ─── 打印完整矩阵预览 ───
    print("\n" + "=" * 80)
    print(f"生存游戏素材矩阵 · {result.n_subjects}×{result.n_styles} ({len(result.cells)} cells)")
    print("=" * 80)

    print("\n【主体列表】")
    for i, s in enumerate(result.subjects):
        print(f"  {i+1:2d}. {s}")

    print("\n【画风列表】")
    for st in result.styles:
        print(f"  {st['abbr']:4s} → {st['full'][:60]}...")

    print("\n【完整矩阵 Prompt】")
    print("-" * 80)

    # 按画风列分组显示
    style_names = [st["abbr"] for st in result.styles]
    header = f"{'主体':<35s}" + "".join(f"{s:^20s}" for s in style_names)
    print(header)
    print("-" * 80)

    for ri, subj in enumerate(result.subjects):
        subj_short = subj[:33] + ".." if len(subj) > 35 else subj
        row_parts = [f"{subj_short:<35s}"]

        for ci in range(result.n_styles):
            cell = next((c for c in result.cells if c.row == ri and c.col == ci), None)
            if cell:
                # 截断到合适长度
                prompt = cell.final_prompt[:50] + "..." if len(cell.final_prompt) > 50 else cell.final_prompt
                row_parts.append(f"[{ri+1:02d},{ci+1}] {prompt[:25]}...")
            else:
                row_parts.append("—")
        print("".join(row_parts))

    print("\n【全部 Prompt 详情】")
    print("-" * 80)
    for cell in result.cells:
        print(f"\n[{cell.row+1:02d},{cell.col+1}] {result.subjects[cell.row][:50]}")
        print(f"     画风: {cell.style[:50]}...")
        print(f"     Prompt: {cell.final_prompt}")

    print(f"\n\n已保存到: {output_dir}/")
    return result


if __name__ == "__main__":
    main()
