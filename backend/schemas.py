"""
Pydantic 请求/响应模型
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


# ── Run ──────────────────────────────────────────────────────────────────────

class RunBase(BaseModel):
    theme: str = "giant-tree"
    category: str
    model: str
    variant: Optional[str] = None
    notes: Optional[str] = None


class RunCreate(RunBase):
    """创建运行任务的请求体"""
    id: str
    quota_date: str  # YYYY-MM-DD
    status: str = "success"
    error_msg: Optional[str] = None


class RunUpdate(BaseModel):
    """更新运行任务（收藏/备注）"""
    notes: Optional[str] = None
    is_favorite: Optional[bool] = None


class RunResponse(RunBase):
    """运行任务响应"""
    id: str
    status: str
    error_msg: Optional[str]
    is_favorite: int
    created_at: datetime
    quota_date: str
    asset_count: int = 0

    class Config:
        from_attributes = True


# ── Asset ────────────────────────────────────────────────────────────────────

class AssetBase(BaseModel):
    run_id: str
    file_path: str
    modality: str
    sub_type: Optional[str] = None
    aspect_ratio: Optional[str] = None
    seed: Optional[int] = None


class AssetCreate(AssetBase):
    """创建资产记录"""
    pass


class AssetUpdate(BaseModel):
    """更新资产（设置云盘链接）"""
    external_url: Optional[str] = None


class AssetResponse(AssetBase):
    """资产响应（含关联字段）"""
    id: int
    external_url: Optional[str]
    created_at: datetime
    # JOIN 来的字段
    theme: str = ""
    category: str = ""
    model: str = ""
    status: str = ""
    is_favorite: int = 0
    prompt_text: str = ""

    class Config:
        from_attributes = True


# ── Prompt ───────────────────────────────────────────────────────────────────

class PromptBase(BaseModel):
    text: str
    lang: str = "en"
    theme: str = "giant-tree"


class PromptCreate(PromptBase):
    run_id: Optional[str] = None


class PromptResponse(PromptBase):
    id: int
    run_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Quota ────────────────────────────────────────────────────────────────────

class QuotaCreate(BaseModel):
    quota_date: str
    model: str
    bucket_name: str
    daily_limit: int


class QuotaUpdate(BaseModel):
    """更新已用额度"""
    used: int


class QuotaResponse(BaseModel):
    id: int
    quota_date: str
    model: str
    bucket_name: str
    daily_limit: int
    used: int
    remaining: int = 0

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, q):
        return cls(
            id=q.id,
            quota_date=q.quota_date,
            model=q.model,
            bucket_name=q.bucket_name,
            daily_limit=q.daily_limit,
            used=q.used,
            remaining=max(0, q.daily_limit - q.used),
        )


# ── Matrix Config ─────────────────────────────────────────────────────────────

class MusicMatrixConfigCreate(BaseModel):
    name: str
    row_styles: list[str]  # 6 个游戏场景主题
    col_styles: list[str]  # 6 个乐器/风格
    base_prompt: str = "game background music, instrumental"
    notes: Optional[str] = None


class MusicMatrixConfigResponse(BaseModel):
    id: int
    name: str
    prompts_text: str  # "row_index,col_index::prompt" 格式，36 行
    theme: str
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class MusicTrackResponse(BaseModel):
    row: int
    col: int
    prompt: str
    file_path: str
    status: str  # generating | done | failed
    error: Optional[str] = None


class MatrixConfigCreate(BaseModel):
    name: str
    subjects_text: str  # newline-separated entity prompts
    styles_text: str    # newline-separated style prompts
    theme: str = "giant-tree"
    notes: Optional[str] = None
    prompt_base: Optional[str] = None  # base prompt used for all cells


class MatrixConfigResponse(BaseModel):
    id: int
    name: str
    subjects_text: str
    styles_text: str
    theme: str
    notes: Optional[str]
    created_at: datetime
    prompt_base: str = ""

    class Config:
        from_attributes = True

class RunFilters(BaseModel):
    category: Optional[str] = None
    model: Optional[str] = None
    theme: Optional[str] = None
    status: Optional[str] = None
    quota_date: Optional[str] = None
    favorites_only: bool = False
    limit: int = 200


class AssetFilters(BaseModel):
    modality: Optional[str] = None
    category: Optional[str] = None
    model: Optional[str] = None
    theme: Optional[str] = None
    status: Optional[str] = None
    quota_date: Optional[str] = None
    favorites_only: bool = False
    search_text: Optional[str] = None
    limit: int = 300


# ── TaskQueue ─────────────────────────────────────────────────────────────────

class TaskQueueCreate(BaseModel):
    """创建队列任务（用户手动提交）"""
    category: str          # t2i | i2i | t2v | i2v | fl2v | s2v | music
    prompt_text: str
    model: str
    notes: Optional[str] = None
    image: Optional[str] = None   # base64 encoded image for i2v/fl2v/s2v/i2i
    image2: Optional[str] = None   # base64 last-frame for fl2v


class TaskQueueUpdate(BaseModel):
    """更新队列任务状态"""
    status: Optional[str] = None
    run_id: Optional[str] = None
    error_msg: Optional[str] = None


class TaskQueueResponse(BaseModel):
    id: int
    task_type: str
    category: str
    prompt_text: str
    model: str
    modality: str
    status: str
    run_id: Optional[str]
    priority: int
    error_msg: Optional[str]
    notes: Optional[str]
    created_at: datetime
    quota_date: str

    class Config:
        from_attributes = True


# ── PromptHistory ─────────────────────────────────────────────────────────────

class PromptHistoryCreate(BaseModel):
    text: str
    direction: str
    lang: str = "en"
    theme: str = "giant-tree"


class PromptHistoryResponse(PromptHistoryCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Auto Prompt 生成 ─────────────────────────────────────────────────────────

class AutoPromptRequest(BaseModel):
    """请求 LLM 生成一批 Auto prompt"""
    direction: str           # 方向描述，如"巨树世界的四季变化"
    theme: str = "giant-tree"
    count: int = 3           # 生成几条
    categories: Optional[list[str]] = None  # 指定类型，不指定则随机


# ── VoiceSample ─────────────────────────────────────────────────────────────────

class VoiceSampleCreate(BaseModel):
    voice_id: str
    voice_name: str
    lang: str = "zh"
    model: str = "speech-2.8-hd"
    script_text: Optional[str] = None
    file_path: str
    file_url: Optional[str] = None
    notes: Optional[str] = None


class VoiceSampleUpdate(BaseModel):
    notes: Optional[str] = None
    is_favorite: Optional[bool] = None


class VoiceSampleResponse(BaseModel):
    id: int
    voice_id: str
    voice_name: str
    lang: str
    model: str
    script_text: Optional[str]
    file_path: str
    file_url: Optional[str]
    notes: Optional[str]
    is_favorite: int
    created_at: datetime

    class Config:
        from_attributes = True
