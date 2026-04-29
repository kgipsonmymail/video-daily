# 能力清单

## 视频生成

| 能力 | 模型 | 代码状态 | 真实 API 验证 |
|------|------|---------|--------------|
| 文生视频 | MiniMax-Hailuo-2.3 | ✅ | 待额度 |
| 图生视频 | MiniMax-Hailuo-2.3-Fast | ✅ | 待额度 |
| 首尾帧视频 | MiniMax-Hailuo-02 | ✅ | 待额度 |
| 主体参考视频 | S2V-01 | ✅ | 待额度 |

## 图片生成

| 能力 | 模型 | 代码状态 | 真实 API 验证 |
|------|------|---------|--------------|
| 文生图 | image-01 | ✅ | ✅ 已验证 |
| 图生图 | image-01 | ✅ | ✅ 已验证 |
| 批量生成 | image-01 | ✅ | ✅ 已验证 |
| 矩阵生成 | image-01 | ✅ | ✅ 已验证（前端 6×6 矩阵） |

## 音乐生成

| 能力 | 模型 | 状态 |
|------|------|------|
| 音乐生成 | music-2.6 | ✅ 已实现 |
| 翻唱 | music-cover | 待实现 |
| 歌词生成 | lyrics_generation | 待实现 |

## 语音合成

| 能力 | 模型 | 状态 |
|------|------|------|
| 语音合成 | Text to Speech HD | ✅ 已实现（`backend/routers/audio.py` + `voices.py`）|
| 精细化 T2S 生成（所有参数） | speech-2.8-hd | ✅ 已实现（音频工坊 Tab） |
| 音色设计 | voice design APIs | 待实现 |
| 音色复刻 | voice clone APIs | 待实现 |

## 数据持久化

| 能力 | 状态 |
|------|------|
| MySQL 数据库（runs/prompts/assets/quotas/matrix_configs/task_queue/prompt_history/voice_samples） | ✅ 已实现 |
| SQLite 本地备用 | ✅ 已实现 |
| React 前端 UI（Tasks/Query/Daily/Queue/Matrix/Voice） | ✅ 已实现 |

## 矩阵生成（头脑风暴 + 质量调整器）

| 能力 | 状态 |
|------|------|
| 主题探索：指定主题生成 N×M 详细提示词矩阵 | ✅ 已实现（`tools/matrix_brainstorm.py`） |
| 主体分解：从主题挖掘多个有差异的主体 | ✅ |
| 风格组合：多种艺术风格 + 情绪氛围 × 细节层次 | ✅ |
| 前端 6×6 矩阵：主体×风格 网格生成界面 | ✅ 已验证 |
| 支持自定义 base prompt（所有 cell 共享前缀） | ✅ 后端+前端 |
| Prompt 质量优化：细节丰富度、情绪引导、视觉层次 | ✅ `MatrixBrainstormer.adjust_quality()` |

## 任务队列

| 能力 | 状态 |
|------|------|
| 用户任务提交（结构化表单） | ✅ 已实现 |
| Auto 任务（LLM 生成 prompt） | ✅ 已实现 |
| 每日 8 点调度器（Windows 任务计划程序） | ✅ 已实现 |
| Prompt 历史去重 | ✅ 已实现 |

## 矩阵提示词生成器 (`tools/matrix_brainstorm.py`)

使用方式：
```python
from tools.matrix_brainstorm import MatrixBrainstormer

bm = MatrixBrainstormer()
result = bm.brainstorm(
    theme="房车生活",
    requirements="放松、冒险、温馨、神秘",
    n_subjects=6,
    n_styles=6,
    subjects_detail_level="rich",
    style_detail_level="detailed",
    quality_preset="rich",
    emotion_weights={"relaxed": 2, "tense": 1, "fun": 1, "mysterious": 1},
)
print(result.summary())
result.save_to_files("output")
```

**核心概念：**
- `MatrixBrainstormer.brainstorm()`：输入主题+需求，输出 N×M 矩阵（含主体×风格组合）
- `QualityAdjuster`：将基础 prompt 调整为 minimal / standard / rich / ultra 四个质量级别（构图、光线、色彩、纹理等逐层丰富）
- `MatrixResult`：保存后可导出 `subjects.txt`, `styles.txt`, `matrix.md`, `matrix.json`

**质量预设（QUALITY_PRESETS）：**
| 预设 | 描述 | 长度上限 |
|------|------|---------|
| `minimal` | 简洁描述，适合模型直接使用 | 60 chars |
| `standard` | 标准描述，包含场景和风格 | 120 chars |
| `rich` | 丰富描述，含构图/光线/色彩/纹理 | 200 chars |
| `ultra` | 极致描述，导演级别 | 350 chars |

**主题库（TOPIC_LIBRARIES）：**
- `房车生活`：25 种场景角度 + 26 种艺术风格模板 + 情绪关键词映射
- `巨树世界`：15 种场景角度 + 6 种艺术风格模板 + 情绪关键词
- `通用`：备用基础角度和风格

**情绪权重（emotion_weights）：**
- `relaxed` / `tense` / `fun` / `mysterious`
- 影响 prompt 中情绪关键词的强度和出现概率
- 可通过 `adjust_emotion()` 在已有 prompt 基础上强化特定情绪

**矩阵调整：**
```python
# 对已有矩阵重新应用更高质量预设
new_result = bm.adjust_existing_matrix(result, new_preset="ultra")
```

**内置常量：**
- `GIANT_TREE_PROMPT`：巨树世界默认 prompt
- `GIANT_TREE_SCENES`：6 个场景描述列表