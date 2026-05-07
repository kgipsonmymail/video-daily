"""
矩阵提示词生成器（头脑风暴 + 质量调整器）

用法:
    from src.matrix_brainstorm import MatrixBrainstormer
    bm = MatrixBrainstormer()
    result = bm.brainstorm(
        theme="房车生活",
        requirements="放松、冒险、温馨、神秘",
        n_subjects=6,
        n_styles=6,
        subjects_detail_level="rich",
        style_detail_level="detailed",
        emotion_weights={"relaxed": 2, "tense": 1, "fun": 1, "mysterious": 1},
    )
    result.save_to_files("output")
"""

from dataclasses import dataclass, field
from pathlib import Path
import json


# ─────────────────────────────────────────────────────────────────────────────
# 主题库：预定义各类主题的探索维度
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# 植物主题库：6×6 矩阵主体
# ─────────────────────────────────────────────────────────────────────────────

PLANT_SUBJECTS = {
    "多肉植物": [
        "A cute chubby succulent with plump oval leaves, soft green color with pink tips, symmetric rosette formation, tiny roots visible at base",
        "A rare blue succulent with powdery coating, geometric spiral leaf arrangement, morning dew drops on leaves",
        "A cluster of small succulents in various greens, jade plant variety, compact globular shape, moss around base",
        "A tall cactus with cylindrical arms, bright yellow flowers blooming at top, soft spines, desert pot",
        "A tiny seedlings emerging from soil, two small cotyledon leaves, fresh sprouts, water droplets nearby",
        "A hanging succulent with trailing stems, string of pearls plant, round bead-like leaves, aerial roots",
    ],
    "观叶植物": [
        "A monstera leaf with dramatic splits and holes, deep glossy green, prominent veins, wet with raindrops",
        "A large tropical palm leaf, feathery fronds, vibrant green, gentle curve, isolated on white",
        "A snake plant with tall upright leaves, variegated yellow-green stripes, rigid sword shape, architectural",
        "A fiddle leaf fig with large violin-shaped leaves, dark green, prominent veins, single stem, glossy",
        "A Boston fern with cascading fronds, bright green delicate leaflets, natural arching shape, humid",
        "A golden pothos with heart-shaped leaves, marbled yellow-green variegation, climbing vine habit",
    ],
    "花朵植物": [
        "A single rose in full bloom, velvety red petals, green sepals, dew on petals, soft natural light",
        "A bouquet of wildflowers, daisies and cornflowers mix, soft pastel colors, wild meadow vibes, airy",
        "A sunflower face, large yellow petals radiating, dark brown center seeds, facing viewer directly",
        "A cherry blossom branch, soft pink five-petaled flowers, delicate stamens, spring breeze feeling",
        "A tulip from above, cup-shaped bloom, gradient pink to white, clean white background, symmetrical",
        "A lotus flower emerging from water, pink petals partially open, green pad underneath, serene",
    ],
    "微型景观": [
        "A tiny moss-covered rock in a forest floor setting, various moss types, miniature ferns, dew drops",
        "A miniature landscape in a glass terrarium, tiny hills, small plants, gravel path, cozy enclosed",
        "A single blade of grass with morning dew, macro close-up, water droplet as magnifier, green bokeh",
        "A tiny toadstool mushroom, red cap with white spots, small yellow flowers nearby, fairy garden",
        "A miniature willow tree in bonsai style, gnarled trunk, cascading branches, tiny green leaves",
        "A patch of clover with one four-leaf clover, small white flowers, close ground-level view",
    ],
    "水果蔬菜": [
        "A ripe tomato on the vine, bright red, green calyx, small yellow flowers nearby, garden setting",
        "A bunch of grapes, deep purple-blue, waxy bloom on skin, large leaves behind, classical still life",
        "A single strawberry with seeds, bright red, green hull with small leaves, water droplets, top-down",
        "A cross-section of a citrus fruit, detailed pulp vesicles, bright orange, white pith boundary",
        "A ear of corn, golden yellow kernels, green husk partially removed, rustic, warm lighting",
        "A cabbage with layered leaves, pale green to white gradient, dewdrops on ruffled edges, serene",
    ],
    "藤本攀援": [
        "A climbing ivy vine on a stone wall, dark green lobed leaves, aerial rootlets, aged stone texture",
        "A wisteria branch with hanging purple flower clusters, delicate petals, flowing downward shape",
        "A morning glory flower in full bloom, trumpet-shaped, rich purple-blue, green heart-shaped leaves",
        "A grapevine with curly tendrils, large lobed leaves, small green grapes forming, Tuscan feeling",
        "A sweet pea climbing strings, multicolored pink and white flowers, delicate butterfly shape",
        "A pothos trail descending from top, variegated leaves, aerial roots hanging, architectural",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# 游戏化风格模板库：完整自包含，无随机性
#
# 统一控制变量（每个模板已固定）：
#   BG       — background  : 纯白 / 单色 / 渐变 / 黑背 / 纸背
#   LIGHT    — lighting    : 方向（前/侧/顶/背/环境）+ 硬度（硬/柔/平）
#   SHADOW   — shadows     : 无影 / 柔和 / 硬边
#   ANGLE    — view angle  : 正面 / 3/4 / 等轴 / 俯视
#   ENV      — environment : 孤立(白背) / 置景 / 环境
#   OUTLINE  — outlines    : 无 / 细(1px) / 粗(3px) / 极粗(4px)
#   PALETTE  — color       : 限制色板 / 灰度 / 彩色 / 霓虹
# ─────────────────────────────────────────────────────────────────────────────

GAME_STYLE_TEMPLATES = {
    # ══════════════════════════════════════════════════════════════════════════
    # 像素风格 Pixel Art
    # ══════════════════════════════════════════════════════════════════════════
    "像素-白背-前光-无影-正面-孤立": (
        "pixel art style, pure white background, flat front lighting, "
        "no shadow, centered subject, sprite-sheet front-facing pose, "
        "16-bit retro RPG, limited 16-color palette, sharp square pixels, "
        "no anti-aliasing, no blur, clean pixel grid, NES-SNES era sprite aesthetic"
    ),
    "像素-灰背-前光-无影-正面-孤立": (
        "pixel art style, solid mid-grey background, flat front lighting, "
        "no shadow, centered subject, sprite-sheet front-facing pose, "
        "game-boy era monochrome palette, sharp square pixels, "
        "no anti-aliasing, no blur, clean pixel grid"
    ),
    "像素-白背-侧光-柔影-正面-置景": (
        "pixel art style, pure white background, 45-degree side light from upper-right, "
        "soft penumbra shadow on ground (2px spread), centered subject, front-facing view, "
        "16-bit retro RPG, limited 16-color palette, sharp square pixels, "
        "dithering for shadow gradients, clean silhouette readable at small size"
    ),
    "像素-黑背-背光-无影-正面-孤立": (
        "pixel art style, pure black background, rim lighting from behind creating silhouette outline, "
        "no shadow on black ground, centered subject, front-facing hero pose, "
        "16-bit retro RPG, limited 16-color palette, sharp square pixels, "
        "high contrast silhouette, dramatic black background"
    ),
    # ══════════════════════════════════════════════════════════════════════════
    # 卡通 / 赛璐璐 Cel-Shading
    # ══════════════════════════════════════════════════════════════════════════
    "卡通-白背-前光-无影-正面-孤立": (
        "anime cel-shading style, pure white background, flat front lighting, "
        "no shadow, centered subject, front-facing character pose, "
        "bold black outlines (3px), flat solid color areas, "
        "slightly saturated vibrant colors, clean lineart, "
        "no gradient shading, vector-clean shapes, friendly and approachable"
    ),
    "卡通-白背-侧光-硬边-3/4-置景": (
        "anime cel-shading style, pure white background, 45-degree side light from upper-left, "
        "hard sharp shadow edge on opposite side, centered subject, 3/4 turn view, "
        "bold black outlines (2px), flat solid color areas, "
        "slightly saturated vibrant colors, clean lineart, "
        "clear shadow boundary, game character portrait aesthetic"
    ),
    "卡通-彩背-前光-无影-正面-孤立": (
        "anime cel-shading style, solid bright single-color background (blue), flat front lighting, "
        "no shadow, centered subject, front-facing character pose, "
        "bold black outlines (3px), flat solid color areas, "
        "saturated vibrant colors, clean lineart, "
        "no gradient shading, pop-art game card aesthetic"
    ),
    "卡通-渐变-环境光-柔影-正面-环境": (
        "anime cel-shading style, soft two-tone gradient background (warm peach to sky blue), "
        "soft ambient fill light, gentle ambient occlusion in folds only, "
        "slight shadow beneath subject, centered subject, front-facing pose, "
        "thin black outlines (1px), soft color transitions at shadow boundaries, "
        "vibrant harmonious colors, Studio Ghibli aesthetic"
    ),
    # ══════════════════════════════════════════════════════════════════════════
    # 低多边形 3D Low-Poly 3D
    # ══════════════════════════════════════════════════════════════════════════
    "低多-灰背-顶光-硬影-等轴-置景": (
        "low-poly 3D render style, solid mid-grey background, top-down directional light, "
        "sharp hard shadows at 45-degree angle (no blur), centered subject, true isometric top-down view, "
        "geometric flat-faceted surfaces, each facet a single flat color, "
        "cool neutral palette (slate grey, steel blue, muted teal), "
        "clean hard-edge shadows on flat ground plane, no ambient occlusion, "
        "modern indie game asset aesthetic"
    ),
    "低多-白背-前光-无影-正面-孤立": (
        "low-poly 3D render style, pure white background, flat front lighting, "
        "no shadow, centered subject, front-facing orthographic view, "
        "geometric flat-faceted surfaces, each facet a single flat color, "
        "clean white background, crisp sharp edges, no rounded bevels, "
        "limited palette of 3-4 colors, toy-like minimalist aesthetic"
    ),
    "低多-彩背-顶光-柔影-等轴-置景": (
        "low-poly 3D render style, solid saturated single-color background (warm coral), "
        "top-down light, soft penumbra shadow beneath subject, centered subject, isometric view, "
        "geometric flat-faceted surfaces catching angled light, bright facets vs shadow facets, "
        "vibrant saturated palette, clean modern indie game aesthetic, "
        "soft-edged shadow, no ambient occlusion"
    ),
    "低多-黑背-边光-无影-正面-孤立": (
        "low-poly 3D render style, pure black background, rim edge lighting in white-blue, "
        "no shadow, centered subject, front-facing orthographic view, "
        "geometric flat-faceted silhouette, crisp dark outline against light edges, "
        "monochromatic light grey facets against black, dramatic high-contrast, "
        "character-select screen 3D portrait aesthetic"
    ),
    # ══════════════════════════════════════════════════════════════════════════
    # 平面矢量 / 极简 Flat Vector / Minimalist
    # ══════════════════════════════════════════════════════════════════════════
    "矢量-白背-平光-无影-正面-孤立": (
        "flat vector art style, pure white background, completely flat even front lighting, "
        "no shadow, no gradient, no texture, centered symmetric composition, "
        "orthographic direct front view, thick bold black outlines (4px), "
        "solid flat color fills only, limited 4-color duotone palette, "
        "clean geometric shapes, modern indie mobile game asset aesthetic"
    ),
    "矢量-彩背-平光-无影-正面-孤立": (
        "flat vector art style, solid bright single-color background (warm orange), "
        "completely flat even front lighting, no shadow, no gradient, no texture, "
        "centered symmetric composition, orthographic direct front view, "
        "thick bold black outlines (4px), solid flat color fills only, "
        "warm complementary palette, modern indie mobile game asset aesthetic"
    ),
    "矢量-灰背-侧光-硬影-3/4-置景": (
        "flat vector art style, mid-grey solid background, 45-degree directional light, "
        "hard sharp shadow on opposite side (no blur), centered subject, 3/4 view, "
        "no gradient shading, flat color areas only, bold black outlines (3px), "
        "medium saturated palette, clean graphic design game poster aesthetic"
    ),
    # ══════════════════════════════════════════════════════════════════════════
    # 霓虹 / 赛博朋克 Neon / Cyberpunk
    # ══════════════════════════════════════════════════════════════════════════
    "霓虹-黑背-边光-无影-正面-孤立": (
        "neon wireframe art style, pure black background, glowing cyan and magenta rim edge lighting, "
        "no shadow, centered subject, front-facing orthographic view, "
        "glowing neon outlines on dark solid-fill subject, bloom effect on light edges, "
        "dark subject with neon accent lines only, high contrast black and neon, "
        "retro-futuristic arcade game character select aesthetic"
    ),
    "霓虹-渐变-霓虹-无影-正面-环境": (
        "neon art style, dark purple to black vertical gradient background, "
        "neon pink and cyan practical lights illuminating subject, no shadows, "
        "centered subject, front-facing view, "
        "glowing neon outlines and accent lines on dark fills, bloom on light sources, "
        "dark atmospheric cyberpunk game environment, rain-wet reflective feel"
    ),
    # ══════════════════════════════════════════════════════════════════════════
    # 漫画 / 厚涂 Comic / Painterly
    # ══════════════════════════════════════════════════════════════════════════
    "漫画-白背-戏剧-硬影-正面-置景": (
        "comic book / graphic novel style, pure white background, dramatic single key light from upper-left, "
        "hard crisp shadow edge, deep shadow on opposite side, centered subject, front-facing view, "
        "bold black outlines (4px), halftone dot pattern in shadow areas, "
        "high contrast saturated colors, bold graphic color blocking, "
        "Marvel-DC style dynamic hero shot, no soft gradients"
    ),
    "厚涂-渐变-戏剧-柔影-3/4-环境": (
        "painterly game concept art style, soft gradient background (warm amber to cool grey), "
        "dramatic single directional light, soft feathered shadow edges, "
        "centered subject, 3/4 view with depth, slight atmospheric perspective, "
        "visible brushstroke texture, rich color transitions, "
        "detailed but stylized, AAA game character concept art aesthetic"
    ),
    # ══════════════════════════════════════════════════════════════════════════
    # 水彩 / 艺术插画 Watercolor / Artistic
    # ══════════════════════════════════════════════════════════════════════════
    "水彩-纸背-散射-无影-正面-孤立": (
        "hand-painted watercolor illustration style, off-white textured paper background visible, "
        "soft diffused ambient fill light, no harsh shadows, "
        "loose off-center composition, front-facing pose, "
        "wet-on-wet bleeding edges between colors, desaturated pastel palette, "
        "visible paper grain texture, dreamy gentle indie game aesthetic"
    ),
    "浮世-米背-平光-无影-正面-环境": (
        "Japanese ukiyo-e woodblock print style, warm beige paper background, flat even front lighting, "
        "no shadow, asymmetric composition with generous empty space, traditional Japanese from-above perspective, "
        "bold outlines, flat ink wash areas, muted indigo and cream with vermillion accent, "
        "paper texture visible, traditional Japanese woodblock aesthetic"
    ),
}

# 兼容性别名
UNIFIED_STYLE_TEMPLATES = GAME_STYLE_TEMPLATES


# ─────────────────────────────────────────────────────────────────────────────
# 主题库：预定义各类主题的探索维度
# ─────────────────────────────────────────────────────────────────────────────

TOPIC_LIBRARIES: dict[str, dict] = {
    "房车生活": {
        "angles": [
            "RV exterior at scenic location",
            "RV interior cozy nook",
            "RV kitchen and dining area",
            "RV dashboard and driving view",
            "RV campsite at night",
            "RV adventure on the road",
            "RV parked by water",
            "RV in urban setting",
            "RV off-grid with solar panels",
            "RV wildlife encounter",
            "RV rainy day atmosphere",
            "RV cooking and dining",
            "RV working remotely",
            "RV sunset silhouette",
            "RV mountain retreat",
            "RV desert exploration",
            "RV forest camping",
            "RV beachside parking",
            "RV winter wonderland",
            "RV festival gathering",
            "RV star-gazing setup",
            "RV pet-friendly space",
            "RV family game night",
            "RV morning routine",
            "RV evening cocktail hour",
        ],
        "style_templates": [
            "Photorealistic photography, dramatic natural lighting, ultra detailed, cinematic composition",
            "Pixel art, 16-bit retro RPG style, vibrant colors, nostalgic gaming atmosphere",
            "Studio Ghibli anime style, soft cel shading, warm and whimsical, detailed background",
            "Watercolor illustration, soft brush strokes, dreamy pastel tones, cozy feeling",
            "Cyberpunk neon aesthetic, rain reflections, moody atmospheric lighting, futuristic",
            "Children's book illustration, cute, colorful, playful shapes, warm and friendly",
            "Classical oil painting, rich texture, warm golden light, impressionistic brushwork",
            "Pencil sketch, detailed linework, hatching shading, graphite on paper aesthetic",
            "Anime cel-shading, clean lineart, expressive character, vibrant colors",
            "Minimalist vector art, flat design, limited color palette, geometric shapes",
            "Vintage travel poster style, bold colors, Art Deco influence, retro typography",
            "Low-poly 3D render, geometric shapes, soft gradients, clean modern aesthetic",
            "Double exposure photography, surreal composition, high contrast black and white",
            "Infrared photography style, dreamlike pink foliage, surreal peaceful mood",
            "Tilt-shift miniature photography, selective focus, toy-like world feeling",
            "Dark moody cinematic, desaturated tones, fog, mysterious atmosphere",
            "Bright sunny editorial photography, lifestyle magazine, warm shadows",
            "Nighttime long exposure, star trails above RV, dramatic sky, peaceful solitude",
            "Macro detail shot, shallow depth of field, intimate cozy details",
            "Aerial drone perspective, RV tiny in vast landscape, grandeur of nature",
            "Steampunk interpretation, brass and copper, Victorian adventure aesthetic",
            "Paper craft / papercut art style, layered silhouettes, warm backlighting",
            "Neon wireframe art, dark background, glowing outlines, retro-futuristic",
            "Comic book / graphic novel style, bold halftone dots, dynamic composition",
            "Lo-fi hip hop album cover aesthetic, warm grain, nostalgic peaceful vibes",
            "Japanese woodblock print (ukiyo-e), flat colors, delicate linework, seasonal",
        ],
        "emotion_keywords": {
            "relaxed": ["peaceful", "calm", "serene", "tranquil", "cozy", "comfortable", "laid-back"],
            "tense": ["dramatic", "stormy", "mysterious", "eerie", "claustrophobic", "tense", "ominous"],
            "fun": ["playful", "whimsical", "adventurous", "exciting", "joyful", "lively", "spirited"],
            "mysterious": ["enigmatic", "moody", "foggy", "shadowy", "secret", "unknown", "intriguing"],
        },
    },
    "巨树世界": {
        "angles": [
            "Giant leaf as big as a town, normal-sized plants surrounding",
            "Cottage built inside a giant tree hollow",
            "Mushroom shop in the village market",
            "Rope bridges connecting giant tree branches",
            "Tiny farmer working on a giant leaf field",
            "Bustling market on a giant leaf town square",
            "Leaf spirit creature peeking from bark hollow",
            "Ancient brass compass on worn wooden table",
            "Watchtower built into tree trunk",
            "Waterfall cascading down giant tree roots",
            "Staircase carved into giant tree trunk",
            "Kids playing on giant mushrooms",
            "Lantern festival on giant tree branches at night",
            "Cloud sea viewed from giant tree canopy",
            "Giant tree hollow interior as grand hall",
        ],
        "style_templates": [
            "Fantasy art, vibrant colors, dramatic lighting, highly detailed",
            "Anime cel-shading, clean lineart, expressive character",
            "Soft watercolor painting, pastel tones, dreamy atmosphere",
            "Pixel art, 16-bit retro RPG style, vibrant colors",
            "Classical oil painting, rich texture, warm golden light",
            "Pencil sketch, detailed linework, hatching shading",
        ],
        "emotion_keywords": {
            "relaxed": ["peaceful", "magical", "serene", "cozy", "dreamy"],
            "tense": ["dramatic", "dangerous", "mysterious", "suspenseful"],
            "fun": ["playful", "whimsical", "adventurous", "lively", "colorful"],
            "mysterious": ["enigmatic", "ancient", "secret", "hidden", "foggy"],
        },
    },
    "通用": {
        "angles": [
            "Close-up detail view",
            "Wide establishing shot",
            "Interior cozy atmosphere",
            "Exterior scenic view",
            "Action/movement moment",
            "Quiet/still moment",
            "Contrast: small vs large",
            "Natural light scene",
            "Artificial light scene",
            "Seasonal/time-of-day variation",
        ],
        "style_templates": [
            "Photorealistic photography, natural lighting, ultra detailed",
            "Artistic illustration, vibrant colors, creative composition",
            "Cinematic film still, dramatic lighting, emotional mood",
            "Minimalist design, clean lines, focused subject",
            "Detailed macro view, intimate perspective",
        ],
        "emotion_keywords": {
            "relaxed": ["peaceful", "calm", "serene", "comfortable"],
            "tense": ["dramatic", "intense", "mysterious", "urgent"],
            "fun": ["playful", "whimsical", "joyful", "lively"],
            "mysterious": ["enigmatic", "moody", "shadowy", "intriguing"],
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 质量调整预设
# ─────────────────────────────────────────────────────────────────────────────

QUALITY_PRESETS = {
    "minimal": {
        "description": "简洁描述，适合模型直接使用",
        "add_composition": False,
        "add_lighting": False,
        "add_camera": False,
        "add_color": False,
        "add_detail_level": "basic",
        "add_emotion": False,
        "add_texture": False,
        "length_cap": 60,
    },
    "standard": {
        "description": "标准描述，包含场景和风格",
        "add_composition": True,
        "add_lighting": True,
        "add_camera": False,
        "add_color": False,
        "add_detail_level": "standard",
        "add_emotion": True,
        "add_texture": False,
        "length_cap": 120,
    },
    "rich": {
        "description": "丰富描述，多层次细节，适合探索质量",
        "add_composition": True,
        "add_lighting": True,
        "add_camera": True,
        "add_color": True,
        "add_detail_level": "rich",
        "add_emotion": True,
        "add_texture": True,
        "length_cap": 200,
    },
    "ultra": {
        "description": "极致描述，导演级别，适合精细控制",
        "add_composition": True,
        "add_lighting": True,
        "add_camera": True,
        "add_color": True,
        "add_detail_level": "ultra",
        "add_emotion": True,
        "add_texture": True,
        "length_cap": 350,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 数据结构
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MatrixCell:
    row: int
    col: int
    subject: str
    style: str
    emotion: str | None
    final_prompt: str
    subject_angle: str
    style_keywords: list[str]


@dataclass
class MatrixResult:
    theme: str
    requirements: str
    n_subjects: int
    n_styles: int
    subjects: list[str]
    styles: list[dict]  # {abbr, full, emotion}
    cells: list[MatrixCell]
    base_prompt: str
    metadata: dict = field(default_factory=dict)

    def summary(self) -> str:
        lines = [f"# {self.theme} · {self.n_subjects}×{self.n_styles} 矩阵"]
        lines.append(f"\nBase: {self.base_prompt}")
        lines.append(f"\n## 主体 ({self.n_subjects})")
        for i, s in enumerate(self.subjects):
            lines.append(f"  {i+1}. {s}")
        lines.append(f"\n## 风格 ({self.n_styles})")
        for st in self.styles:
            lines.append(f"  {st['abbr']:12s} → {st['full']}")
        lines.append(f"\n## 矩阵 ({len(self.cells)} cells)")
        return "\n".join(lines)

    def save_to_files(self, out_dir: str | Path):
        """保存到文件：subjects.txt, styles.txt, matrix.md, matrix.json"""
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # subjects.txt
        (out_dir / "subjects.txt").write_text(
            "\n".join(f"{i+1}. {s}" for i, s in enumerate(self.subjects)),
            encoding="utf-8",
        )

        # styles.txt
        (out_dir / "styles.txt").write_text(
            "\n".join(f"{st['abbr']:12s} {st['full']}" for st in self.styles),
            encoding="utf-8",
        )

        # matrix.md
        header = f"# {self.theme} · {self.n_subjects}×{self.n_styles} Matrix\n\n**Base:** {self.base_prompt}\n\n"
        rows = ["| | " + " | ".join(st["abbr"] for st in self.styles) + " |", "|" + "-|" * (self.n_styles + 1)]
        for ri, subj in enumerate(self.subjects):
            cells_in_row = [c for c in self.cells if c.row == ri]
            cell_strs = []
            for ci in range(self.n_styles):
                cell = next((c for c in cells_in_row if c.col == ci), None)
                cell_strs.append(f"**S{ri+1}C{ci+1}**\n{cell.final_prompt[:80]}..." if cell else "—")
            rows.append(f"|*{subj[:30]}*| " + " | ".join(cell_strs) + " |")

        (out_dir / "matrix.md").write_text(header + "\n".join(rows), encoding="utf-8")

        # matrix.json
        (out_dir / "matrix.json").write_text(
            json.dumps(
                {
                    "theme": self.theme,
                    "requirements": self.requirements,
                    "n_subjects": self.n_subjects,
                    "n_styles": self.n_styles,
                    "base_prompt": self.base_prompt,
                    "subjects": self.subjects,
                    "styles": self.styles,
                    "cells": [
                        {
                            "row": c.row, "col": c.col,
                            "subject": c.subject, "style": c.style,
                            "emotion": c.emotion,
                            "prompt": c.final_prompt,
                        }
                        for c in self.cells
                    ],
                },
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )

        print(f"Saved to {out_dir}/")


# ─────────────────────────────────────────────────────────────────────────────
# 质量调整器
# ─────────────────────────────────────────────────────────────────────────────

class QualityAdjuster:
    """将基础 prompt 调整为不同质量级别"""

    COMPOSITIONS = [
        "symmetrical centered composition",
        "rule of thirds, subject off-center",
        "leading lines drawing eye to subject",
        "framing within frame, natural arch",
        "diagonal composition for dynamic tension",
        "layered depth: foreground-midground-background",
        "negative space, minimalist",
        "radial composition from center",
        "dynamic low-angle worm's-eye view",
        "sweeping aerial bird's-eye view",
    ]

    LIGHTING = [
        "golden hour warm sunlight, long shadows",
        "overcast soft diffused light, even exposure",
        "dramatic rim lighting, silhouette backlight",
        "high-key bright fill, cheerful mood",
        "low-key chiaroscuro, deep shadows",
        "volumetric foggy light rays, atmospheric",
        "blue hour cool twilight, peaceful",
        "warm firelight / candlelight, cozy glow",
        "harsh midday sun, strong contrast",
        "studio softbox lighting, clean and flat",
        "practical lights from window, natural",
        "neon and urban light mixing",
    ]

    CAMERAS = [
        "shot on 35mm film, grain and warmth",
        "shot on medium format, shallow depth of field",
        "shot on anamorphic lens, oval bokeh",
        "wide angle 24mm, immersive landscape",
        "telephoto 85mm, creamy bokeh portrait",
        "tilt-shift lens, miniature effect",
        "gooseflesh camera shake, intimate handheld",
        "steady gimbal movement, cinematic glide",
        "macro lens, extreme close-up details",
        "fisheye lens, exaggerated perspective",
    ]

    COLORS = [
        "warm orange and gold color palette",
        "cool blue and teal tones, desaturated",
        "vibrant saturated primaries, bold contrast",
        "muted earth tones, natural and grounded",
        "high contrast black and white monochrome",
        "soft pastel palette, dreamy and gentle",
        "complementary orange and blue contrast",
        "monochromatic green forest tones",
        "vintage faded tones, nostalgic feeling",
        "neon magenta and cyan cyberpunk palette",
        "golden warm sepia tones, memory-like",
        "crisp clean white and grey minimalism",
    ]

    TEXTURES = [
        "rough canvas texture visible in brushstrokes",
        "smooth porcelain-like surface",
        "weathered wood grain, aged patina",
        "glossy wet surface reflecting light",
        "soft fuzzy fabric texture",
        "rough stone rock surface, mineral detail",
        "translucent skin with soft subsurface scattering",
        "metallic chrome reflection",
        "paper / cardboard craft texture",
        "glass refraction with caustics",
        "soft velvet light absorption",
        "scratched vintage metal surface",
    ]

    def __init__(self, preset: str = "standard"):
        self.preset = preset
        self.cfg = QUALITY_PRESETS.get(preset, QUALITY_PRESETS["standard"])

    def adjust(self, subject: str, style: str, emotion: str | None = None) -> str:
        """将主体+风格组合扩展为完整 prompt"""
        parts = [subject.strip(), style.strip()]

        if self.cfg["add_composition"]:
            import random
            parts.append(random.choice(self.COMPOSITIONS))

        if self.cfg["add_lighting"]:
            import random
            parts.append(random.choice(self.LIGHTING))

        if self.cfg["add_camera"]:
            import random
            parts.append(random.choice(self.CAMERAS))

        if self.cfg["add_color"]:
            import random
            parts.append(random.choice(self.COLORS))

        if self.cfg["add_emotion"] and emotion:
            parts.append(f"evoking {emotion} mood and atmosphere")

        if self.cfg["add_texture"]:
            import random
            parts.append(random.choice(self.TEXTURES))

        prompt = ", ".join(parts)

        if self.cfg["length_cap"] and len(prompt) > self.cfg["length_cap"]:
            prompt = prompt[: self.cfg["length_cap"]].rsplit(", ", 1)[0] + "..."

        return prompt

    def enrich_subject(self, subject: str, level: str = "standard") -> str:
        """为主体添加细节层次"""
        enrichments = {
            "basic": subject,
            "standard": subject + ", detailed and realistic",
            "rich": subject + ", intricate details, soft ambient atmosphere, shallow depth of field",
            "ultra": (
                subject
                + ", ultra-detailed, intricate micro-details, "
                + "cinematic atmosphere, volumetric light, "
                + "meticulous textures, 8K resolution, hyperrealistic"
            ),
        }
        return enrichments.get(level, subject)

    def adjust_emotion(self, base_prompt: str, emotion: str, intensity: float = 1.0) -> str:
        """在已有 prompt 基础上强化特定情绪"""
        emotion_map = {
            "relaxed": ("soft", "peaceful", "serene", "warm", "comfortable"),
            "tense": ("dramatic", "urgent", "claustrophobic", "threatening", "high stakes"),
            "fun": ("playful", "whimsical", "joyful", "energetic", "vibrant"),
            "mysterious": ("enigmatic", "shadowy", "foggy", "unknown", "intriguing"),
        }
        keywords = emotion_map.get(emotion, [])

        if intensity >= 1.5:
            qualifiers = [f"strongly evoking {emotion} feeling", f"deeply {keywords[1] if len(keywords) > 1 else emotion} atmosphere"]
            prompt = base_prompt + ", " + ", ".join(qualifiers)
        elif intensity >= 1.0:
            prompt = base_prompt + f", evoking {emotion} mood"
        else:
            prompt = base_prompt  # minimal emotion influence

        return prompt


# ─────────────────────────────────────────────────────────────────────────────
# 矩阵头脑风暴核心
# ─────────────────────────────────────────────────────────────────────────────

class MatrixBrainstormer:
    """
    输入：主题 + 需求（情绪/氛围/画风偏好）
    输出：N×M 提示词矩阵

    使用方法:
        bm = MatrixBrainstormer()
        result = bm.brainstorm(
            theme="房车生活",
            requirements="放松、冒险、温馨、神秘",
            n_subjects=6,
            n_styles=6,
        )
        print(result.summary())
        result.save_to_files("output")
    """

    DEFAULT_SUBJECTS = [
        "RV exterior at mountain lakeside, golden hour light",
        "Cozy RV interior nook with string lights and warm blankets",
        "RV dashboard view during a thunderstorm, lightning flash",
        "RV campsite at night, starry sky and campfire glow",
        "Vintage RV on dramatic desert canyon road at sunset",
        "RV small kitchen corner in morning light, coffee",
    ]

    DEFAULT_STYLES = [
        {"abbr": "写实", "full": "Photorealistic photography, dramatic natural lighting, ultra detailed, national geographic"},
        {"abbr": "像素", "full": "Pixel art, 16-bit retro RPG style, vibrant colors, nostalgic gaming atmosphere"},
        {"abbr": "吉卜力", "full": "Studio Ghibli anime, soft cel shading, warm and whimsical, detailed background"},
        {"abbr": "水彩", "full": "Watercolor illustration, soft brush strokes, dreamy pastel tones, cozy feeling"},
        {"abbr": "赛博", "full": "Cyberpunk neon aesthetic, rain reflections on asphalt, moody atmospheric lighting"},
        {"abbr": "绘本", "full": "Children book illustration style, cute, colorful, playful, warm and friendly"},
    ]

    def __init__(self):
        self._import_random()

    def _import_random(self):
        import random as _random
        self._random = _random

    def brainstorm_unified(
        self,
        theme: str = "植物矩阵",
        subject_category: str = "多肉植物",
        requirements: str = "",
        n_subjects: int = 6,
        n_styles: int = 6,
        emotion_weights: dict[str, float] | None = None,
    ) -> MatrixResult:
        """
        生成统一风格矩阵（无随机性）：主体 × 风格
        使用预定义的 UNIFIED_STYLE_TEMPLATES，每个风格模板已包含完整描述。

        Args:
            theme: 主题名称
            subject_category: PLANT_SUBJECTS 中的主体类别
            requirements: 需求关键词
            n_subjects: 主体数量
            n_styles: 风格数量
            emotion_weights: 情绪权重
        """
        emotion_weights = emotion_weights or {"relaxed": 1, "fun": 1, "tense": 1, "mysterious": 1}
        emotions = list(emotion_weights.keys())

        # 获取植物主体
        plant_groups = PLANT_SUBJECTS.get(subject_category, PLANT_SUBJECTS["多肉植物"])
        subjects = list(plant_groups[:n_subjects])

        # 获取统一风格模板（固定索引分布，覆盖不同风格类别）
        style_keys = list(UNIFIED_STYLE_TEMPLATES.keys())
        # 固定索引：像素(白/黑) / 卡通(白/渐变) / 低多(灰背) / 霓虹(黑背)
        # 覆盖：BG(白/灰/黑/渐变) / LIGHT(前/背/顶/环境) / SHADOW(无/柔/硬) / ANGLE(正面/等轴/3/4)
        fixed_style_indices = [0, 3, 4, 7, 8, 15]
        selected_styles = []
        for i in range(n_styles):
            idx = fixed_style_indices[i] if i < len(fixed_style_indices) else i % len(style_keys)
            key = style_keys[idx]
            abbr = key.split("-")[0] if "-" in key else key[:4]
            selected_styles.append({
                "abbr": abbr,
                "full": UNIFIED_STYLE_TEMPLATES[key],
                "keywords": key,
            })

        # 构建 base_prompt
        base_prompt = f"A beautiful {subject_category} plant, highly detailed, professional product photography"

        # 构建矩阵
        cells: list[MatrixCell] = []
        for ri, subj in enumerate(subjects[:n_subjects]):
            emotion = emotions[ri % len(emotions)]
            enriched_subj = subj

            for ci, style_entry in enumerate(selected_styles[:n_styles]):
                full_style = style_entry["full"]
                final_prompt = f"{enriched_subj}, {full_style}"

                cells.append(
                    MatrixCell(
                        row=ri,
                        col=ci,
                        subject=subj,
                        style=full_style,
                        emotion=emotion,
                        final_prompt=final_prompt,
                        subject_angle=enriched_subj,
                        style_keywords=style_entry.get("keywords", []),
                    )
                )

        return MatrixResult(
            theme=f"{theme} · {subject_category}",
            requirements=requirements,
            n_subjects=min(n_subjects, len(subjects)),
            n_styles=min(n_styles, len(selected_styles)),
            subjects=subjects[:n_subjects],
            styles=selected_styles[:n_styles],
            cells=cells,
            base_prompt=base_prompt,
            metadata={
                "mode": "unified",
                "subject_category": subject_category,
                "emotion_weights": emotion_weights,
            },
        )

    def brainstorm(
        self,
        theme: str,
        requirements: str = "",
        n_subjects: int = 6,
        n_styles: int = 6,
        subjects: list[str] | None = None,
        styles: list[dict] | None = None,
        subjects_detail_level: str = "rich",
        style_detail_level: str = "detailed",
        quality_preset: str = "rich",
        emotion_weights: dict[str, float] | None = None,
        base_prompt: str | None = None,
    ) -> MatrixResult:
        """
        生成 N×M 提示词矩阵

        Args:
            theme: 主题名称，如"房车生活"、"巨树世界"
            requirements: 需求关键词，如"放松、冒险、温馨"
            n_subjects: 主体数量
            n_styles: 风格数量
            subjects: 可选，自定义主体列表（覆盖 n_subjects 自动生成）
            styles: 可选，自定义风格列表
            subjects_detail_level: 主体丰富度 (minimal/standard/rich/ultra)
            style_detail_level: 风格描述详细度
            quality_preset: 质量预设 (minimal/standard/rich/ultra)
            emotion_weights: 情绪权重，dict 如 {"relaxed": 2, "tense": 1}
            base_prompt: 基础场景描述，所有 prompt 共享的前缀
        """
        # 1. 解析情绪权重
        emotion_weights = emotion_weights or {"relaxed": 1, "fun": 1, "tense": 1, "mysterious": 1}
        emotions = list(emotion_weights.keys())

        # 2. 获取或生成主体
        if subjects is None:
            subjects = self._generate_subjects(theme, n_subjects, requirements)

        # 3. 获取或使用自定义风格
        if styles is None:
            styles = self._generate_styles(theme, n_styles, requirements)

        # 4. 生成 base prompt
        if base_prompt is None:
            base_prompt = self._build_base_prompt(theme, requirements)

        # 5. 质量调整器
        adjuster = QualityAdjuster(preset=quality_preset)

        # 6. 构建矩阵
        cells: list[MatrixCell] = []
        for ri, subj in enumerate(subjects[:n_subjects]):
            # 为每行分配一个主要情绪
            emotion = emotions[ri % len(emotions)]

            # 丰富主体描述
            enriched_subj = adjuster.enrich_subject(subj, subjects_detail_level)

            for ci, style_entry in enumerate(styles[:n_styles]):
                full_style = style_entry["full"]

                # 组合最终 prompt
                core_prompt = f"{enriched_subj}, {full_style}"
                final_prompt = adjuster.adjust(core_prompt, full_style, emotion=emotion)
                final_prompt = adjuster.adjust_emotion(final_prompt, emotion, emotion_weights.get(emotion, 1.0))

                cells.append(
                    MatrixCell(
                        row=ri,
                        col=ci,
                        subject=subj,
                        style=full_style,
                        emotion=emotion,
                        final_prompt=final_prompt,
                        subject_angle=enriched_subj,
                        style_keywords=style_entry.get("keywords", []),
                    )
                )

        return MatrixResult(
            theme=theme,
            requirements=requirements,
            n_subjects=min(n_subjects, len(subjects)),
            n_styles=min(n_styles, len(styles)),
            subjects=subjects[: n_subjects],
            styles=styles[: n_styles],
            cells=cells,
            base_prompt=base_prompt,
            metadata={
                "quality_preset": quality_preset,
                "emotion_weights": emotion_weights,
                "subjects_detail_level": subjects_detail_level,
            },
        )

    def _generate_subjects(
        self, theme: str, n: int, requirements: str = ""
    ) -> list[str]:
        """从主题库中提取 + 组合生成多样主体"""
        # 优先从 PLANT_SUBJECTS 获取（植物主题）
        if theme in PLANT_SUBJECTS:
            plants = PLANT_SUBJECTS[theme]
            return list(plants[:n])

        lib = TOPIC_LIBRARIES.get(theme, TOPIC_LIBRARIES["通用"])
        base_angles = lib.get("angles", [])

        # 补齐：如果库不够，随机组合变化
        while len(base_angles) < n:
            import random
            base = random.choice(base_angles)
            variations = [
                f"{base}, early morning mist",
                f"{base}, dramatic sunset",
                f"{base}, rainy day atmosphere",
                f"{base}, under starry night sky",
                f"{base}, snow falling gently",
                f"{base}, golden autumn colors",
            ]
            for v in variations:
                if v not in base_angles:
                    base_angles.append(v)
                    break

        import random

        def time_variation(angle: str) -> str:
            variations = [
                "at golden hour with warm light",
                "at blue hour with cool twilight",
                "at noon with harsh sunlight",
                "at night with soft moonlight",
                "during a rainstorm with wet reflections",
                "during a snowstorm, white silence",
                "at sunrise with pink clouds",
                "at dusk with dramatic clouds",
            ]
            if "night" in requirements.lower() or "星空" in requirements:
                variations = [v for v in variations if "night" in v or "moonlight" in v]
            elif "relaxed" in requirements.lower() or "放松" in requirements:
                variations = [v for v in variations if "golden" in v or "sunrise" in v or "mist" in v]
            return f"{angle}, {random.choice(variations)}"

        subjects = []
        for i in range(n):
            angle = base_angles[i % len(base_angles)]
            subject = time_variation(angle)
            subjects.append(subject)

        random.shuffle(subjects)
        return subjects

    def _generate_styles(
        self, theme: str, n: int, requirements: str = ""
    ) -> list[dict]:
        """从主题库中提取 + 组合生成多样风格"""
        lib = TOPIC_LIBRARIES.get(theme, TOPIC_LIBRARIES["通用"])
        style_templates = lib.get("style_templates", [])

        styles = []
        for i, tmpl in enumerate(style_templates[:n]):
            abbr = tmpl.split(",")[0].strip()[:10]
            styles.append({"abbr": abbr, "full": tmpl, "keywords": tmpl.split(",")})

        # 补齐
        import random

        extras = [
            {"abbr": "写实", "full": "Photorealistic photography, dramatic natural lighting, ultra detailed, cinematic", "keywords": ["photorealistic", "cinematic"]},
            {"abbr": "水彩", "full": "Watercolor illustration, soft brush strokes, dreamy pastel tones, cozy feeling", "keywords": ["watercolor", "pastel"]},
            {"abbr": "赛博", "full": "Cyberpunk neon aesthetic, rain reflections, moody atmospheric lighting", "keywords": ["cyberpunk", "neon"]},
            {"abbr": "绘本", "full": "Children book illustration, cute, colorful, playful, warm and friendly", "keywords": ["illustration", "children"]},
            {"abbr": "素描", "full": "Pencil sketch, detailed linework, hatching shading, graphite aesthetic", "keywords": ["sketch", "linework"]},
            {"abbr": "油画", "full": "Classical oil painting, rich texture, warm golden light, impressionistic", "keywords": ["oil", "painting"]},
            {"abbr": "极简", "full": "Minimalist vector art, flat design, limited color palette, geometric shapes", "keywords": ["minimalist", "vector"]},
            {"abbr": "复古", "full": "Vintage travel poster, bold colors, Art Deco influence, retro typography", "keywords": ["vintage", "retro"]},
        ]

        while len(styles) < n:
            extra = random.choice(extras)
            if extra not in styles:
                styles.append(extra)

        random.shuffle(styles)
        return styles[:n]

    def _build_base_prompt(self, theme: str, requirements: str = "") -> str:
        """根据主题构建 base prompt"""
        base_map = {
            "房车生活": "A recreational vehicle (RV) scene, cinematic composition, highly detailed",
            "巨树世界": "A giant tree world: giant leaf as big as a town, normal-sized plants and trees surrounding",
        }
        # 植物主题
        if theme in PLANT_SUBJECTS:
            return f"A beautiful {theme} plant, highly detailed, professional botanical photography"

        base = base_map.get(theme, f"A {theme} scene, cinematic composition")

        if requirements:
            req_parts = requirements.replace("，", ",").replace("、", ",").split(",")
            mood = req_parts[0].strip() if req_parts else ""
            if mood:
                base += f", {mood} atmosphere"

        return base

    def adjust_existing_matrix(
        self,
        result: MatrixResult,
        new_preset: str = "ultra",
    ) -> MatrixResult:
        """对已有矩阵重新应用质量预设（不改变主体和风格组合）"""
        adjuster = QualityAdjuster(preset=new_preset)
        new_cells = []

        for cell in result.cells:
            new_prompt = adjuster.adjust(
                cell.subject_angle, cell.style, emotion=cell.emotion
            )
            new_prompt = adjuster.adjust_emotion(new_prompt, cell.emotion or "relaxed")
            new_cells.append(
                MatrixCell(
                    row=cell.row, col=cell.col,
                    subject=cell.subject, style=cell.style,
                    emotion=cell.emotion, final_prompt=new_prompt,
                    subject_angle=cell.subject_angle,
                    style_keywords=cell.style_keywords,
                )
            )

        new_result = MatrixResult(
            theme=result.theme,
            requirements=result.requirements,
            n_subjects=result.n_subjects,
            n_styles=result.n_styles,
            subjects=result.subjects,
            styles=result.styles,
            cells=new_cells,
            base_prompt=result.base_prompt,
            metadata={**result.metadata, "quality_preset": new_preset, "readjusted": True},
        )
        return new_result


# ─────────────────────────────────────────────────────────────────────────────
# 快速使用
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    bm = MatrixBrainstormer()

    # ── 方式1：统一风格植物矩阵（推荐，无随机性）───────────────────────────
    result = bm.brainstorm_unified(
        theme="植物矩阵",
        subject_category="多肉植物",
        requirements="可爱、精致、治愈",
        n_subjects=6,
        n_styles=6,
        emotion_weights={"relaxed": 2, "fun": 1, "tense": 1, "mysterious": 1},
    )

    print(result.summary())
    result.save_to_files("works/2026-04-30/矩阵_多肉植物_unified")

    print("\n=== 统一风格 Cell 示例 ===")
    for cell in result.cells[:3]:
        print(f"\n[{cell.row},{cell.col}] ({cell.emotion})")
        print(f"  Subject: {cell.subject[:80]}")
        print(f"  Style: {cell.style[:80]}")
        print(f"  Prompt: {cell.final_prompt[:200]}")

    # ── 方式2：传统随机风格矩阵（保留旧功能）───────────────────────────────
    result2 = bm.brainstorm(
        theme="房车生活",
        requirements="放松、冒险、温馨、神秘",
        n_subjects=6,
        n_styles=6,
        quality_preset="rich",
        emotion_weights={"relaxed": 2, "fun": 1, "tense": 1, "mysterious": 2},
    )

    print("\n\n" + "=" * 60)
    print("传统随机风格矩阵")
    print("=" * 60)
    print(result2.summary())
