"""
SQLAlchemy ORM 模型 — minimax-take 数据库表结构
使用 SQLAlchemy 2.0 Annotated Declarative 风格
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


class Run(Base):
    __tablename__ = "runs"
    __allow_unmapped__ = True

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    theme: Mapped[str] = mapped_column(String(64), default="giant-tree")
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    variant: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="success")
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    quota_date: Mapped[str] = mapped_column(String(10), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    matrix_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    assets: Mapped[List["Asset"]] = relationship(
        "Asset", back_populates="run", cascade="all, delete-orphan"
    )


class Asset(Base):
    __tablename__ = "assets"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("runs.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(256), nullable=False)
    external_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    modality: Mapped[str] = mapped_column(String(16), nullable=False)
    sub_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    aspect_ratio: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    prompt_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("prompts.id"), nullable=True)

    run: Mapped["Run"] = relationship("Run", back_populates="assets")
    prompt: Mapped[Optional["Prompt"]] = relationship("Prompt", back_populates="assets")


class Prompt(Base):
    __tablename__ = "prompts"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    lang: Mapped[str] = mapped_column(String(8), default="en")
    theme: Mapped[str] = mapped_column(String(64), default="giant-tree")
    run_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("runs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    assets: Mapped[list["Asset"]] = relationship("Asset", back_populates="prompt")


class Quota(Base):
    __tablename__ = "quotas"
    __table_args__ = (
        UniqueConstraint("quota_date", "model", name="uix_quota_date_model"),
    )
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quota_date: Mapped[str] = mapped_column(String(10), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    bucket_name: Mapped[str] = mapped_column(String(64), nullable=False)
    daily_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    used: Mapped[int] = mapped_column(Integer, default=0)


class TaskQueue(Base):
    """用户任务队列，每天 8 点调度器按优先级执行。"""
    __tablename__ = "task_queue"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(8), nullable=False)   # user | auto
    category: Mapped[str] = mapped_column(String(16), nullable=False)   # t2i | i2i | t2v | i2v | fl2v | s2v | music
    prompt_text: Mapped[str] = mapped_column(String(1024), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    modality: Mapped[str] = mapped_column(String(16), nullable=False)  # image | video | music
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | running | done | failed
    run_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # 关联的 run_id
    priority: Mapped[int] = mapped_column(Integer, default=10)  # 越小越先，user=1, auto=10
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # base64 image for i2i/i2v/s2v
    image2: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # base64 last-frame for fl2v
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    quota_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD，计划执行日期


class PromptHistory(Base):
    """Prompt 历史记录，用于 Auto 任务去重。"""
    __tablename__ = "prompt_history"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    direction: Mapped[str] = mapped_column(String(256), nullable=False)  # 所属方向/主题
    lang: Mapped[str] = mapped_column(String(8), default="en")
    theme: Mapped[str] = mapped_column(String(64), default="giant-tree")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VoiceSample(Base):
    """T2S 音色示例音频，记录已生成的案例。"""
    __tablename__ = "voice_samples"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    voice_id: Mapped[str] = mapped_column(String(128), nullable=False)   # MiniMax voice_id
    voice_name: Mapped[str] = mapped_column(String(128), nullable=False)  # 显示名称
    lang: Mapped[str] = mapped_column(String(16), default="zh")           # 音色语言
    model: Mapped[str] = mapped_column(String(64), default="speech-2.8-hd")
    script_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 使用的讲稿
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)   # 本地文件路径
    file_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # 访问URL
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class QuotaUsageLog(Base):
    """每次 API 额度调用记录（全局日志）"""
    __tablename__ = "quota_usage_log"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    quota_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    bucket_name: Mapped[str] = mapped_column(String(64), nullable=False)
    n_used: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(16), nullable=False)   # backend | tools | scheduler | claude
    run_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
