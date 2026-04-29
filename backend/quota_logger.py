"""
全局额度记录器 — 记录所有来源（backend API / tools pipeline / scheduler）的 API 调用。
写 JSONL 文件 + quota_usage_log DB 表。
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal


_log_path = Path(__file__).parent.parent / "works" / "quota_usage_log.jsonl"
_log_path.parent.mkdir(parents=True, exist_ok=True)


def log_quota_usage(
    quota_date: str,
    model: str,
    bucket_name: str,
    n_used: int = 1,
    source: Literal["backend", "tools", "scheduler", "claude"] = "backend",
    run_id: str = "",
    category: str = "",
    notes: str = "",
) -> str:
    """
    记录一次额度使用，同时写入 JSONL 和 DB 表 quota_usage_log。
    """
    record_id = uuid.uuid4().hex[:12]
    entry = {
        "record_id": record_id,
        "quota_date": quota_date,
        "model": model,
        "bucket_name": bucket_name,
        "n_used": n_used,
        "source": source,
        "run_id": run_id,
        "category": category,
        "notes": notes,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Always append to JSONL
    with open(_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Write to DB if session available (QuotaUsageLog is defined in backend/models.py)
    try:
        from backend.database import SessionLocal
        from backend.models import QuotaUsageLog

        session = SessionLocal()
        try:
            record = QuotaUsageLog(
                record_id=record_id,
                quota_date=quota_date,
                model=model,
                bucket_name=bucket_name,
                n_used=n_used,
                source=source,
                run_id=run_id or None,
                category=category or None,
                notes=notes or None,
            )
            session.add(record)
            session.commit()
        finally:
            session.close()
    except Exception:
        pass  # Never fail just because DB write fails

    return record_id
