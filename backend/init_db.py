"""初始化脚本 — 创建 minimax-take 数据库和所有表"""
import pymysql
from backend.config import get_settings

settings = get_settings()

conn = pymysql.connect(
    host=settings.db_host,
    port=settings.db_port,
    user=settings.db_user,
    password=settings.db_password,
    charset="utf8mb4",
)
try:
    with conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{settings.db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"[OK] Database '{settings.db_name}' created")
    conn.commit()
finally:
    conn.close()

from backend.models import Base
from backend.database import engine
Base.metadata.create_all(bind=engine)
print("[OK] All tables created")

# 确保 music_matrix_configs 表存在
from backend.database import get_db
with get_db() as db:
    from sqlalchemy import text
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS music_matrix_configs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            prompts_text TEXT NOT NULL,
            theme VARCHAR(64) DEFAULT 'game-bgm',
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    db.commit()
    print("[OK] music_matrix_configs table ensured")
