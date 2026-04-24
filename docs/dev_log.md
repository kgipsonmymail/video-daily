# 开发日志

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

- 抓取 MiniMax API 文档（text/voice/video/image/music/file 子目录）
- 音乐生成 API 支持