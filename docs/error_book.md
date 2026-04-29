# 错误手册

## 常见错误

### API 错误码

| status_code | 说明 | 处理 |
|-------------|------|------|
| 0 | 成功 | - |
| 1002 | 触发限流 | 稍后重试 |
| 1004 | 鉴权失败 | 检查 API Key |
| 1008 | 余额不足 | 检查账户 |
| 1026 | 内容涉及敏感 | 调整描述 |
| 1027 | 生成内容敏感 | 调整描述 |
| 2013 | 参数异常 | 检查入参 |

### T2S 任务超时（408）

- **现象**：`POST /api/voices/preview` 返回 408 Request Timeout
- **原因**：MiniMax 对部分音色（如"搞笑大爷"）处理较慢，后端轮询 60×5s=5分钟即超时
- **解决**：将 `backend/routers/voices.py` 和 `audio.py` 轮询上限从 60 提升到 180（15分钟）
- **影响**：长文本或慢音色生成现在最多等待 15 分钟

### 前端音频播放无声音

- 检查 `Audio` 对象 `onloadedmetadata` 是否正确调用 `play()`
- `play()` 可能因浏览器策略失败（需用户交互触发），添加 `.catch()` 吞掉异常
- 确认 `audioRef.current?.pause()` 在播放新音频前调用，避免多个音频重叠

---

## Bug 修复记录

### `quota_usage_log` 表重复定义导致后端启动失败

- **现象**：`uvicorn backend.main:app` 启动报错 `sqlalchemy.exc.InvalidRequestError: Table 'quota_usage_log' is already defined for this MetaData instance`
- **根因**：`backend/quota_logger.py` 定义了 `class QuotaUsageLog(Base)`，但 `backend/models.py` 也定义了同名 class。`Base.metadata.create_all()` 在 `main.py` 导入时被调用两次，导致冲突
- **修复**：`quota_logger.py` 移除 `QuotaUsageLog` class 定义，直接从 `backend.models` 导入。模型只在一处定义
- **影响文件**：`backend/quota_logger.py`

### 歌词生成额度未累加（首次创建时 SET used = 1 而非 used + 1）

- **现象**：歌词生成成功，但每日额度始终显示 `0/N`
- **根因**：`backend/routers/music.py` 中 lyrics 路由的额度更新逻辑是：
  ```python
  if row:
      db.execute(text("UPDATE quotas SET used = 1 WHERE id = :id"), {"id": row[0]})  # 错误：只设成1
  else:
      q = Quota(..., used=1)  # 首次创建也是1
  ```
  每次调用都设成 1，而不是累加 `used + 1`
- **修复**：改为 `UPDATE quotas SET used = used + 1`，首次创建时 `used=1`（正确）
- **影响文件**：`backend/routers/music.py`

### 歌词生成前端直调 MiniMax API 报 401

- **现象**：歌词生成 Tab 点"生成歌词"后 `net::ERR_CONNECTION_REFUSED`（后端未启动）→ 后端启动后报 `⚠️ login fail: Please carry the API secret key in the 'Authorization' field`
- **根因**：LyricsTab 直接用前端 `fetch('https://api.minimaxi.com/v1/lyrics_generation', ...)` 调用 MiniMax，绕过后端。浏览器端没有后端的 `.env` API Key，所以 401
- **修复**：新增 `POST /api/music/lyrics` 后端路由，所有 MiniMax 调用经过后端。LyricsTab 改为调用 `musicApi.generateLyrics()`（走后端）
- **影响文件**：`backend/routers/music.py`（新增路由）、`frontend/src/api/music.ts`（新增方法）、`frontend/src/pages/MusicPage.tsx`（LyricsTab 改用后端 API）

### 歌词生成缺少记录（Run / Asset / txt 文件）

- **现象**：歌词生成成功，但历史里查不到，Daily 页面也没记录
- **根因**：`/api/music/lyrics` 只返回歌词文本，没有写入 `runs` 表、`assets` 表、`works/.../prompts/lyrics/` txt 文件
- **修复**：完整实现"生成 → 创建 Run 记录 → 保存 txt → 创建 Asset 记录 → 扣减额度"流程。txt 命名 `<run_id>.txt`，内容含 Title/Style/Mode 和完整歌词
- **影响文件**：`backend/routers/music.py`

### SQLAlchemy 编辑被截断导致 music.py 损坏

- **现象**：`backend/routers/music.py` 第 243 行变成 `db.commit()\n        raise HTTPException`（缩进丢失、代码断裂）
- **根因**：用 `Edit` 工具修改时 old_string 在文件中只存在一次但匹配位置不对，导致替换后文件损坏
- **修复**：用 `Write` 工具重写整个文件，确保完整性和正确缩进。以后避免对已损坏文件做增量 Edit，改用 Write 重写
- **影响文件**：`backend/routers/music.py`

---

## Bug 修复记录

### 音乐矩阵 file_path 路径错误（播放 404）

- **现象**：`NotSupportedError: Failed to load because no supported source was found`；日志显示 404 on `/files/2026-04-29/assets/music/...`
- **根因**：
  1. `task_runner.py` 中 `out_path.relative_to(proj_root)` 在 Windows 上生成反斜杠路径 `2026-04-29\assets\music\...`，存入 DB 后前端的 `/files/` URL 无法解析（URL 不认识反斜杠）
  2. 实际文件在 `works/2026-04-29/assets/music/`，但 DB 里存的路径缺少 `works/` 前缀，导致静态文件服务 404
  3. 前端 `MusicGridPreview` 组件里硬编码 `FILE_BASE = "localhost:8000/files"` 缺少 `http://`
- **修复**：
  - `task_runner.py`：路径拼接改为 `str(out_path.relative_to(proj_root)).replace("\\", "/")`，确保正斜杠
  - `main.py` 启动时执行 SQL 修复：给 music assets 补上 `works/` 前缀，并统一反斜杠
    ```sql
    UPDATE assets SET file_path = CASE
        WHEN file_path LIKE 'works/%' THEN REPLACE(file_path, '\\', '/')
        ELSE CONCAT('works/', REPLACE(file_path, '\\', '/'))
    END
    WHERE modality = 'music' AND (file_path LIKE '%\%' OR file_path NOT LIKE 'works/%')
    ```
  - 前端 `MusicGridPreview`：`FILE_BASE` 改为 `"http://localhost:8000/files"`

### React key 重复导致控制台警告（`instrument` duplicate key）

- **现象**：`Encountered two children with the same key, instrument`；MatrixPage 两个 grid 的表头 `<th key={s.abbr}>` 中 `s.abbr` 可能重复（如 "instrument"）
- **根因**：`colStyleLabels`（音乐列）和 `styles`（图片列）都用 `s.abbr` 作为 React key，但abbr可能重复（多个列同名）
- **修复**：所有 `key={s.abbr}` 改为 `key={`${prefix}-${index}`}` 形式，用数组索引保证唯一
  - 图片矩阵：`key={`img-col-${ci}`}`
  - 音乐矩阵：`key={`col-${ci}`}`

### music_matrix_configs 表不存在（启动报错 1146）

- **现象**：`pymysql.err.ProgrammingError: (1146, "Table 'minimax-take.music_matrix_configs' doesn't exist")`
- **根因**：该表使用原始 SQL 管理，不在 SQLAlchemy ORM `Base` 模型中，所以 `Base.metadata.create_all()` 不会创建它
- **修复**：`main.py` 启动时手动执行 `CREATE TABLE IF NOT EXISTS music_matrix_configs (...)`

### MiniMax 音乐 API 2151 错误（服务端临时故障）

- **现象**：`API error: {'base_resp': {'status_code': 2151, 'status_msg': '音乐生成准备失败，请稍后重试'}}`
- **根因**：MiniMax 服务端临时过载或队列满，非 prompt 内容问题
- **修复**：`task_runner.py` 的 `_run_single_music_track` 增加重试逻辑：检测到 `bc == 2151` 或 `status == 1` 时等待 5 秒重试，最多 3 次

### task_runner.py 闭包变量 bug（config_id 永远是 0）

- **现象**：所有 music track 的 `matrix_name` 都是 `music-matrix-0`
- **根因**：`_run_single_music_track` 闭包内引用外层 `config_id`，但 `_run()` 里对 `_config_id` 的赋值在闭包创建之后，导致所有线程都用最后一次的 `config_id` 值
- **修复**：`submit_music_matrix_async` 中用 `_config_id = config_id` 在 `_run` 定义前捕获，再传给 tasks tuple

### 前端轮询 tracks 时 tracks 为空导致 cells 重置

- **现象**：点击"继续生成"后跳转历史页，cells 被重置为空状态（pending格子消失）
- **根因**：`tracks` query 有 `refetchInterval: 5000`，但初始加载时 `activeMusicConfigId` 刚设置、tracks 数据还未返回，`useEffect` 用空的 `tracks` 覆盖了 `initCells`
- **修复**：`useEffect` 开头加 `if (!tracks.length) return;` 保护，初始化由 `handleGenerate` 里的 `initCells` 单独负责