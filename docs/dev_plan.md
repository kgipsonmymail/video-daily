# 开发计划

## 已完成

- [x] 核心视频生成管线搭建（代码框架）
- [x] 4 种视频生成任务（代码实现，额度待验证）
- [x] 文生图 / 图生图（已真实调用 API 验证）
- [x] 数据库元数据持久化（runs / prompts / assets / quotas）
- [x] 本地资产浏览器 UI（Streamlit，已被前端替代）
- [x] FastAPI 后端（端口 8000）
- [x] React 前端（端口 5173）
- [x] 矩阵提示词生成器（tools/matrix_brainstorm.py）
- [x] 前端 6×6 矩阵生成界面
- [x] 任务队列 + 每日 8 点调度器
- [x] 数据库层 + 本地查看 UI（SQLite + Streamlit）
- [x] 音色样本管理 + T2S 预览

## 进行中

- [ ] 真实视频生成任务端到端验证（额度）

## 待办

- [ ] 文生视频任务 (T2V) — `MiniMax-Hailuo-2.3` 真实调用
- [ ] 图生视频任务 (I2V) — `MiniMax-Hailuo-2.3-Fast` 真实调用
- [ ] 首尾帧视频任务 (FL2V) — `MiniMax-Hailuo-02` 真实调用
- [ ] 主体参考视频任务 (S2V) — `S2V-01` 真实调用（额度待确认）
- [ ] 音乐生成 API — `music-2.6` / `music-cover` / `lyrics_generation`
- [x] 语音合成 — Text to Speech HD（`TTS HD`）— ✅ 已实现（音频工坊 + 音色预览）
- [ ] 音色设计 API
- [ ] 音色复刻 API
- [ ] 视频下载 URL 过期处理（当前仅记录原始 URL，有效期 1 小时）

## 测试主题

巨树世界场景：
- 巨树上的人类聚落
- 树叶上的农田与建筑
- 正常大小植物与巨树的对比

## 里程碑

1. ✅ 跑通图片生成 API（T2I + I2I，已真实验证）
2. ✅ 数据库持久化层（SQLite，已落地）
3. ✅ 本地资产查看 UI（Streamlit，已被前端替代）
4. ✅ FastAPI 后端 + React 前端
5. ✅ 矩阵提示词生成器 + 前端界面
6. ⬜ 跑通 4 种视频生成 API（额度待验证）
7. ⬜ 音乐生成支持
8. ⬜ 语音合成支持

## 每日额度速查

| 模型 | 每日限额 | 备注 |
|------|---------|------|
| Hailuo-2.3-768P 6s (T2V) | 2 | 文生视频标准画质 |
| Hailuo-2.3-Fast-768P 6s (I2V) | 2 | 图生视频快速 |
| Hailuo-02-768P 6s (FL2V) | 2 | 首尾帧视频 |
| S2V-01 6s | 2 | 主体参考视频 |
| image-01 | 120 | 文/图生图 |
| music-2.5 | 4 | 音乐生成（已下线） |
| music-2.6 | 100 | 音乐生成 |
| music-cover | 100 | 翻唱 |
| lyrics_generation | 100 | 歌词生成 |
| Text to Speech HD | 11000 | 语音合成 |