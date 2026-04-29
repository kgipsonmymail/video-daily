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

    # 示例：房车 6×6 矩阵
    result = bm.brainstorm(
        theme="房车生活",
        requirements="放松、冒险、温馨、神秘",
        n_subjects=6,
        n_styles=6,
        quality_preset="rich",
        emotion_weights={"relaxed": 2, "fun": 1, "tense": 1, "mysterious": 2},
    )

    print(result.summary())
    result.save_to_files("works/matrix_preview")

    print("\n=== 示例 Cell ===")
    for cell in result.cells[:3]:
        print(f"\n[{cell.row},{cell.col}] ({cell.emotion})")
        print(f"  {cell.final_prompt[:200]}")
