# Video Daily

基于 MiniMax API 的 AI 内容生成管理系统，支持视频（T2V/I2V/FL2V/S2V）、图片（T2I/I2I）、音乐生成，并提供 React 前端 + FastAPI 后端的完整资产管理平台。

## 技术栈

- **后端**: FastAPI (端口 8000) + SQLAlchemy + MySQL
- **前端**: React 18 + Vite + React Router + React Query + Axios (端口 5173)
- **工具模块**: Python 独立脚本 (tools/) — scheduler、pipeline、矩阵生成
- **数据库**: MySQL (主) + SQLite (本地备用)
- **调度**: Windows 任务计划程序 → 每日 8 点触发 scheduler

## 项目结构

```
video-daily/
├── backend/              # FastAPI 后端服务
│   ├── main.py           # 入口，注册 8 个路由模块
│   ├── config.py         # Pydantic Settings (.env)
│   ├── database.py       # MySQL 连接 (pool_pre_ping=True)
│   ├── models.py         # SQLAlchemy ORM (8 张表)
│   ├── schemas.py        # Pydantic 请求/响应模型
│   ├── init_db.py        # 建库+建表脚本
│   └── routers/          # API 路由
│       ├── runs.py       # /api/runs — Run CRUD + 收藏切换
│       ├── assets.py     # /api/assets — Asset CRUD
│       ├── prompts.py    # /api/prompts — Prompt 去重
│       ├── quotas.py     # /api/quotas — 额度 UPSERT
│       ├── tasks.py      # /api/tasks — 任务队列 + Auto 生成
│       ├── generate.py   # /api/generate — 直接调用 MiniMax API
│       ├── matrix.py     # /api/matrix — 矩阵配置
│       └── voices.py     # /api/voices — 音色样本管理
├── frontend/             # React 前端 (端口 5173)
│   └── src/
│       ├── api/          # Axios API 客户端 (8 个)
│       ├── components/   # Layout, RunCard, AssetCard
│       └── pages/        # Tasks/Query/Daily/Queue/Matrix/Voice
├── tools/                # 独立工具模块 (非 API 服务)
│   ├── config.py         # 路径/API 配置 (dotenv)
│   ├── client.py         # MiniMax HTTP 客户端
│   ├── db.py             # MySQL/SQLite 双模式 ORM
│   ├── image_tasks.py    # T2I / I2I 任务 (写 MySQL)
│   ├── video_tasks.py    # T2V / I2V / FL2V / S2V 任务
│   ├── music_tasks.py    # 音乐生成任务
│   ├── scheduler.py      # 每日 8 点调度器
│   ├── matrix_brainstorm.py  # 矩阵提示词生成器
│   └── pipeline.py       # 巨树世界管线入口
├── works/                # 生成产物存储
│   ├── video-daily.db    # SQLite (本地备用)
│   └── YYYY-MM-DD/       # 每日输出
│       ├── prompts/     # t2i/i2i/t2v/i2v/music/
│       └── assets/
│           ├── images/  # t2i/i2i/refs/
│           ├── videos/ # t2v/i2v/flf/s2v/
│           └── music/
├── ref/api/              # MiniMax API 参考文档 (本地)
│   ├── image/
│   ├── video/
│   ├── music/
│   ├── voice/
│   └── text/
├── scripts/legacy/      # 已废弃脚本
├── docs/                 # WCS 项目文档
└── start.bat             # Windows 启动脚本
```

## 数据库表结构

| 表 | 主键 | 用途 |
|----|------|------|
| `runs` | id (String) | 每次生成会话，含 theme/category/model/variant/status/notes/is_favorite |
| `assets` | id (Int) | 产物文件，含 file_path/external_url/modality/sub_type |
| `prompts` | id (Int) | 提示词去重 (text UNIQUE)，含 lang/theme |
| `quotas` | id (Int) | 每日额度追踪 (quota_date+model UNIQUE) |
| `task_queue` | id (Int) | 任务调度队列，含 task_type( user/auto)/category/model/priority/status |
| `prompt_history` | id (Int) | Auto 任务 prompt 去重 (text UNIQUE)，含 direction/theme |
| `matrix_configs` | id (Int) | 矩阵配置，含 subjects_text/styles_text/prompt_base |
| `voice_samples` | id (Int) | 音色样本，含 voice_id/voice_name/lang/file_path |

## 关键规则

### 启动方式

```bash
# 方式1: start.bat (Windows 双窗口)
start.bat

# 方式2: 手动启动
uvicorn backend.main:app --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

### 调度器配置 (Windows 任务计划程序)

```
操作: 启动程序
程序: python
参数: {项目路径}\tools\scheduler.py
起始位置: {项目路径}
触发器: 每天 08:00
```

### API 调用规则

> **所有 MiniMax API 调用必须先查阅本地 `ref/api/` 目录文档，严禁直接查阅网络文档。**

### 文件命名规范

```
{ts}__{theme}__{category}__{variant}__v{nnn}.{ext}
例: 20260424_015015__giant-tree__t2i__farmer-panorama__v001.png
```

### 额度限制

| 模型 | 每日限额 |
|------|---------|
| Hailuo-2.3-Fast-768P 6s | 2 |
| Hailuo-2.3-768P 6s | 2 |
| image-01 | 120 |
| music-2.5 | 4 |
| music-2.6 | 100 |
| music-cover | 100 |
| lyrics_generation | 100 |

### 数据库写入规则

- **backend API** (`routers/generate.py`): 直接写 MySQL
- **tools pipeline** (`image_tasks.py` 等): `use_mysql(True)` 后写 MySQL，`use_mysql(False)` 写 SQLite
- **默认**: tools 模块已设置 `use_mysql(True)`，与后端保持一致

## 矩阵生成器使用

```python
from tools.matrix_brainstorm import MatrixBrainstormer

bm = MatrixBrainstormer()
result = bm.brainstorm(
    theme="房车生活",
    requirements="放松、冒险、温馨、神秘",
    n_subjects=6,
    n_styles=6,
    quality_preset="rich",
    emotion_weights={"relaxed": 2, "tense": 1, "fun": 1, "mysterious": 1},
)
result.save_to_files("works/matrix_output")
```

质量预设: minimal (60ch) / standard (120ch) / rich (200ch) / ultra (350ch)

## 前端页面

- `/tasks` — Run 记录列表，支持 modality/date/favorites 过滤
- `/query` — 高级资产查询，支持多条件 + 全文搜索
- `/daily` — 每日总览，含今日额度和生成结果
- `/queue` — 任务队列管理，提交 user/auto 任务
- `/matrix` — 矩阵生成界面（T2I 图片矩阵 + I2I 批量图生图）
- `/voices` — 音色样本管理，预览 T2S 效果

## 环境变量 (.env)

```bash
MINIMAX_API_KEY=         # MiniMax API 密钥
DB_HOST=                 # MySQL 主机
DB_PORT=3306
DB_NAME=                 # 数据库名
DB_USER=
DB_PASSWORD=
```

## 注意事项

1. **视频下载 URL 有效期 1 小时**，DB 记录原始 URL，超时需重新生成
2. **tools 模块与 backend 使用不同的 db.py**，各自独立管理数据库连接
3. **i2i/i2v 任务需要参考图**，scheduler 中暂时跳过
4. **两个 Claude Code 窗口可能分别占用不同端口**，统一使用 8000