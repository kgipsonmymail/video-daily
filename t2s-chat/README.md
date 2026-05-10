# T2S-Chat 对话页面 · 部署说明

## 目录结构

```
t2s-chat/
├── index.html      # 主页面
├── .env           # 后端API地址配置（可选）
├── portrait.png   # 角色立绘（放在index.html同级）
└── user-avatar.png # 用户头像（可选）
```

## 部署方式

### 方式1：前后端同机部署（推荐）

后端 FastAPI 运行在同一台服务器上时，不需要修改任何配置。

```bash
# 后端运行在 8000 端口
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Nginx 代理（或直接访问）
# 确保 /api 请求转发到 8000
```

### 方式2：后端与前端分离

编辑 `.env` 文件，填写后端地址：

```
T2S_API_BASE=https://你的后端域名或IP
```

### 方式3：前后端都用 Nginx 托管

在云服务器上，用 Nginx 把前端和后端（8000端口）统一代理到同一域名/端口：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/t2s-chat;
    index index.html;

    # 前端文件
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理到后端
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
```

然后 `index.html` 中的 `API_BASE` 会自动使用当前域名，不需要修改任何配置。

## 立绘设置

把角色立绘图片命名为 `portrait.png` 放到同目录即可。默认是占位图。

## 注意事项

- 后端 CORS 必须允许前端域名，修改 `backend/main.py` 中的 `allow_origins`
- 视频/音频下载 URL 有效期 1 小时
- 额度使用 `speech-2.8-hd` 模型，按句子数计费