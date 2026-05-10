# Netlify 部署说明

## 问题原因
Netlify 只能托管静态文件（HTML/CSS/JS），无法运行 Python 后端服务。你需要分别部署前端和后端。

## 解决方案

### 方案1：部署后端到云服务（推荐）

1. **部署后端到 Railway/Render/Heroku**
   - 注册账号：https://railway.app 或 https://render.com
   - 连接 GitHub 仓库
   - 选择 `backend` 目录部署
   - 获取后端 URL（例如：https://your-app.railway.app）

2. **更新前端配置**
   - 编辑 `t2s-chat/config.js`
   - 修改 `API_BASE` 为后端 URL：
     ```javascript
     API_BASE: "https://your-app.railway.app/api"
     ```

3. **重新部署到 Netlify**
   - 提交更改到 GitHub
   - Netlify 会自动重新部署

### 方案2：仅展示UI（Demo模式）

如果只想展示界面效果，不需要实际功能：

1. 编辑 `t2s-chat/config.js`：
   ```javascript
   DEMO_MODE: true
   ```

2. 重新部署到 Netlify

## Netlify 部署步骤

1. 将 `t2s-chat` 目录推送到 GitHub
2. 在 Netlify 中连接仓库
3. 设置构建配置：
   - Base directory: `t2s-chat`
   - Publish directory: `.`（当前目录）
4. 点击 Deploy

## 当前状态

- ✅ 前端代码已配置为可部署
- ⚠️ 需要部署后端服务才能正常使用
- 📝 配置文件：`t2s-chat/config.js`
