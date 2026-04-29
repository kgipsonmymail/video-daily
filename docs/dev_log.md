# 开发日志

## 2026-04-29

### 额度系统重构 + 每日界面全模型覆盖 + 音乐模型补全

**背景**：用户发现每日界面缺少 music-2.5、music-cover、lyrics_generation 等模型的额度显示，且全局额度使用记录不完整。

**1. 集中式 QUOTA_BUCKETS 配置**

在 `backend/config.py` 和 `tools/config.py` 中分别定义 `QUOTA_BUCKETS` dict，统一管理所有模型的 `bucket_name` 和 `daily_limit`：

```python
QUOTA_BUCKETS = {
    "image-01": ("image-01", 120),
    "MiniMax-Hailuo-2.3": ("Hailuo-2.3-768P 6s", 2),
    "MiniMax-Hailuo-2.3-Fast": ("Hailuo-2.3-Fast-768P 6s", 2),
    "speech-2.8-hd": ("Text to Speech HD", 11000),
    "music-2.5": ("music-2.5", 4),
    "music-2.6": ("music-2.6", 100),
    "music-cover": ("music-cover", 100),
    "lyrics_generation": ("lyrics_generation", 100),
}
```

新增 `get_quota_bucket(model)` 辅助函数，未知模型返回 `(model, 9999)`。同步移除 Hailuo-02 和 S2V-01（用户无额度）。

**2. 全局额度记录器**

新增 `backend/quota_logger.py`：
- 每次 API 调用同时写 `works/quota_usage_log.jsonl`（append，零成本）和 `quota_usage_log` 表（DB 查询用）
- `source` 字段区分 `backend` / `tools` / `scheduler` / `claude`
- `QuotaUsageLog` 模型定义在 `backend/models.py`（避免重复定义冲突）

**3. 后端路由器更新**

- `backend/routers/generate.py`：`_charge_quota` 改用 `get_quota_bucket()` + `log_quota_usage()`
- `backend/routers/music.py`：同上的完整更新，新增 `/api/music/lyrics` 歌词生成路由
- `backend/routers/audio.py`：T2S 合成后增加额度扣减 + 日志记录

**4. 每日界面展示所有模型**

`backend/routers/quotas.py` 新增两个端点：
- `GET /api/quotas/all`：返回所有已知额度类型（不只在 DB 中有记录的），未创建的返回 `used=0` 占位
- `POST /api/quotas/init`：将所有已知额度类型 Upsert 到 DB

`frontend/src/pages/DailyPage.tsx`：
- 改用 `quotasApi.listAll(TODAY)` 获取完整列表
- 每种额度旁边显示小标签（"字符数/日" / "次数/日"）

**5. 音乐页面补全**

`frontend/src/pages/MusicPage.tsx`：
- `MUSIC_MODELS` 扩展为 4 个：`music-2.6`、`music-2.6-free`、`music-cover`、`music-cover-free`
- 翻唱模型新增"参考音频 URL"输入框
- 新增**歌词生成 Tab**，调用 `POST /api/music/lyrics`，实时显示剩余次数

`backend/routers/music.py`：
- `MusicGenerateRequest` 新增 `audio_url` 字段透传给 music API
- 新增 `POST /api/music/lyrics` 路由：创建 Run → 调用 MiniMax → 保存 txt → 创建 Asset → 扣减额度 → 返回歌词

**6. tools 模块同步**

`tools/config.py`：新增 `QUOTA_BUCKETS` + `get_quota_bucket()` + `log_quota_usage()`（写 JSONL）
`tools/video_tasks.py`、`tools/music_tasks.py`、`tools/image_tasks.py`：改为引用 `tools/config` 中的集中配置

**注意：后端需重启生效。**

---

## 2026-04-28（下午）

### 音频工坊 + 音色批量生成

**背景**：用户需要在音色管理页面新增精细化 T2S 生成能力，并希望一键生成所有未生成的音色。

**新增文件：**
- `backend/routers/audio.py` — `POST /api/audio/generate`，完整透传 T2S HD 所有参数（语速/音量/音调/情绪/音效/采样率/比特率/格式/声道/语言增强/发音规则/水印）。结果写入 `voice_samples` 表
- `frontend/src/api/audio.ts` — 前端 API 封装

**VoicePage 改造：**
- 新增 Tab 切换（"音色预览" | "音频工坊"）
- 音频工坊 Tab：完整参数表单 + 历史记录列表
- 所有音频播放按钮支持暂停/继续（点击播放 → 再次点击暂停 → 再次点击从暂停处继续）
- 音色预览页面播放按钮已升级为 play/pause 语义

**参数表单包含：**
- 文本输入（最长5万字符）
- 音色选择（所有系统音色下拉）
- 语速 [0.5, 2.0] slider
- 音量 [0.1, 10] slider
- 音调 [-12, 12] slider
- 情绪（happy/sad/angry/fearful/disgusted/surprised/calm/fluent）
- 音效（无/spacious_echo/auditorium_echo/lofi_telephone/robotic）
- 采样率/比特率/格式/声道
- 语言增强/发音规则/水印

**一键生成全部音色：**
- 顶部显示已生成/总数（如 `12/48 已生成，36 待生成`）
- 生成中显示进度条 + 当前音色名
- 自动跳过已生成的音色（通过 `samples.some(s => s.voice_id === v.voice_id)` 判断）
- 每个音色最多重试2次，超时等待20秒后重试
- 每次请求超时3分钟（前端 AbortController）
- 间隔 800ms~2300ms 随机延迟避免限流

**后端轮询超时修复：**
- `backend/routers/voices.py` 和 `backend/routers/audio.py`：轮询上限从 60×5s=5分钟提升到 180×5s=15分钟
- 原因：部分音色（如搞笑大爷）MiniMax 处理较慢，超过5分钟会返回 408
- 后端开了 `--reload`，改动自动生效

**验证结果：** 全部 48 个音色一键生成成功

---

## 2026-04-28（傍晚）

### 任务队列 + Daily 页面重构 + FL2V/S2V 移除

**背景**：用户发现任务队列缺少图片上传、每日页面顺序和分组不合理、且 FL2V/S2V 模型不在订阅中。

**任务队列（QueuePage）改造：**
- 新增图片上传按钮（i2i/i2v 任务），支持本地上传和从已有资产选择
- 新增 `AssetPickerDialog` 组件：弹窗网格展示所有图片资产，支持搜索
- 移除 FL2V/S2V 选项（用户只有 Hailuo-2.3 和 Hailuo-2.3-Fast 两个订阅）
- `handleSubmit` 改为 async，先上传文件获取路径再提交任务

**每日页面（DailyPage）重构：**
- 改为「额度卡 → 模型分组 → 折叠 runs 列表」结构
- 每种模型独立折叠/展开
- 额度和 runs 列表联动，used 从实际 runs 统计

**调度器（scheduler.py）扩展：**
- `_run_task()` 支持 i2i/i2v/fl2v/s2v 全部图片类任务
- 新增 `_resolve_image_path()` 辅助函数：支持 base64 Data URL 和文件路径两种格式
- SQL 查询新增 `image`、`image2` 字段
- 临时文件在任务结束后自动清理

**后端改动：**
- `TaskQueue` 模型：新增 `image`、`image2` 字段（存储文件路径或 base64）
- `TaskQueueCreate` schema：新增 `image`、`image2` 可选字段
- `audio.py` `/history` 端点：`response_model=list[VoiceSample]` → `response_model=list[VoiceSampleResponse]`（修复 FastAPI ORM response_model 错误）

**已知问题修复：**
- `create_asset() got unexpected keyword argument 'file_url'`：从所有调用中移除该参数
- 每日额度显示错误：Hailuo-2.3 实际用了 2，image-01 用了 78，通过 SQL 重新计算 `used` 字段
- 后端 CORS：实际是双 uvicorn 进程冲突，杀掉旧进程解决
- start.bat 中文乱码：改用纯 ASCII 英文提示

**数据库清理：**
- 删除 `quotas` 表中 `MiniMax-Hailuo-02` 和 `S2V-01` 行（用户未订阅）

**验证：**
- 前端 i2i/i2v 图片上传和资产选择功能正常
- Daily 页面额度和 runs 分组正常
- 后端启动无报错

---

## 2026-04-28

### 项目目录整理

**背景**：项目经过多轮迭代，存在过时脚本、旧查看器、src/ 与 backend/ 功能重叠等问题，需要整理归档。

**删除的文件（→ scripts/legacy/）：**
- `batch_preview.py`、`batch_rv_images.py`、`batch_rv_v2.py`、`batch_rv_v3.py` — 批量生成脚本
- `migrate_from_sqlite.py`、`migrate_to_mysql.py` — 迁移脚本（一次性使用）
- `test_i2i_music.py` — 测试脚本
- `streamlit_viewer.py` — Streamlit 查看器（已被前端替代）

**目录重组：**
- `src/` → `tools/`（核心 pipeline 代码）
  - `src/config.py` → `tools/config.py`
  - `src/minimax_client.py` → `tools/client.py`
  - `src/db.py` → `tools/db.py`（独立实现，非 backend 数据库转发）
  - `src/image_tasks.py` → `tools/image_tasks.py`
  - `src/video_tasks.py` → `tools/video_tasks.py`
  - `src/music_tasks.py` → `tools/music_tasks.py`
  - `src/scheduler.py` → `tools/scheduler.py`（import 路径已更新）
  - `src/matrix_brainstorm.py` → `tools/matrix_brainstorm.py`
  - `src/main.py` → `tools/pipeline.py`

**文档更新：**
- `docs/structure.md` — 重写，反映 tools/ 架构
- `docs/features.md` — 更新 import 路径和功能说明
- `docs/project_status.md` — 更新已实现模块列表和目录结构
- `docs/CODING_STANDARDS.md` — 更新引用路径
- 新增 `CLAUDE.md` — 项目概览，供 Claude Code 使用

**WCS 文档整理目标**：确保开发时不遗漏重要信息和规则。所有文档现在反映当前真实状态。

---

## 2026-04-25

### 数据库双写问题修复 + 房车主题矩阵生成

**问题发现：**
- 批量生成脚本（`batch_rv_images.py`）写入 SQLite，而 FastAPI 后端读 MySQL
- 前端 API 客户端指向错误端口 8002（另一个项目），应指向 8000
- 29 张图片在 SQLite 中，前端看不到

**修复内容：**
- `src/image_tasks.py`：添加 `use_mysql(True)` 统一写 MySQL
- `src/api/client.ts`：端口 8002 → 8000
- `migrate_to_mysql.py`：将 SQLite 29 条记录迁移到 MySQL
- 后端新增 `prompt_base` 列到 `matrix_configs` 表

**房车主题图片生成：**
- `batch_rv_images.py`：16 张（像素/游戏/写实/暖心多种风格）
- `batch_rv_v2.py`：8 张简化版重新生成
- `batch_rv_v3.py`：5 张极简 prompt 验证
- 结论：MiniMax image-01 对复杂场景渲染不稳定，建议图生图或更简单 prompt

**前端 Lightbox 修复：**
- `frontend/src/components/AssetCard.tsx`
  - 图片从 `width:100vw/height:100vh`（变形）改为 `max-width/max-height:100%`（保持比例）
  - 添加 `useEffect` 监听 ESC 键关闭

**素材矩阵功能增强：**
- 前端 `MatrixPage.tsx`：新增 `promptBaseText` 状态和 Base Prompt 输入框
- 后端 `routers/matrix.py` + `schemas.py`：支持 `prompt_base` 字段读写
- 数据库 `matrix_configs` 表新增 `prompt_base` 列
- 已创建「房车世界 · 6×6 矩阵」配置（ID=5）

---

### 矩阵提示词生成器（头脑风暴 + 质量调整器）

**新增文件：** `tools/matrix_brainstorm.py`

**功能：**
- `MatrixBrainstormer`：输入主题 + 需求 → 输出 N×M 详细提示词矩阵
- `QualityAdjuster`：四档质量预设（minimal/standard/rich/ultra），控制构图/光线/色彩/纹理/情绪等层次
- `MatrixResult`：含 `summary()` 和 `save_to_files()` 方法，可导出 markdown 和 json
- 内置主题库：`房车生活`（25+角度，26种风格）、`巨树世界`、`通用`
- 支持情绪权重：`relaxed` / `tense` / `fun` / `mysterious`
- 支持 `adjust_existing_matrix()` 对已有矩阵重新应用更高质量预设

**使用示例：**
```python
from tools.matrix_brainstorm import MatrixBrainstormer
result = bm.brainstorm(
    theme="房车生活",
    requirements="放松、冒险、温馨、神秘",
    n_subjects=6, n_styles=6,
    quality_preset="rich",
    emotion_weights={"relaxed": 2, "fun": 1, "tense": 1, "mysterious": 1},
)
result.save_to_files("output")
```

---

## 2026-04-24

### 数据库层 + 本地查看 UI

**变更内容：**
- 新增 `tools/db.py`：SQLAlchemy ORM，4 张表（runs / prompts / assets / quotas）
- 更新 `tools/config.py`：新增日期目录结构、数据库路径
- 修复 `tools/client.py`：`create_image_task` 新增 `subject_reference` 参数（图生图支持）
- 重写 `tools/image_tasks.py`：文生图/图生图结果自动写入数据库和新目录结构
- 重写 `tools/video_tasks.py`：4 种视频任务均写入数据库；本地图片自动转 Base64 Data URL 传 API
- 修复 `src/main.py`：修正相对导入（`from .config` 等），`python -m src.main` 可正常执行
- 新增 `tools/pipeline.py`：管线入口（`python tools/pipeline.py`）
- 新增 `requirements.txt` 依赖：`sqlalchemy>=2.0.0`、`streamlit>=1.28.0`

**实际 API 验证（均成功）：**
- 文生图（T2I）：成功，图片已下载（488KB / 534KB）
- 图生图（I2I）：成功，基于文生图结果生成变体
- 文生视频（T2V）：代码已就绪，待额度轮到此任务时验证

**数据库状态（`works/video-daily.db`）：**
- `runs`：1 条（t2i, image-01, success）
- `assets`：2 条（图片，均可正确定位）
- `prompts`：1 条（自动去重）
- `quotas`：1 条（image-01 daily, 120/120）

**目录结构（已落地）：**
```
works/
  video-daily.db
  2026-04-24/
    prompts/t2i/{run_id}.txt
    assets/images/t2i/{run_id}_1.png
    assets/images/t2i/{run_id}_2.png
```

**Streamlit UI：**
- 地址：`streamlit run streamlit_viewer.py`（端口 8501）
- 4 个标签页：资产画廊（支持查看提示词）、运行记录、今日额度、提示词库
- 资产画廊每张图可展开查看完整提示词

**用户确认的每日额度：**
| 模型 | 每日限额 |
|------|---------|
| Hailuo-2.3-768P 6s | 2 |
| Hailuo-2.3-Fast-768P 6s | 2 |
| image-01 | 120 |
| music-2.5 | 4 |
| music-2.6 | 100 |
| music-cover | 100 |
| lyrics_generation | 100 |
| Text to Speech HD | 11000 |

**Bug 修复：**
- Windows 路径分隔符问题：`Path.relative_to()` 换为 `.as_posix()` 存储 DB 路径
- `Streamlit` 内 `text` 变量名与 SQLAlchemy `text()` 函数重名冲突（导致 TypeError）
- `src/main.py` 导入错误（`ModuleNotFoundError`）

**待处理：**
- [ ] 真实视频生成任务端到端验证（额度）
- [ ] 音乐生成（music-2.5/2.6/cover/lyrics）
- [ ] 语音合成（TTS HD）
- [ ] API 文档抓取（prompt.txt 原始需求）

---

## 2026-04-23

### 项目初始化

**变更内容:**
- 创建 `src/` 目录结构（config, minimax_client, video_tasks, image_tasks, main）
- 创建 `docs/` WCS 文档骨架（9 个文档）
- 创建 `works/photo/` 和 `works/video/` 输出目录
- 添加 `.gitignore`（保护 .env 和输出目录）
- 添加 `requirements.txt`（python-dotenv, requests）

**验证依据:**
- 目录结构已创建
- WCS 文档模板已应用

**学习复盘:**
- 项目为海螺视频生成管线，需支持 4 种视频生成任务
- 每日额度有限（2x Hailuo-2.3-Fast-768P，2x Hailuo-2.3-768P），需合理规划任务执行
- 配置通过 .env 文件管理 API Key，与代码分离
- .env 文件和 .claude/settings.local.json 不提交到仓库
- 本地图片可通过 Base64 Data URL 直接传给 API（无需公网 URL）

### 安全审查

**.env 文件:** 已添加到 .gitignore，不会提交
**.claude/settings.local.json:** 已添加到 .gitignore，不会提交
**测试文件:** test_quick.py, test_run.py 不会提交

### 待处理（prompt.txt 扩展任务）

---

## 2026-04-29

### 文件上传架构重构（base64 → 文件路径）

**问题：** 用户上传图片提交 i2i/i2v/fl2v/s2v 任务时，前端将图片转 base64 存数据库（TEXT 字段约 715KB），导致 `DataError: Data too long for column 'image'`。

**根本原因：** `task_queue.image` 字段存的是原始 base64 数据，而不是文件路径。图片数据不应该存数据库。

**解决方案：** 用户上传 → 前端调 `/api/generate/upload` 保存文件到 `works/uploads/` → DB 只存文件路径。

**改动文件：**

- `backend/routers/generate.py` — 新增 `POST /api/generate/upload`，接收 `multipart/form-data`，文件存 `works/uploads/{timestamp}__{uuid}.{ext}`，返回 `{"file_path": "works/uploads/xxx", "url": "/files/works/uploads/xxx"}`
- `frontend/src/api/generate.ts` — 新增 `generateApi.upload(file: File)` 方法
- `frontend/src/pages/QueuePage.tsx` — `handleSubmit` 改用 `generateApi.upload()` 上传文件，拿路径后传给 tasks API，不再转 base64
- `tools/scheduler.py` — `_resolve_image_path` 重写，支持文件路径格式（`works/uploads/xxx`）和旧 base64 格式，返回 `(path, is_temp)` 元组，只删除临时文件（base64 生成的），真实上传文件不删除

**注意：** 重启后端生效。重启命令：
```bash
taskkill //FI "IMAGENAME eq python3.13.exe" //F 2>nul
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

## 2026-04-28（续）

### 矩阵页 prompt_base 逻辑修复

**问题：** 加载 `prompt_base=""` 的配置时，前端 `cfg.prompt_base || TREE_BASE` 因空字符串为 falsy，fallback 到巨树默认描述，导致生成的图片有大树背景。

**根因：** `""` 是 falsy，`"some_value" || fallback` 会正确返回 `"some_value"`，但 `"" || fallback` 会返回 `fallback`。

**修复：** `frontend/src/pages/MatrixPage.tsx` 的 `loadConfig()` 改为：
```typescript
const base = cfg.prompt_base !== undefined
  ? cfg.prompt_base
  : (cfg.theme === "rv-themed" ? RV_BASE : TREE_BASE);
```

**同时修复数据库旧配置：** ID 2 (giant-tree) 和 ID 6 (rv-themed) 的 `prompt_base` 原本为 NULL/空字符串，已补全正确的默认值。

---

---

## 2026-04-28（傍晚）

### 任务队列 + Daily 页面重构 + FL2V/S2V 移除

**背景**：用户发现任务队列缺少图片上传、每日页面顺序和分组不合理、且 FL2V/S2V 模型不在订阅中。

**任务队列（QueuePage）改造：**
- 新增图片上传按钮（i2i/i2v 任务），支持本地上传和从已有资产选择
- 新增 `AssetPickerDialog` 组件：弹窗网格展示所有图片资产，支持搜索
- 移除 FL2V/S2V 选项（用户只有 Hailuo-2.3 和 Hailuo-2.3-Fast 两个订阅）
- `handleSubmit` 改为 async，先上传文件获取路径再提交任务

**每日页面（DailyPage）重构：**
- 改为「额度卡 → 模型分组 → 折叠 runs 列表」结构
- 每种模型独立折叠/展开
- 额度和 runs 列表联动，used 从实际 runs 统计

**调度器（scheduler.py）扩展：**
- `_run_task()` 支持 i2i/i2v/fl2v/s2v 全部图片类任务
- 新增 `_resolve_image_path()` 辅助函数：支持 base64 Data URL 和文件路径两种格式
- SQL 查询新增 `image`、`image2` 字段
- 临时文件在任务结束后自动清理

**后端改动：**
- `TaskQueue` 模型：新增 `image`、`image2` 字段（存储文件路径或 base64）
- `TaskQueueCreate` schema：新增 `image`、`image2` 可选字段
- `audio.py` `/history` 端点：`response_model=list[VoiceSample]` → `response_model=list[VoiceSampleResponse]`（修复 FastAPI ORM response_model 错误）

**已知问题修复：**
- `create_asset() got unexpected keyword argument 'file_url'`：从所有调用中移除该参数
- 每日额度显示错误：Hailuo-2.3 实际用了 2，image-01 用了 78，通过 SQL 重新计算 `used` 字段
- 后端 CORS：实际是双 uvicorn 进程冲突（PID 47084 + 49224），杀掉旧进程解决
- start.bat 中文乱码：改用纯 ASCII 英文提示

**数据库清理：**
- 删除 `quotas` 表中 `MiniMax-Hailuo-02` 和 `S2V-01` 行（用户未订阅）

**验证：**
- 前端 i2i/i2v 图片上传和资产选择功能正常
- Daily 页面额度和 runs 分组正常
- 后端启动无报错（CORS + VoiceSample response_model 均已修复）

---

## 2026-04-29

### 文件上传架构重构（base64 → 文件路径）

**问题：** 用户上传图片提交 i2i/i2v/fl2v/s2v 任务时，前端将图片转 base64 存数据库（TEXT 字段约 715KB），导致 `DataError: Data too long for column 'image'`。

**根本原因：** `task_queue.image` 字段存的是原始 base64 数据，而不是文件路径。图片数据不应该存数据库。

**解决方案：** 用户上传 → 前端调 `/api/generate/upload` 保存文件到 `works/uploads/` → DB 只存文件路径。

**改动文件：**

- `backend/routers/generate.py` — 新增 `POST /api/generate/upload`，接收 `multipart/form-data`，文件存 `works/uploads/{timestamp}__{uuid}.{ext}`，返回 `{"file_path": "works/uploads/xxx", "url": "/files/works/uploads/xxx"}`
- `frontend/src/api/generate.ts` — 新增 `generateApi.upload(file: File)` 方法
- `frontend/src/pages/QueuePage.tsx` — `handleSubmit` 改用 `generateApi.upload()` 上传文件，拿路径后传给 tasks API，不再转 base64
- `tools/scheduler.py` — `_resolve_image_path` 重写，支持文件路径格式（`works/uploads/xxx`）和旧 base64 格式，返回 `(path, is_temp)` 元组，只删除临时文件（base64 生成的），真实上传文件不删除

**注意：** 重启后端生效。重启命令：
```bash
taskkill //FI "IMAGENAME eq python3.13.exe" //F 2>nul
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

## 2026-04-28（续）

### 矩阵页 prompt_base 逻辑修复

**问题：** 加载 `prompt_base=""` 的配置时，前端 `cfg.prompt_base || TREE_BASE` 因空字符串为 falsy，fallback 到巨树默认描述，导致生成的图片有大树背景。

**根因：** `""` 是 falsy，`"some_value" || fallback` 会正确返回 `"some_value"`，但 `"" || fallback` 会返回 `fallback`。

**修复：** `frontend/src/pages/MatrixPage.tsx` 的 `loadConfig()` 改为：
```typescript
const base = cfg.prompt_base !== undefined
  ? cfg.prompt_base
  : (cfg.theme === "rv-themed" ? RV_BASE : TREE_BASE);
```

**同时修复数据库旧配置：** ID 2 (giant-tree) 和 ID 6 (rv-themed) 的 `prompt_base` 原本为 NULL/空字符串，已补全正确的默认值。

---

- 抓取 MiniMax API 文档（text/voice/video/image/music/file 子目录）
- 音乐生成 API 支持
