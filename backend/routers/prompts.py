"""
提示词库路由 /api/prompts
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Prompt
from backend.schemas import PromptCreate, PromptResponse

router = APIRouter()


@router.get("", response_model=list[PromptResponse])
def list_prompts(
    theme: str | None = None,
    search: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """查询提示词列表（支持主题过滤和全文搜索）"""
    q = db.query(Prompt)
    if theme:
        q = q.filter(Prompt.theme.like(f"%{theme}%"))
    if search:
        q = q.filter(Prompt.text.like(f"%{search}%"))
    prompts = q.order_by(Prompt.created_at.desc()).limit(limit).all()
    return [PromptResponse.model_validate(p) for p in prompts]


@router.get("/{prompt_id}", response_model=PromptResponse)
def get_prompt(prompt_id: int, db: Session = Depends(get_db)):
    p = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="提示词不存在")
    return PromptResponse.model_validate(p)


@router.post("", response_model=PromptResponse)
def create_prompt(data: PromptCreate, db: Session = Depends(get_db)):
    """创建提示词（自动去重）"""
    existing = db.query(Prompt).filter(Prompt.text == data.text).first()
    if existing:
        return PromptResponse.model_validate(existing)
    p = Prompt(
        text=data.text,
        lang=data.lang,
        theme=data.theme,
        run_id=data.run_id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return PromptResponse.model_validate(p)


@router.get("/{prompt_id}/assets")
def get_prompt_assets(prompt_id: int, db: Session = Depends(get_db)):
    """获取使用某提示词生成的所有资产"""
    p = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="提示词不存在")
    return {
        "prompt_id": p.id,
        "text": p.text,
        "run_id": p.run_id,
        "assets": [],
    }
