# 目录结构

```
video-daily/
├── src/
│   ├── __init__.py
│   ├── config.py         # 配置管理
│   ├── minimax_client.py # MiniMax API 客户端
│   ├── video_tasks.py    # 视频生成任务
│   ├── image_tasks.py    # 图片生成任务
│   └── main.py           # 入口
├── works/
│   ├── photo/            # 图片输出
│   └── video/            # 视频输出
├── ref/                  # API 参考文档
├── docs/                 # 项目文档
├── .env                  # 环境配置（不提交）
├── .env.example          # 配置模板
└── README.md
```