# 项目审计报告

审计日期：2026-08-07
审计提交：`dcbb75a` (`main`, 已与 `origin/main` 快进同步)
审计方式：按 WCS `references/audit_checklists.md` 执行，只读检查；未修改业务代码。

## 四维审计框架

| 维度 | 回答的问题 | 本次覆盖结论 |
|---|---|---|
| 功能与业务完成度 | 用户能否完成核心任务，失败时是否有可理解的结果？ | 已根据功能清单、路由和实现做静态对照；真实 MiniMax、MySQL 和浏览器端到端流程尚未验证。 |
| 效率与鲁棒性 | 高负载、失败、重试、重启时能否稳定工作？ | 已发现文件 Range 读取的内存放大风险；并发、队列和外部 API 的真实压力尚未验证。 |
| 文档完整度与有效性 | 新维护者能否根据文档正确运行、定位和修改项目？ | 多份文档存在乱码和版本漂移；已新增 `project_index.yaml` 作为 WCS 入口索引。 |
| 安全、数据与交付运维 | 是否有访问边界、数据保护、可观测性和可复现交付？ | 发现文件读取、上传与 API 授权的高优先级缺口；构建/lint 目前不可复现。 |

## 范围与证据

- 后端 FastAPI 入口、文件服务、上传和路由。
- Python 工具、依赖配置、数据库初始化。
- React/Vite 前端构建配置。
- WCS 基线文档及项目文档一致性。
- 命令证据：`git status --short --branch`、`git log -1`、`python -m compileall -q backend tools src`、`npm run build`、`npm run lint`、`rg` 安全扫描。

## Findings

### AUD-001 — P1 / 高置信度：文件服务存在路径穿越与任意文件读取

- 位置：`backend/main.py:70-155` 的 `/download/{file_path:path}` 与 `/files/{file_path:path}`。
- 证据：直接使用 `PROJECT_ROOT / file_path`，未 `resolve()` 后检查路径是否仍位于项目目录；也未限制可访问子目录或扩展名。
- 影响：未授权请求可能读取项目外文件或 `.env` 等敏感文件；服务文档还建议绑定 `0.0.0.0`。
- 建议：统一使用解析后的安全路径函数，执行 `relative_to(PROJECT_ROOT)` containment 校验；仅开放 `works/` 等允许目录，并补充鉴权/部署边界测试。
- 验证：增加 `..`、绝对路径、`.env` 和符号链接测试。

### AUD-002 — P1 / 高置信度：上传接口无认证、大小和类型限制

- 位置：`backend/routers/generate.py:264-286` 的 `POST /api/generate/upload`。
- 证据：直接 `await file.read()` 后写入 `works/uploads/`；未校验 Content-Type、扩展名、文件大小、图片内容或配额。
- 影响：可被任意调用者耗尽磁盘/内存，上传非图片文件并通过文件服务暴露；在非本机部署时风险更高。
- 建议：增加认证、请求体大小上限、允许 MIME/扩展名白名单、内容签名检查、配额和失败清理。
- 验证：超大文件、伪造 MIME、非图片和并发上传测试。

### AUD-003 — P2 / 高置信度：Range 文件读取存在内存放大与边界校验缺陷

- 位置：`backend/main.py:118-155`。
- 证据：每次 Range 请求先调用 `full_path.read_bytes()` 读取整个文件；`range_end` 未限制到 `file_size - 1`，负值和反向范围也未拒绝。
- 影响：大视频并发拖拽会造成高内存占用；异常 Range 可能返回不符合协议的响应。
- 建议：使用文件句柄分段读取，严格校验 `0 <= start <= end < size`，限制单次范围并返回规范 `416`。

### AUD-004 — P1 / 中高置信度：生成与资产 API 没有认证/授权边界

- 位置：`backend/main.py:40-60` 路由注册及各 `backend/routers/*.py`。
- 证据：未发现认证依赖；CORS 仅限制来源但不提供身份校验，生成、配额和资产操作均可直接调用。
- 影响：同网段或暴露端口的调用者可消耗 MiniMax 配额、读取/删除资产或修改任务。
- 建议：在反向代理或应用层增加认证与权限模型；将 CORS、监听地址和生产配置外置，并补充未授权请求测试。

### AUD-005 — P2 / 高置信度：项目文档编码损坏且版本信息不一致

- 位置：`docs/CODING_STANDARDS.md`、`docs/workflow.md`、`docs/project_status.md` 等。
- 证据：文件中可见 `浠ｇ爜瑙勮寖` 等乱码；文档描述 React 18，而 `frontend/package.json` 使用 React 19、Vite 8、TypeScript 6。
- 影响：维护者无法可靠阅读规范；按文档操作可能得到错误的运行时与依赖预期。
- 建议：统一保存为 UTF-8，修复乱码；从 `package.json`/锁文件生成版本事实源并更新文档。

### AUD-006 — P2 / 高置信度：前端自动化验证不可复现

- 位置：`frontend/package.json` 与工作区依赖状态。
- 证据：`npm run build` 失败（`tsc` not recognized），`npm run lint` 失败（`eslint` not recognized）；当前工作区没有安装 `frontend/node_modules`。
- 影响：无法确认 TypeScript、Vite 和 ESLint 结果，发布前质量门禁缺失。
- 建议：执行 `npm ci` 后运行 build/lint；在 CI 固定 Node 版本并将结果记录到文档。

### AUD-007 — P2 / 高置信度：缺少 WCS 项目中枢索引，审计与维护入口不统一

- 位置：审计开始时 `docs/project_index.yaml` 不存在。
- 证据：WCS 最新版要求其作为每个任务的开场入口；项目文档分散在 README 与 `docs/` 中，缺少机器可读的加载指引。
- 影响：AI/维护者容易一次性加载过多或遗漏关键文档，无法稳定复现审计与维护流程。
- 处理：本次已新增 `docs/project_index.yaml`，列出项目入口、文档用途、维护焦点和审计任务上下文。

## 覆盖与未知项

- Python 静态编译：通过（`compileall`）。
- 前端构建/lint：未完成，原因是依赖未安装。
- 未执行真实 MySQL、MiniMax API、浏览器端到端和 Windows 任务计划测试；这些需要外部服务或运行环境。
- 未发现已跟踪的 `.env` 文件；仍需在部署环境核查密钥与网络暴露。

## 优先后续动作

1. 修复 AUD-001/AUD-002/AUD-004 的访问控制与文件边界。
2. 修复 Range 读取并补充安全回归测试（AUD-003）。
3. 统一文档编码与版本事实源（AUD-005）。
4. 安装锁定依赖并接入 CI build/lint（AUD-006）。
