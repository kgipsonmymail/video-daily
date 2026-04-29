"""
将 SQLite 中的今日数据迁移到 MySQL
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
import src.db as db


ASSET_COLS = "id, run_id, prompt_id, file_path, file_url, modality, sub_type, aspect_ratio, seed, created_at, external_url"
RUN_COLS = "id, theme, category, model, variant, version, api_resp_id, status, error_msg, created_at, quota_date, notes, is_favorite"
PROMPT_COLS = "id, text, lang, theme, created_at"
QUOTA_COLS = "id, quota_date, model, bucket_name, daily_limit, used"


def rows_to_dicts(cols_str, rows):
    names = [c.strip() for c in cols_str.split(",")]
    return [{n: v for n, v in zip(names, r)} for r in rows]


def migrate():
    # 1. 从 SQLite 读取
    db.use_mysql(False)
    db.init_db()
    sqlite_sess = db.get_session()

    asset_dicts  = rows_to_dicts(ASSET_COLS,  sqlite_sess.execute(text(f"SELECT {ASSET_COLS} FROM assets WHERE created_at LIKE '2026-04-25%'")).fetchall())
    run_dicts    = rows_to_dicts(RUN_COLS,     sqlite_sess.execute(text(f"SELECT {RUN_COLS} FROM runs WHERE quota_date='2026-04-25'")).fetchall())
    quota_dicts  = rows_to_dicts(QUOTA_COLS,  sqlite_sess.execute(text(f"SELECT {QUOTA_COLS} FROM quotas WHERE quota_date='2026-04-25'")).fetchall())

    prompt_ids = {a["prompt_id"] for a in asset_dicts if a["prompt_id"]}
    prompt_dicts = rows_to_dicts(PROMPT_COLS, sqlite_sess.execute(
        text(f"SELECT {PROMPT_COLS} FROM prompts WHERE id IN ({','.join(map(str, prompt_ids))})")
    ).fetchall()) if prompt_ids else []

    print(f"Read from SQLite: {len(run_dicts)} runs, {len(asset_dicts)} assets, {len(prompt_dicts)} prompts, {len(quota_dicts)} quotas")

    # 2. 写入 MySQL
    db.use_mysql(True)
    db.init_db()
    mysql_engine = db.get_engine()

    with mysql_engine.connect() as conn:
        # prompts
        prompt_id_map = {}
        for pd in prompt_dicts:
            try:
                conn.execute(
                    text("""INSERT INTO prompts (text, lang, theme, created_at)
                             VALUES (:text, :lang, :theme, :created_at)
                             ON DUPLICATE KEY UPDATE text=text"""),
                    {"text": pd["text"], "lang": pd["lang"], "theme": pd["theme"], "created_at": pd["created_at"]}
                )
                existing = conn.execute(text("SELECT id FROM prompts WHERE text=:text"), {"text": pd["text"]}).fetchone()
                if existing:
                    prompt_id_map[pd["id"]] = existing[0]
            except Exception as e:
                print(f"Prompt error: {e}")
        print(f"Migrated {len(prompt_id_map)} prompts")

        # runs
        run_id_map = {}
        for rd in run_dicts:
            try:
                conn.execute(
                    text("""INSERT INTO runs (id, theme, category, model, variant, version, api_resp_id, status, error_msg, created_at, quota_date, notes, is_favorite)
                             VALUES (:id, :theme, :category, :model, :variant, :version, :api_resp_id, :status, :error_msg, :created_at, :quota_date, :notes, :is_favorite)
                             ON DUPLICATE KEY UPDATE status=status"""),
                    {
                        "id": rd["id"], "theme": rd["theme"], "category": rd["category"], "model": rd["model"],
                        "variant": rd["variant"], "version": rd["version"], "api_resp_id": rd["api_resp_id"],
                        "status": rd["status"], "error_msg": rd["error_msg"], "created_at": rd["created_at"],
                        "quota_date": rd["quota_date"], "notes": rd["notes"], "is_favorite": rd["is_favorite"] or 0
                    }
                )
                run_id_map[rd["id"]] = rd["id"]
            except Exception as e:
                print(f"Run error for {rd['id']}: {e}")
        print(f"Migrated {len(run_id_map)} runs")

        # assets
        asset_count = 0
        for ad in asset_dicts:
            mysql_run_id    = run_id_map.get(ad["run_id"],    ad["run_id"])
            mysql_prompt_id = prompt_id_map.get(ad["prompt_id"]) if ad["prompt_id"] else None
            try:
                conn.execute(
                    text("""INSERT INTO assets (run_id, prompt_id, file_path, file_url, modality, sub_type, aspect_ratio, seed, created_at, external_url)
                             VALUES (:run_id, :prompt_id, :file_path, :file_url, :modality, :sub_type, :aspect_ratio, :seed, :created_at, :external_url)"""),
                    {
                        "run_id": mysql_run_id, "prompt_id": mysql_prompt_id,
                        "file_path": ad["file_path"], "file_url": ad["file_url"],
                        "modality": ad["modality"], "sub_type": ad["sub_type"],
                        "aspect_ratio": ad["aspect_ratio"], "seed": ad["seed"],
                        "created_at": ad["created_at"], "external_url": ad["external_url"]
                    }
                )
                asset_count += 1
            except Exception as e:
                print(f"Asset error: {e}")
        print(f"Migrated {asset_count} assets")

        # quotas
        for qd in quota_dicts:
            try:
                conn.execute(
                    text("""INSERT INTO quotas (quota_date, model, bucket_name, daily_limit, used)
                             VALUES (:quota_date, :model, :bucket_name, :daily_limit, :used)
                             ON DUPLICATE KEY UPDATE used=:used"""),
                    {"quota_date": qd["quota_date"], "model": qd["model"],
                     "bucket_name": qd["bucket_name"], "daily_limit": qd["daily_limit"], "used": qd["used"]}
                )
            except Exception as e:
                print(f"Quota error: {e}")
        print(f"Migrated {len(quota_dicts)} quotas")

        conn.commit()

    # 验证
    db.use_mysql(True)
    s = db.get_session()
    cnt  = s.execute(text("SELECT COUNT(*) FROM assets WHERE created_at LIKE '2026-04-25%'")).fetchone()
    quot = s.execute(text("SELECT model, used, daily_limit FROM quotas WHERE quota_date='2026-04-25'")).fetchall()
    print(f"\nMySQL verified: {cnt[0]} assets for 2026-04-25")
    for q in quot:
        print(f"  Quota {q[0]}: used={q[1]}/{q[2]}")


if __name__ == "__main__":
    migrate()
