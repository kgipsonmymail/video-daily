"""
运行任务路由 /api/runs
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Run, Asset
from backend.schemas import RunCreate, RunUpdate, RunResponse

router = APIRouter()


@router.get("", response_model=list[RunResponse])
def list_runs(
    category: str | None = None,
    model: str | None = None,
    theme: str | None = None,
    status: str | None = None,
    quota_date: str | None = None,
    favorites_only: bool = False,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """查询运行任务列表（支持过滤）"""
    q = db.query(Run)
    if category:
        q = q.filter(Run.category == category)
    if model:
        q = q.filter(Run.model == model)
    if theme:
        q = q.filter(Run.theme.like(f"%{theme}%"))
    if status:
        q = q.filter(Run.status == status)
    if quota_date:
        q = q.filter(Run.quota_date == quota_date)
    if favorites_only:
        q = q.filter(Run.is_favorite == 1)

    runs = q.order_by(Run.created_at.desc()).limit(limit).all()

    # 附加 asset_count
    result = []
    for r in runs:
        asset_count = db.query(Asset).filter(Asset.run_id == r.id).count()
        resp = RunResponse(
            id=r.id,
            theme=r.theme,
            category=r.category,
            model=r.model,
            variant=r.variant,
            notes=r.notes,
            status=r.status,
            error_msg=r.error_msg,
            is_favorite=r.is_favorite,
            created_at=r.created_at,
            quota_date=r.quota_date,
            asset_count=asset_count,
        )
        result.append(resp)
    return result


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    """获取单个任务详情"""
    r = db.query(Run).filter(Run.id == run_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="任务不存在")
    asset_count = db.query(Asset).filter(Asset.run_id == r.id).count()
    return RunResponse(
        id=r.id,
        theme=r.theme,
        category=r.category,
        model=r.model,
        variant=r.variant,
        notes=r.notes,
        status=r.status,
        error_msg=r.error_msg,
        is_favorite=r.is_favorite,
        created_at=r.created_at,
        quota_date=r.quota_date,
        asset_count=asset_count,
    )


@router.post("", response_model=RunResponse)
def create_run(data: RunCreate, db: Session = Depends(get_db)):
    """创建新的运行任务记录"""
    r = Run(
        id=data.id,
        theme=data.theme,
        category=data.category,
        model=data.model,
        variant=data.variant,
        notes=data.notes,
        status=data.status,
        error_msg=data.error_msg,
        quota_date=data.quota_date,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return RunResponse(
        id=r.id,
        theme=r.theme,
        category=r.category,
        model=r.model,
        variant=r.variant,
        notes=r.notes,
        status=r.status,
        error_msg=r.error_msg,
        is_favorite=r.is_favorite,
        created_at=r.created_at,
        quota_date=r.quota_date,
        asset_count=0,
    )


@router.patch("/{run_id}", response_model=RunResponse)
def update_run(run_id: str, data: RunUpdate, db: Session = Depends(get_db)):
    """更新任务（收藏/备注）"""
    r = db.query(Run).filter(Run.id == run_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="任务不存在")
    if data.notes is not None:
        r.notes = data.notes
    if data.is_favorite is not None:
        r.is_favorite = 1 if data.is_favorite else 0
    db.commit()
    asset_count = db.query(Asset).filter(Asset.run_id == r.id).count()
    return RunResponse(
        id=r.id,
        theme=r.theme,
        category=r.category,
        model=r.model,
        variant=r.variant,
        notes=r.notes,
        status=r.status,
        error_msg=r.error_msg,
        is_favorite=r.is_favorite,
        created_at=r.created_at,
        quota_date=r.quota_date,
        asset_count=asset_count,
    )


@router.post("/{run_id}/toggle-favorite", response_model=RunResponse)
def toggle_favorite(run_id: str, db: Session = Depends(get_db)):
    """切换收藏状态"""
    r = db.query(Run).filter(Run.id == run_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="任务不存在")
    r.is_favorite = 1 if r.is_favorite == 0 else 0
    db.commit()
    asset_count = db.query(Asset).filter(Asset.run_id == r.id).count()
    return RunResponse(
        id=r.id,
        theme=r.theme,
        category=r.category,
        model=r.model,
        variant=r.variant,
        notes=r.notes,
        status=r.status,
        error_msg=r.error_msg,
        is_favorite=r.is_favorite,
        created_at=r.created_at,
        quota_date=r.quota_date,
        asset_count=asset_count,
    )
