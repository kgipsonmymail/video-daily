# 项目状态

## 技术栈

- Python 3.x
- MiniMax API (海螺视频/图片生成)

## 已实现模块

- `src/config.py` - 配置管理（API Key, 路径等）
- `src/minimax_client.py` - MiniMax API 客户端封装
- `src/video_tasks.py` - 视频生成任务管理
- `src/image_tasks.py` - 图片生成任务管理

## API 能力

### 视频生成

| 模型 | 分辨率 | 时长 | 额度/日 |
|------|--------|------|---------|
| Hailuo-2.3-Fast-768P | 768P | 6s | 2 |
| Hailuo-2.3-768P | 768P | 6s | 2 |

### 图片生成

| 模型 | 说明 |
|------|------|
| image-01 | 文生图/图生图 |

## 目录结构

```
video-daily/
├── src/              # 核心代码
├── works/
│   ├── photo/        # 生成的图片
│   └── video/       # 生成的视频
├── ref/              # API 参考文档
└── docs/             # 项目文档
```

## 已知限制

- API Key 需要从环境变量或 .env 文件获取
- 视频下载 URL 有效期 1 小时
- 需手动管理每日额度