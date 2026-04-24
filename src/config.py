"""配置管理"""

import os
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


def ensure_dirs() -> None:
    """确保必要的目录存在"""
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)


def get_api_key() -> str:
    """获取 API Key"""
    if not API_KEY:
        raise ValueError("MINIMAX_API_KEY not set. Copy .env.example to .env and fill in your API key.")
    return API_KEY