"""
环境变量配置 — 从 .env 文件加载
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，读取 .env 环境变量"""

    # MiniMax API 密钥
    minimax_api_key: str = ""

    # MySQL 数据库连接
    db_host: str
    db_port: int = 3306
    db_name: str
    db_user: str
    db_password: str

    @property
    def database_url(self) -> str:
        """构建 SQLAlchemy 连接字符串"""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


# All MiniMax quota buckets: model key → (bucket_name, daily_limit)
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


@lru_cache
def get_settings() -> Settings:
    """单例配置实例"""
    return Settings()


def get_quota_bucket(model: str) -> tuple[str, int]:
    """Return (bucket_name, daily_limit) for a model, defaults to (model, 9999)."""
    return QUOTA_BUCKETS.get(model, (model, 9999))
