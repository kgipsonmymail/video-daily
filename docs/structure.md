# 项目结构

## 整体架构

```
浏览器 (5173) ←→ React 前端 ←→ FastAPI 后端 (8000) ←→ MySQL (阿里云)
                          ↓
                   MiniMax API (生成内容)
                          ↓
                    文件写入 works/
```

## 目录结构

```
video-daily/
├── CLAUDE.md             # 项目概览（供 Claude Code 使用）
├── start.bat             # Windows 启动脚本
├── requirements.txt      # Python 依赖
├── .env                  # 环境变量（不提交）
├── .env.example          # 配置模板
├── backend/              # FastAPI 后端服务
│   ├── main.py           # 入口：CORS（5173/3000）+ 静态文件 /files/{path}
│   ├── config.py         # Pydantic Settings：API Key + MySQL 配置，@lru_cache 单例
│   ├── database.py       # MySQL engine (pool_pre_ping, pool_recycle=3600) + get_db 依赖注入
│   ├── models.py         # SQLAlchemy 2.0 ORM：8 张表（Run/Asset/Prompt/Quota/TaskQueue/PromptHistory/VoiceSample）
│   ├── schemas.py        # Pydantic 模型：对应 ORM 模型
│   ├── init_db.py        # 建库 + 建表脚本
│   └── routers/
│       ├── runs.py       # /api/runs — CRUD + 收藏切换（toggle_favorite）
│       ├── assets.py     # /api/assets — CRUD，复杂 JOIN 查询（assets+runs+prompts）
│       ├── prompts.py    # /api/prompts — 去重创建，获取 prompt 关联资产
│       ├── quotas.py     # /api/quotas — UPSERT，计算 remaining
│       ├── tasks.py      # /api/tasks — 队列 CRUD，POST /auto/generate 调用 LLM 生成
│       ├── generate.py   # /api/generate/image — 直接调用 MiniMax，下载保存到 works/
│       ├── matrix.py    # /api/matrix — matrix_configs CRUD，GET /configs/{id}/assets
│       ├── voices.py     # /api/voices — 音色样本，POST /preview 异步 T2S
│       └── audio.py      # /api/audio — 音频工坊，POST /generate 精细化 T2S
├── frontend/             # React + Vite 前端
│   ├── src/
│   │   ├── main.tsx      # React 入口
│   │   ├── App.tsx       # Router + QueryClientProvider
│   │   ├── types.ts      # TypeScript 接口
│   │   ├── api/          # Axios 客户端（client.ts + 8 个资源模块）
│   │   ├── components/   # Layout（导航）, RunCard, AssetCard（Lightbox）
│   │   └── pages/        # Tasks / Query / Daily / Queue / Matrix / Voice
│   └── package.json
├── tools/                # 独立工具模块（scheduler / pipeline 调用）
│   ├── config.py         # dotenv 加载，API_BASE_URL="https://api.minimaxi.com"
│   ├── client.py         # MiniMax HTTP 客户端（create/wait_for/query/download）
│   ├── db.py             # MySQL/SQLite 双模式 ORM（use_mysql() 切换）
│   ├── image_tasks.py    # run_t2i_task / run_i2i_task（use_mysql(True)）
│   ├── video_tasks.py    # run_t2v_task / run_i2v_task / run_fl2v_task / run_s2v_task
│   ├── music_tasks.py    # run_music_task（hex 音频保存）
│   ├── scheduler.py      # 每日 8 点调度器（Windows 任务计划程序触发）
│   ├── matrix_brainstorm.py  # MatrixBrainstormer + QualityAdjuster
│   └── pipeline.py       # 巨树世界管线入口（依次执行 6 种任务）
├── scripts/legacy/       # 已废弃脚本（batch_*/migrate_*/test_*.py）
├── ref/api/              # MiniMax API 本地参考文档
│   ├── image/            # 文生图、图生图
│   ├── video/            # 文生视频、图生视频、首尾帧、主体参考
│   ├── music/            # 音乐生成、歌词生成、翻唱前处理
│   ├── voice/            # 语音合成、音色设计/复刻
│   ├── file/             # 文件上传、下载、列出、删除
│   ├── text/             # AI SDK、文本对话
│   └── other/            # 主动缓存、接口概览、错误码
├── docs/                 # WCS 项目文档
│   ├── CLAUDE.md        # 项目概览
│   ├── structure.md      # 本文档
│   ├── features.md       # 能力清单（视频/图片/音乐/语音/矩阵/任务队列）
│   ├── project_status.md # 技术栈、已实现模块、每日额度、已知限制
│   ├── workflow.md       # 开发流程、API 文档规范、调度器配置、文件命名
│   ├── CODING_STANDARDS.md  # 代码规范
│   ├── error_book.md     # API 错误码手册
│   ├── dev_plan.md       # 开发计划
│   └── dev_log.md        # 开发日志
└── works/                # 生成产物存储
    ├── video-daily.db    # SQLite（本地备用）
    └── YYYY-MM-DD/       # 每日输出
        ├── prompts/      # t2i/i2i/t2v/i2v/music/*.txt
        └── assets/
            ├── images/  # t2i/ i2i/ refs/
            ├── videos/ # t2v/ i2v/ flf/ s2v/
            └── music/
```

## 模块关系

```
后端 API (backend/)
    ├── routers/generate.py — 调用 MiniMax API 生成内容，写入 MySQL
    └── routers/tasks.py    — 写入 task_queue，供 scheduler 读取

工具模块 (tools/)
    ├── scheduler.py — 读取 task_queue，执行任务，写入 MySQL runs/assets/quotas
    └── pipeline.py — 独立运行，直接写 MySQL

前端 (frontend/)
    ├── pages/MatrixPage.tsx — 调用 tools/matrix_brainstorm.py 生成矩阵
    └── api/generate.ts    — 批量提交到 /api/generate/image
```

## 关键配置文件

| 文件 | 用途 |
|------|------|
| `.env` | API Key + MySQL 连接参数（不提交 git） |
| `backend/config.py` | Pydantic Settings（backend 专用） |
| `tools/config.py` | dotenv 加载（tools 专用） |
| `start.bat` | 同时启动 backend (8000) + frontend (5173) |