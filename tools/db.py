"""工具模块数据库层 — tools 任务专用（独立于 backend 的数据库操作）。"""

from datetime import date, datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, Text, ForeignKey, UniqueConstraint, create_engine, text
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# ── engine / session ─────────────────────────────────────────────────────────

_sqlite_engine = None
_sqlite_session_factory = None


def get_sqlite_engine():
    global _sqlite_engine
    if _sqlite_engine is None:
        DB_PATH = Path(__file__).parent.parent / "works" / "video-daily.db"
        _sqlite_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    return _sqlite_engine


def get_sqlite_session() -> Session:
    global _sqlite_session_factory
    if _sqlite_session_factory is None:
        _sqlite_session_factory = sessionmaker(bind=get_sqlite_engine())
    return _sqlite_session_factory()


_mysql_engine = None
_mysql_session_factory = None


def get_mysql_engine():
    global _mysql_engine
    if _mysql_engine is None:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        host = os.getenv("DB_HOST", "localhost")
        port = int(os.getenv("DB_PORT", "3306"))
        name = os.getenv("DB_NAME", "minimax-take")
        user = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "")
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
        _mysql_engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600, echo=False)
    return _mysql_engine


def get_mysql_session() -> Session:
    global _mysql_session_factory
    if _mysql_session_factory is None:
        _mysql_session_factory = sessionmaker(bind=get_mysql_engine())
    return _mysql_session_factory()


_use_mysql = False


def use_mysql(v: bool = True) -> None:
    global _use_mysql
    _use_mysql = v


def get_session() -> Session:
    return get_mysql_session() if _use_mysql else get_sqlite_session()


def get_engine():
    return get_mysql_engine() if _use_mysql else get_sqlite_engine()


# ── ORM models ───────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    __allow_unmapped__ = True


class Run(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True)
    theme = Column(String, nullable=False, default="giant-tree")
    category = Column(String, nullable=False)
    model = Column(String, nullable=False)
    variant = Column(String, nullable=True)
    version = Column(Integer, default=1)
    api_resp_id = Column(String, nullable=True)
    status = Column(String, default="success")
    error_msg = Column(Text, nullable=True)
    created_at = Column(String, nullable=False)
    quota_date = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    is_favorite = Column(Integer, default=0)
    matrix_name = Column(String, nullable=True)
    config_id = Column(Integer, nullable=True)

    assets: list["Asset"] = []


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False, unique=True)
    lang = Column(String, default="en")
    theme = Column(String, default="giant-tree")
    created_at = Column(String, nullable=False)

    assets: list["Asset"] = []


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=True)
    file_path = Column(String, nullable=False)
    external_url = Column(String, nullable=True)
    modality = Column(String, nullable=False)
    sub_type = Column(String, nullable=True)
    aspect_ratio = Column(String, nullable=True)
    seed = Column(Integer, nullable=True)
    created_at = Column(String, nullable=False)


class Quota(Base):
    __tablename__ = "quotas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quota_date = Column(String, nullable=False)
    model = Column(String, nullable=False)
    bucket_name = Column(String, nullable=False)
    daily_limit = Column(Integer, nullable=False)
    used = Column(Integer, default=0)

    __table_args__ = (UniqueConstraint("quota_date", "model", name="uix_quota_date_model"),)


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)


def upsert_prompt(session: Session, prompt_text: str, lang: str = "en", theme: str = "giant-tree") -> Prompt:
    row = session.execute(
        text("SELECT id FROM prompts WHERE text = :t"),
        {"t": prompt_text}
    ).fetchone()
    if row:
        return session.query(Prompt).get(row[0])
    p = Prompt(text=prompt_text, lang=lang, theme=theme, created_at=datetime.utcnow().isoformat())
    session.add(p)
    session.flush()
    return p


def create_run(session: Session, run_id: str, category: str, model: str,
               variant: str | None = None, theme: str = "giant-tree",
               api_resp_id: str | None = None, status: str = "success",
               error_msg: str | None = None, notes: str | None = None,
               matrix_name: str | None = None, config_id: int | None = None) -> Run:
    today = date.today().isoformat()
    run = Run(id=run_id, theme=theme, category=category, model=model,
              variant=variant, version=1, api_resp_id=api_resp_id,
              status=status, error_msg=error_msg,
              created_at=datetime.utcnow().isoformat(), quota_date=today, notes=notes,
              matrix_name=matrix_name, config_id=config_id)
    session.add(run)
    session.flush()
    return run


def create_asset(session: Session, run_id: str, file_path: str, modality: str,
                 sub_type: str | None = None,
                 prompt_id: int | None = None, aspect_ratio: str | None = None,
                 seed: int | None = None) -> Asset:
    asset = Asset(run_id=run_id, prompt_id=prompt_id, file_path=file_path,
                  modality=modality, sub_type=sub_type,
                  aspect_ratio=aspect_ratio, seed=seed,
                  created_at=datetime.utcnow().isoformat())
    session.add(asset)
    session.flush()
    return asset


def get_or_create_quota(session: Session, quota_date: str, model: str,
                        bucket_name: str, daily_limit: int) -> Quota:
    row = session.execute(
        text("SELECT id FROM quotas WHERE quota_date = :d AND model = :m"),
        {"d": quota_date, "m": model}
    ).fetchone()
    if row:
        return session.query(Quota).get(row[0])
    q = Quota(quota_date=quota_date, model=model, bucket_name=bucket_name,
              daily_limit=daily_limit, used=0)
    session.add(q)
    session.flush()
    return q


def get_quota_status(session: Session, quota_date: str | None = None) -> list[Quota]:
    d = quota_date or date.today().isoformat()
    return session.query(Quota).where(Quota.quota_date == d).all()