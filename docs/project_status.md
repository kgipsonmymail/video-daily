# 项目状态

## 技术栈

- **后端**: FastAPI (端口 8000) + SQLAlchemy + MySQL
- **前端**: React 18 + Vite + React Router + React Query + Axios (端口 5173)
- **工具模块**: Python (tools/) — scheduler、pipeline、矩阵生成
- **数据库**: MySQL (主) + SQLite (本地备用)
- **调度**: Windows 任务计划程序 → 每日 8 点触发 `tools/scheduler.py`

## 系统架构

```
浏览器 (5173) ←→ React 前端 ←→ FastAPI 后端 (8000) ←→ MySQL (阿里云)
                          ↓
                   MiniMax API (生成内容)
                          ↓
                    文件写入 works/
```

## 数据库（MySQL）

- 连接参数：`.env` 中 `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD`
- ORM via SQLAlchemy：`tools/db.py`，调用 `use_mysql(True)` 切到 MySQL
- 表：`runs`, `prompts`, `assets`, `quotas`, `matrix_configs`, `task_queue`, `prompt_history`, `voice_samples`, `quota_usage_log`

## 已实现模块

| 文件 | 说明 |
|------|------|
| `tools/config.py` | 配置管理（API Key、路径、日期目录） |
| `tools/client.py` | MiniMax API 客户端封装 |
| `tools/db.py` | SQLAlchemy ORM（MySQL + SQLite 双模式，`use_mysql()` 切换） |
| `tools/image_tasks.py` | 文生图 / 图生图（含 DB 写入，默认写 MySQL） |
| `tools/video_tasks.py` | 文生视频 / 图生视频 / 首尾帧 / 主体参考（含 DB 写入） |
| `tools/music_tasks.py` | 音乐生成任务（含 DB 写入） |
| `tools/scheduler.py` | 每日 8 点调度器 |
| `tools/matrix_brainstorm.py` | 矩阵提示词生成器（头脑风暴 + 质量调整器） |
| `backend/main.py` | FastAPI 后端入口（`uvicorn backend.main:app --port 8000`） |
| `backend/routers/generate.py` | `POST /api/generate/image`（图生图）、`POST /api/generate/upload`（上传参考图，存 `works/uploads/`） |
| `backend/routers/music.py` | `POST /api/music/generate`（音乐生成）、`POST /api/music/lyrics`（歌词生成，含 Run/Asset/txt 记录） |
| `backend/routers/audio.py` | 音频工坊 `POST /api/audio/generate`（完整 T2S HD 参数） |
| `backend/routers/quotas.py` | `GET /api/quotas/all`（全模型列表含未记录）、`POST /api/quotas/init`（初始化当天额度） |
| `backend/quota_logger.py` | 全局额度记录器，写入 `quota_usage_log` 表 + `works/quota_usage_log.jsonl` |
| `frontend/` | React + Vite 前端（`npm run dev`，端口 5173） |

## 每日额度（已确认）

### 图片生成
| 模型 | 每日限额 |
|------|---------|
| `image-01` | 120 |

### 视频生成
| 模型 | 限额/日 | 用途 |
|------|---------|------|
| `MiniMax-Hailuo-2.3` (T2V) | 2 | 文生视频 |
| `MiniMax-Hailuo-2.3-Fast` (I2V) | 2 | 图生视频 |

### 音乐生成
| 模型 | 限额/日 |
|------|---------|
| `music-2.6` | 100 |
| `music-2.6-free` | 4 |
| `music-cover` | 100 |
| `music-cover-free` | 4 |
| `lyrics_generation` | 100 |

### 语音合成
| 模型 | 限额/日 |
|------|---------|
| Text to Speech HD | 11000 |

## 目录结构

```
video-daily/
├── tools/
│   ├── config.py            # 路径 + API 配置
│   ├── client.py             # MiniMax HTTP 客户端
│   ├── db.py                 # SQLAlchemy ORM（MySQL/SQLite 双模式）
│   ├── image_tasks.py        # 文生图 / 图生图（默认写 MySQL）
│   ├── video_tasks.py        # 文生视频 / 图生视频 / 首尾帧 / 主体参考
│   ├── music_tasks.py        # 音乐生成
│   ├── scheduler.py          # 每日 8 点调度器
│   ├── matrix_brainstorm.py   # 矩阵提示词生成器（头脑风暴）
│   └── pipeline.py           # 管线入口
├── backend/                  # FastAPI 后端（端口 8000）
│   ├── main.py               # 入口
│   ├── database.py           # MySQL 连接
│   ├── schemas.py             # Pydantic 模型
│   └── routers/               # API 路由
│       ├── assets.py
│       ├── runs.py
│       ├── quotas.py
│       ├── matrix.py          # 矩阵配置（支持 prompt_base）
│       └── ...
├── frontend/                  # React + Vite 前端（端口 5173）
│   └── src/pages/
│       ├── MatrixPage.tsx    # 6×6 矩阵生成界面
│       └── ...
├── works/
│   ├── video-daily.db        # SQLite（本地备用）
│   ├── uploads/              # 用户上传的参考图（i2i/i2v/fl2v/s2v 用）
│   └── YYYY-MM-DD/
│       ├── prompts/t2i/, i2i/, t2v/, i2v/, music/
│       └── assets/images/{t2i,i2i,refs}/, videos/{t2v,i2v,flf,s2v}/
├── ref/api/                   # MiniMax API 参考文档
├── scripts/legacy/            # 已废弃脚本
└── docs/                      # 项目文档
```

## 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 启动后端（端口 8000）
uvicorn backend.main:app --reload --port 8000

# 启动前端（端口 5173）
cd frontend && npm run dev

# 运行管线（生成内容）
python tools/pipeline.py

# 运行调度器
python tools/scheduler.py
```

## 重要修复记录

- **API 端口不匹配**：前端 API 客户端原指向 `8002`，改为 `8000`
- **数据库双写问题**：脚本默认写 SQLite，`use_mysql(True)` 后才写 MySQL；已统一为写 MySQL
- **Matrix 配置 prompt_base**：DB 新增 `prompt_base` 列，后端支持读写
- **ImageLightbox bug**：图片放大用 `100vw/100vh` 会变形，改为 `max-width/max-height`；添加 ESC 键关闭
- **目录整理 (2026-04-28)**：`src/` → `tools/`，删除过时脚本，统一文档路径引用
- **T2S 轮询超时修复**：`voices.py` / `audio.py` 轮询上限从 60 次提升到 180 次（5分钟 → 15分钟），解决部分音色 MiniMax 处理慢导致的 408 错误

## 已知限制

- API Key 从 `.env` 获取
- 视频下载 URL 有效期 1 小时（DB 记录原始 URL）
- MiniMax image-01 对复杂/简单场景渲染不稳定，部分 prompt 可能生成暗色/模糊图片
- 两个 Claude Code 窗口可能分别占用不同端口，统一使用 8000
- i2i / i2v 任务需要参考图，scheduler 中暂时跳过