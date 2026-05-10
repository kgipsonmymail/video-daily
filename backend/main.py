"""
FastAPI 后端入口 — Video Daily 资源管理系统
运行: uvicorn backend.main:app --reload --port 8000
"""

# ⚠️ 必须在所有其他 import 之前加载 .env
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.models import Base
from backend.database import engine
from backend.routers import runs, assets, prompts, quotas, tasks, generate, matrix, voices, audio, music, chat

# 项目根目录，用于静态文件访问
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# 启动时自动建表
Base.metadata.create_all(bind=engine)

# 确保 music_matrix_configs 表存在（无 ORM 模型，手动建表）
with engine.connect() as conn:
    from sqlalchemy import text
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS music_matrix_configs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            prompts_text TEXT NOT NULL,
            theme VARCHAR(64) DEFAULT 'game-bgm',
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.commit()

# 修复 music assets 路径：统一用正斜杠，有 works/ 则保留，无则加上
with engine.connect() as conn:
    conn.execute(text("""
        UPDATE assets
        SET file_path = CASE
            WHEN file_path LIKE 'works/%' THEN REPLACE(file_path, '\\\\', '/')
            ELSE CONCAT('works/', REPLACE(file_path, '\\\\', '/'))
        END
        WHERE modality = 'music' AND (file_path LIKE '%\\\\%' OR file_path NOT LIKE 'works/%')
    """))
    conn.commit()

app = FastAPI(title="Video Daily API", version="1.0.0")

# 允许 React 前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5175", "http://localhost:5176", "http://localhost:5174", "http://localhost:3000", "http://localhost:5177", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由模块
app.include_router(runs.router, prefix="/api/runs", tags=["运行任务"])
app.include_router(assets.router, prefix="/api/assets", tags=["资产文件"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["提示词库"])
app.include_router(quotas.router, prefix="/api/quotas", tags=["额度管理"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["任务队列"])
app.include_router(generate.router, prefix="/api/generate", tags=["内容生成"])
app.include_router(matrix.router, prefix="/api/matrix", tags=["矩阵配置"])
app.include_router(voices.router, prefix="/api/voices", tags=["音色管理"])
app.include_router(audio.router, prefix="/api/audio", tags=["音频工坊"])
app.include_router(music.router, prefix="/api/music", tags=["音乐生成"])
app.include_router(chat.router, prefix="/api/chat", tags=["文本对话"])


@app.get("/api/health")
def health_check():
    """健康检查接口"""
    return {"status": "ok", "message": "Video Daily API 运行正常"}


@app.get("/download/{file_path:path}")
def download_file(file_path: str):
    """
    提供文件下载服务，浏览器访问时弹出系统"另存为"对话框
    """
    import os, urllib.parse
    full_path = PROJECT_ROOT / file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    _, ext = os.path.splitext(file_path)
    media_type = {
        ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
        ".flac": "audio/flac", ".pcm": "audio/pcm",
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".mp4": "video/mp4", ".webm": "video/webm",
    }.get(ext.lower(), "application/octet-stream")
    filename = urllib.parse.quote(os.path.basename(file_path))
    contents = full_path.read_bytes()
    return Response(
        content=contents,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Content-Length": str(len(contents)),
        },
    )


@app.get("/files/{file_path:path}")
def serve_file(file_path: str):
    """
    提供本地文件访问服务（浏览器直接播放/预览）
    """
    import os
    full_path = PROJECT_ROOT / file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    media_types = {
        ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
        ".flac": "audio/flac", ".pcm": "audio/pcm",
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".mp4": "video/mp4", ".webm": "video/webm",
    }
    _, ext = os.path.splitext(file_path)
    media_type = media_types.get(ext.lower(), "application/octet-stream")
    contents = full_path.read_bytes()
    return Response(
        content=contents,
        media_type=media_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Content-Length": str(len(contents)),
        },
    )
