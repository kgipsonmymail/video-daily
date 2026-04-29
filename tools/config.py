"""配置管理"""

import os
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# API 配置
API_KEY = os.getenv("MINIMAX_API_KEY", "")
API_BASE_URL = "https://api.minimaxi.com"

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent
WORKS_DIR = PROJECT_ROOT / "works"
PHOTO_DIR = WORKS_DIR / "photo"
VIDEO_DIR = WORKS_DIR / "video"

# SQLite（仅用于本地 pipeline，线上使用 MySQL）
DB_PATH = WORKS_DIR / "video-daily.db"

# MySQL 数据库（pipeline 写入目标）
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "minimax-take")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


def get_mysql_url() -> str:
    return (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )


def today_str() -> str:
    return date.today().isoformat()


def date_dir(d: str | None = None) -> Path:
    tag = d or today_str()
    return WORKS_DIR / tag


def prompts_dir(d: str | None = None) -> Path:
    return date_dir(d) / "prompts"


def assets_dir(d: str | None = None) -> Path:
    return date_dir(d) / "assets"


def ensure_dirs() -> None:
    """确保必要的目录存在"""
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    # 新结构
    for subdir in ["t2i", "i2i", "refs"]:
        (assets_dir() / "images" / subdir).mkdir(parents=True, exist_ok=True)
    for subdir in ["t2v", "i2v", "flf", "s2v"]:
        (assets_dir() / "videos" / subdir).mkdir(parents=True, exist_ok=True)
    for subdir in ["t2i", "i2i", "t2v", "i2v", "music"]:
        (prompts_dir() / subdir).mkdir(parents=True, exist_ok=True)


def get_api_key() -> str:
    """获取 API Key"""
    if not API_KEY:
        raise ValueError("MINIMAX_API_KEY not set. Copy .env.example to .env and fill in your API key.")
    return API_KEY


# ── Quota buckets ──────────────────────────────────────────────────────────────
# Centralized quota config shared by all tools modules.
# model key → (bucket_name, daily_limit)

QUOTA_BUCKETS: dict[str, tuple[str, int]] = {
    # Image
    "image-01": ("image-01", 120),
    # Video (Hailuo-02 and S2V-01 have 0 quota — excluded)
    "MiniMax-Hailuo-2.3": ("Hailuo-2.3-768P 6s", 2),
    "MiniMax-Hailuo-2.3-Fast": ("Hailuo-2.3-Fast-768P 6s", 2),
    # Speech / TTS
    "speech-2.8-hd": ("Text to Speech HD", 11000),
    # Music
    "music-2.5": ("music-2.5", 4),
    "music-2.6": ("music-2.6", 100),
    "music-cover": ("music-cover", 100),
    # Lyrics
    "lyrics_generation": ("lyrics_generation", 100),
}


def get_quota_bucket(model: str) -> tuple[str, int]:
    """Return (bucket_name, daily_limit) for a model, defaults to (model, 9999)."""
    return QUOTA_BUCKETS.get(model, (model, 9999))


# ── Quota logger (tools pipeline) ───────────────────────────────────────────────

def log_quota_usage(
    quota_date: str,
    model: str,
    bucket_name: str,
    n_used: int = 1,
    source: str = "tools",
    run_id: str = "",
    category: str = "",
    notes: str = "",
) -> None:
    """
    Log quota usage from tools pipeline to the shared JSONL log file.
    This mirrors backend.quota_logger but runs in the tools process.
    """
    import json
    from datetime import datetime as dt

    log_path = PROJECT_ROOT / "works" / "quota_usage_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "record_id": "",
        "quota_date": quota_date,
        "model": model,
        "bucket_name": bucket_name,
        "n_used": n_used,
        "source": source,
        "run_id": run_id,
        "category": category,
        "notes": notes,
        "created_at": dt.utcnow().isoformat(),
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")