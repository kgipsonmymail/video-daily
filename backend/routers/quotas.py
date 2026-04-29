"""
额度管理路由 /api/quotas
"""

from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Quota
from backend.schemas import QuotaCreate, QuotaUpdate, QuotaResponse
from backend.config import QUOTA_BUCKETS

router = APIRouter()


@router.get("", response_model=list[QuotaResponse])
def list_quotas(
    quota_date: str | None = None,
    db: Session = Depends(get_db),
):
    """查询额度列表（默认当天）"""
    q = db.query(Quota)
    if quota_date:
        q = q.filter(Quota.quota_date == quota_date)
    quotas = q.order_by(Quota.model).all()
    return [QuotaResponse.from_model(quota) for quota in quotas]


@router.get("/all", response_model=list[QuotaResponse])
def list_all_quota_types(
    quota_date: str | None = None,
    db: Session = Depends(get_db),
):
    """
    返回所有已知额度类型（QUOTA_BUCKETS）加上 DB 中的已用记录。
    未在 DB 中的类型返回 used=0 占位，便于前端展示完整列表。
    """
    today = quota_date or date.today().isoformat()
    # Fetch all DB records for this date
    rows = {q.model: q for q in db.query(Quota).filter(Quota.quota_date == today).all()}
    result = []
    for model, (bucket_name, daily_limit) in sorted(QUOTA_BUCKETS.items()):
        if model in rows:
            result.append(QuotaResponse.from_model(rows[model]))
        else:
            # Merge with DB state even if not yet created today
            result.append(QuotaResponse(
                id=0,
                quota_date=today,
                model=model,
                bucket_name=bucket_name,
                daily_limit=daily_limit,
                used=0,
                remaining=daily_limit,
            ))
    return result


@router.post("/init", response_model=list[QuotaResponse])
def init_all_quotas(quota_date: str | None = None, db: Session = Depends(get_db)):
    """
    确保当天所有已知额度类型都在 DB 中有记录（upsert）。
    返回完整的列表。
    """
    today = quota_date or date.today().isoformat()
    for model, (bucket_name, daily_limit) in QUOTA_BUCKETS.items():
        existing = db.query(Quota).filter(
            Quota.quota_date == today,
            Quota.model == model,
        ).first()
        if not existing:
            q = Quota(
                quota_date=today,
                model=model,
                bucket_name=bucket_name,
                daily_limit=daily_limit,
                used=0,
            )
            db.add(q)
    db.commit()
    # Return full list
    return list_all_quota_types(today, db)


@router.post("", response_model=QuotaResponse)
def create_or_update_quota(data: QuotaCreate, db: Session = Depends(get_db)):
    """创建或更新额度记录（UPSERT）"""
    existing = db.query(Quota).filter(
        Quota.quota_date == data.quota_date,
        Quota.model == data.model,
    ).first()
    if existing:
        existing.bucket_name = data.bucket_name
        existing.daily_limit = data.daily_limit
        db.commit()
        db.refresh(existing)
        return QuotaResponse.from_model(existing)
    q = Quota(
        quota_date=data.quota_date,
        model=data.model,
        bucket_name=data.bucket_name,
        daily_limit=data.daily_limit,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return QuotaResponse.from_model(q)


@router.patch("/{quota_id}", response_model=QuotaResponse)
def update_quota(quota_id: int, data: QuotaUpdate, db: Session = Depends(get_db)):
    """更新已用额度"""
    q = db.query(Quota).filter(Quota.id == quota_id).first()
    if not q:
        q = Quota(
            quota_date="",
            model="",
            bucket_name="",
            daily_limit=0,
            used=0,
        )
    q.used = data.used
    db.commit()
    db.refresh(q)
    return QuotaResponse.from_model(q)
