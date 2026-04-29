"""
从旧 SQLite 数据库迁移数据到 MySQL
运行一次即可: python migrate_from_sqlite.py
"""

from sqlalchemy import create_engine, text


def migrate():
    # 旧 SQLite
    sqlite_engine = create_engine(
        "sqlite:///works/video-daily.db",
        connect_args={"check_same_thread": False},
    )

    # 新 MySQL
    from backend.config import get_settings
    settings = get_settings()
    mysql_engine = create_engine(settings.database_url, pool_pre_ping=True)

    with sqlite_engine.connect() as src, mysql_engine.connect() as dst:
        # 迁移 runs
        print("[1/4] 迁移 runs...")
        rows = src.execute(text("SELECT * FROM runs")).fetchall()
        for row in rows:
            d = dict(row._mapping)
            dst.execute(
                text("""
                    INSERT IGNORE INTO runs (id, theme, category, model, variant, status, error_msg, is_favorite, created_at, quota_date, notes)
                    VALUES (:id, :theme, :category, :model, :variant, :status, :error_msg, :is_favorite, :created_at, :quota_date, :notes)
                """),
                {
                    "id": d["id"],
                    "theme": d.get("theme", "giant-tree"),
                    "category": d["category"],
                    "model": d["model"],
                    "variant": d.get("variant"),
                    "status": d.get("status", "success"),
                    "error_msg": d.get("error_msg"),
                    "is_favorite": d.get("is_favorite", 0),
                    "created_at": d["created_at"],
                    "quota_date": d["quota_date"],
                    "notes": d.get("notes"),
                },
            )
        dst.commit()
        print(f"  {len(rows)} runs")

        # 迁移 prompts
        print("[2/4] 迁移 prompts...")
        rows = src.execute(text("SELECT * FROM prompts")).fetchall()
        for row in rows:
            d = dict(row._mapping)
            dst.execute(
                text("""
                    INSERT IGNORE INTO prompts (text, lang, theme, run_id, created_at)
                    VALUES (:text, :lang, :theme, :run_id, :created_at)
                """),
                {
                    "text": d["text"][:512],
                    "lang": d.get("lang", "en"),
                    "theme": d.get("theme", "giant-tree"),
                    "run_id": d.get("run_id"),
                    "created_at": d["created_at"],
                },
            )
        dst.commit()
        print(f"  {len(rows)} prompts")

        # 迁移 assets
        print("[3/4] 迁移 assets...")
        rows = src.execute(text("SELECT * FROM assets")).fetchall()
        for row in rows:
            d = dict(row._mapping)
            dst.execute(
                text("""
                    INSERT IGNORE INTO assets (id, run_id, file_path, file_url, modality, sub_type, aspect_ratio, seed, created_at)
                    VALUES (:id, :run_id, :file_path, :file_url, :modality, :sub_type, :aspect_ratio, :seed, :created_at)
                """),
                {
                    "id": d["id"],
                    "run_id": d["run_id"],
                    "file_path": d["file_path"],
                    "file_url": d.get("file_url"),
                    "modality": d["modality"],
                    "sub_type": d.get("sub_type"),
                    "aspect_ratio": d.get("aspect_ratio"),
                    "seed": d.get("seed"),
                    "created_at": d["created_at"],
                },
            )
        dst.commit()
        print(f"  {len(rows)} assets")

        # 迁移 quotas
        print("[4/4] 迁移 quotas...")
        rows = src.execute(text("SELECT * FROM quotas")).fetchall()
        for row in rows:
            d = dict(row._mapping)
            dst.execute(
                text("""
                    INSERT IGNORE INTO quotas (quota_date, model, bucket_name, daily_limit, used)
                    VALUES (:quota_date, :model, :bucket_name, :daily_limit, :used)
                """),
                {
                    "quota_date": d["quota_date"],
                    "model": d["model"],
                    "bucket_name": d.get("bucket_name", d["model"]),
                    "daily_limit": d["daily_limit"],
                    "used": d.get("used", 0),
                },
            )
        dst.commit()
        print(f"  {len(rows)} quotas")

    print("[OK] 迁移完成!")


if __name__ == "__main__":
    migrate()
