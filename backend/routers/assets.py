"""
资产路由 /api/assets
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Asset, Run
from backend.schemas import AssetCreate, AssetUpdate, AssetResponse

router = APIRouter()


@router.get("", response_model=list[AssetResponse])
def list_assets(
    modality: str | None = None,
    category: str | None = None,
    model: str | None = None,
    theme: str | None = None,
    status: str | None = None,
    quota_date: str | None = None,
    favorites_only: bool = False,
    search_text: str | None = None,
    limit: int = 300,
    db: Session = Depends(get_db),
):
    """
    查询资产列表（支持多条件过滤）
    JOIN runs 表以支持 category/model/theme/status/favorites 过滤
    JOIN prompts 表以支持 search_text 搜索
    """
    sql = """
        SELECT a.id, a.run_id, a.file_path, a.modality, a.sub_type,
               a.aspect_ratio, a.seed, a.created_at, a.external_url,
               r.theme, r.category, r.model, r.status, r.is_favorite,
               p.text as prompt_text
        FROM assets a
        JOIN runs r ON r.id = a.run_id
        LEFT JOIN prompts p ON p.id = a.prompt_id
        WHERE 1=1
    """
    params = {}
    if modality:
        sql += " AND a.modality = :modality"
        params["modality"] = modality
    if category:
        sql += " AND r.category = :category"
        params["category"] = category
    if model:
        sql += " AND r.model = :model"
        params["model"] = model
    if theme:
        sql += " AND r.theme LIKE :theme"
        params["theme"] = f"%{theme}%"
    if status:
        sql += " AND r.status = :status"
        params["status"] = status
    if quota_date:
        sql += " AND r.quota_date = :quota_date"
        params["quota_date"] = quota_date
    if favorites_only:
        sql += " AND r.is_favorite = 1"
    if search_text:
        sql += " AND p.text LIKE :search_text"
        params["search_text"] = f"%{search_text}%"
    sql += " ORDER BY a.created_at DESC LIMIT :limit"
    params["limit"] = limit

    rows = db.execute(text(sql), params).fetchall()
    return [
        AssetResponse(
            id=row[0],
            run_id=row[1],
            file_path=row[2],
            modality=row[3],
            sub_type=row[4],
            aspect_ratio=row[5],
            seed=row[6],
            created_at=row[7],
            external_url=row[8],
            theme=row[9],
            category=row[10],
            model=row[11],
            status=row[12],
            is_favorite=row[13],
            prompt_text=row[14] or "",
        )
        for row in rows
    ]


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    a = db.query(Asset).filter(Asset.id == asset_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="资产不存在")
    r = db.query(Run).filter(Run.id == a.run_id).first()
    prompt_text = ""
    if r:
        row = db.execute(
            text("SELECT text FROM prompts WHERE run_id = :rid LIMIT 1"),
            {"rid": r.id}
        ).fetchone()
        if row:
            prompt_text = row[0]
    return AssetResponse(
        id=a.id,
        run_id=a.run_id,
        file_path=a.file_path,
        modality=a.modality,
        sub_type=a.sub_type,
        aspect_ratio=a.aspect_ratio,
        seed=a.seed,
        created_at=a.created_at,
        external_url=a.external_url,
        theme=r.theme if r else "",
        category=r.category if r else "",
        model=r.model if r else "",
        status=r.status if r else "",
        is_favorite=r.is_favorite if r else 0,
        prompt_text=prompt_text,
    )


@router.post("", response_model=AssetResponse)
def create_asset(data: AssetCreate, db: Session = Depends(get_db)):
    a = Asset(
        run_id=data.run_id,
        file_path=data.file_path,
        modality=data.modality,
        sub_type=data.sub_type,
        aspect_ratio=data.aspect_ratio,
        seed=data.seed,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    r = db.query(Run).filter(Run.id == a.run_id).first()
    return AssetResponse(
        id=a.id,
        run_id=a.run_id,
        file_path=a.file_path,
        modality=a.modality,
        sub_type=a.sub_type,
        aspect_ratio=a.aspect_ratio,
        seed=a.seed,
        created_at=a.created_at,
        external_url=a.external_url,
        theme=r.theme if r else "",
        category=r.category if r else "",
        model=r.model if r else "",
        status=r.status if r else "",
        is_favorite=r.is_favorite if r else 0,
        prompt_text="",
    )


@router.patch("/{asset_id}", response_model=AssetResponse)
def update_asset(asset_id: int, data: AssetUpdate, db: Session = Depends(get_db)):
    a = db.query(Asset).filter(Asset.id == asset_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="资产不存在")
    if data.external_url is not None:
        a.external_url = data.external_url
    db.commit()
    r = db.query(Run).filter(Run.id == a.run_id).first()
    return AssetResponse(
        id=a.id,
        run_id=a.run_id,
        file_path=a.file_path,
        modality=a.modality,
        sub_type=a.sub_type,
        aspect_ratio=a.aspect_ratio,
        seed=a.seed,
        created_at=a.created_at,
        external_url=a.external_url,
        theme=r.theme if r else "",
        category=r.category if r else "",
        model=r.model if r else "",
        status=r.status if r else "",
        is_favorite=r.is_favorite if r else 0,
        prompt_text="",
    )


@router.get("/picker")
def picker_assets(
    modality: str = "image",
    search: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    轻量图片选择器接口，返回图片资产列表（支持搜索）。
    用于 i2i 矩阵等场景选择参考图。
    """
    sql = """
        SELECT a.id, a.run_id, a.file_path, a.modality, a.sub_type,
               a.aspect_ratio, a.seed, a.created_at, a.external_url,
               r.theme, r.category, r.model, r.status, r.is_favorite,
               p.text as prompt_text
        FROM assets a
        JOIN runs r ON r.id = a.run_id
        LEFT JOIN prompts p ON p.id = a.prompt_id
        WHERE a.modality = :modality
    """
    params: dict = {"modality": modality, "limit": limit}
    if search:
        sql += " AND p.text LIKE :search"
        params["search"] = f"%{search}%"
    sql += " ORDER BY a.created_at DESC LIMIT :limit"

    rows = db.execute(text(sql), params).fetchall()
    return [
        AssetResponse(
            id=row[0],
            run_id=row[1],
            file_path=row[2],
            modality=row[3],
            sub_type=row[4],
            aspect_ratio=row[5],
            seed=row[6],
            created_at=row[7],
            external_url=row[8],
            theme=row[9],
            category=row[10],
            model=row[11],
            status=row[12],
            is_favorite=row[13],
            prompt_text=row[14] or "",
        )
        for row in rows
    ]
