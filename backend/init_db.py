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
from backend.database import engine, SessionLocal
Base.metadata.create_all(bind=engine)
print("[OK] All tables created")

from sqlalchemy import text
db = SessionLocal()
try:
    # 确保 music_matrix_configs 表存在
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

    # 扩展 matrix_configs 表（i2i 批量图生图支持）
    for col_def in [
        "category VARCHAR(16) DEFAULT 't2i'",
        "reference_image TEXT",
        "rows_count INT DEFAULT 6",
        "cols_count INT DEFAULT 6",
    ]:
        col_name = col_def.split()[0]
        try:
            db.execute(text(f"ALTER TABLE matrix_configs ADD COLUMN {col_def}"))
            print(f"[OK] matrix_configs.{col_name} added")
        except Exception as e:
            print(f"[SKIP] matrix_configs.{col_name}: {e}")

    db.commit()
finally:
    db.close()

# 扩展 task_queue 表（新增参数列）
_db = SessionLocal()
try:
    for col_def, col_name in [
        ("ADD COLUMN aspect_ratio VARCHAR(8) DEFAULT '16:9'", "aspect_ratio"),
        ("ADD COLUMN duration INT DEFAULT 6", "duration"),
        ("ADD COLUMN resolution VARCHAR(8) DEFAULT '768P'", "resolution"),
        ("ADD COLUMN is_instrumental INT DEFAULT 0", "is_instrumental"),
    ]:
        try:
            _db.execute(text(f"ALTER TABLE task_queue {col_def}"))
            _db.commit()
            print(f"[OK] task_queue.{col_name} added")
        except Exception as e:
            print(f"[SKIP] task_queue.{col_name}: {e}")
finally:
    _db.close()
