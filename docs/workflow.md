# 工作流

## 开发流程

1. 接收任务 → 确认需求与约束
2. 编码前门禁 → 阅读规范文档，制定实现计划
3. 实现 → 紧扣范围，避免无关重构
4. 验证 → 测试通过后再提交
5. 文档同步 → 更新相关文档
6. 学习复盘 → 沉淀可复用经验

## 质量门禁

- lint/type 检查通过
- 核心 API 流程验证
- 文档已同步更新

## API 文档规范

> **所有 MiniMax API 调用必须先查阅本地 `ref/api/` 目录文档，严禁直接查阅网络文档。**

本地 MiniMax API 规范位于 `ref/api/` 目录，按模块分组：

```
ref/api/
├── image/        # 文生图、图生图
├── video/        # 文生视频、图生视频、首尾帧视频、主体参考视频
├── music/        # 音乐生成、歌词生成、翻唱前处理
├── voice/        # 语音合成、音色设计、音色复刻
├── file/         # 文件上传下载
└── text/         # 文本对话
```

## 内容生成管线

### 启动服务

```bash
# 方式1: start.bat（Windows 双窗口）
start.bat

# 方式2: 手动启动
uvicorn backend.main:app --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

服务地址：
- 后端: http://localhost:8000
- 前端: http://localhost:5173
- API 文档: http://localhost:8000/docs

### 独立工具运行

```bash
# 运行管线（生成内容 + 写入数据库）
python tools/pipeline.py

# 运行调度器（每日 8 点由 Windows 任务计划程序触发）
python tools/scheduler.py
```

### 视频任务执行流程

1. 创建任务 → 获取 task_id
2. 轮询状态 → `query_video_task`
3. 成功后下载 → `get_file_download_url`
4. 保存到 `works/{date}/assets/videos/{category}/`
5. 自动写入 MySQL（runs + assets + quotas 表）

### 图片任务执行流程

1. 调用 `image_generation` API
2. 下载返回的图片 URL
3. 保存到 `works/{date}/assets/images/{category}/`
4. 自动写入数据库

## 数据库结构

| 表 | 用途 |
|----|------|
| `runs` | 每次生成会话（run_id, category, model, status…） |
| `prompts` | 提示词去重（text UNIQUE） |
| `assets` | 产物文件（本地路径、原始 URL、sub_type…） |
| `quotas` | 每日额度追踪（quota_date + model → 已用/限额） |
| `task_queue` | 用户/Auto 任务队列（pending/running/done/failed） |
| `prompt_history` | Prompt 历史记录（用于 Auto 任务去重） |
| `matrix_configs` | 矩阵配置（主体×风格，支持 prompt_base） |
| `voice_samples` | 音色样本管理 |

## 额度管理

- 每次创建 run 时自动检查对应模型的当日剩余额度
- 额度耗尽时报错，不继续消耗
- 已用数量实时写入 `quotas` 表

## 每日 8 点调度器

每天 8 点由 Windows 任务计划程序启动 `tools/scheduler.py`：

1. 读取 `task_queue` 中当日所有 `pending` 任务
2. 优先执行 `user` 任务（priority=1），再执行 `auto` 任务（priority=10）
3. 每执行前检查剩余额度，额度耗尽则跳过该任务
4. 执行完成后更新 `task_queue.status` 和 `run_id`
5. 所有用过的 prompt 写入 `prompt_history`（去重）

Windows 任务计划程序配置：
```
操作：启动程序
程序：python
参数：{项目路径}\tools\scheduler.py
起始位置：{项目路径}
触发器：每天 08:00
```

## 文件命名规范

```
{ts}__{theme}__{category}__{variant}__v{nnn}.{ext}
```

例：
```
20260424_015015__giant-tree__t2i__farmer-panorama__v001.png
20260424_015015__giant-tree__i2i__farmer-market__v001.png
20260424_100012__giant-tree__t2v__leaf-town__v001.mp4
```

## 开发规范

### Python 代码规范

1. 使用 type hints
2. 类名大驼峰，函数/变量小写下划线
3. docstring 使用三引号简洁描述
4. 相对导入，tools/ 内模块互相引用

### 配置规范

- API Key 不硬编码，使用环境变量或 .env
- 路径使用 Path 对象
- 敏感配置与代码分离

### 命名规则

| 类型 | 规则 | 示例 |
|------|------|------|
| 类 | 大驼峰 | `MiniMaxClient` |
| 函数/变量 | 小写下划线 | `create_video_task` |
| 常量 | 全大写下划线 | `API_BASE_URL` |
| 配置文件 | 小写下划线 | `config.py` |