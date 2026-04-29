"""
生成路由 /api/generate — 直接调用 MiniMax API 生成内容（用于前端矩阵页等场景）
"""

import base64
import urllib.request
import uuid
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Run, Asset, Prompt, Quota
from backend.config import get_settings, get_quota_bucket, QUOTA_BUCKETS
from backend.quota_logger import log_quota_usage

router = APIRouter()


def _charge_quota(db: Session, quota_date: str, model: str, n: int = 1, category: str = ""):
    """Charge quota using centralized bucket config, logs to global logger."""
    bucket_name, limit = get_quota_bucket(model)
    row = db.execute(
        __import__("sqlalchemy").text(
            "SELECT id, used, daily_limit FROM quotas WHERE quota_date = :d AND model = :m"
        ),
        {"d": quota_date, "m": model},
    ).fetchone()
    if row:
        db.execute(
            __import__("sqlalchemy").text(
                "UPDATE quotas SET used = used + :n WHERE id = :id"
            ),
            {"n": n, "id": row[0]},
        )
    else:
        q = Quota(
            quota_date=quota_date,
            model=model,
            bucket_name=bucket_name,
            daily_limit=limit,
            used=n,
        )
        db.add(q)
    db.flush()
    # Global log
    log_quota_usage(
        quota_date=quota_date,
        model=model,
        bucket_name=bucket_name,
        n_used=n,
        source="backend",
        category=category,
    )


# ── schemas ─────────────────────────────────────────────────────────────────

class ImageGenerateRequest(BaseModel):
    prompt: str
    model: str = "image-01"
    aspect_ratio: str = "16:9"
    n: int = 1
    variant: str = "matrix"
    theme: str = "giant-tree"
    config_id: int | None = None
    matrix_name: str | None = None


class ImageGenerateResponse(BaseModel):
    run_id: str
    assets: list[dict]


# ── helpers ─────────────────────────────────────────────────────────────────

def _ts_prefix() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _slug(prompt: str, max_len: int = 30) -> str:
    return (
        prompt[:max_len]
        .replace(" ", "_")
        .replace(",", "")
        .replace("/", "-")
        .replace("\n", "_")
    )


def _local_to_data_url(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    suffix = "png" if image_path.suffix.lower() in (".png", "") else "jpeg"
    return f"data:image/{suffix};base64,{b64}"


def _mark_run(db: Session, run_id: str, status: str, api_resp_id: str | None = None,
              error_msg: str | None = None):
    from sqlalchemy import text
    params = {"s": status, "rid": run_id}
    if api_resp_id:
        params["aid"] = api_resp_id
    if error_msg:
        params["e"] = error_msg
    set_clause = "status = :s"
    if api_resp_id:
        set_clause += ", api_resp_id = :aid"
    if error_msg:
        set_clause += ", error_msg = :e"
    db.execute(text(f"UPDATE runs SET {set_clause} WHERE id = :rid"), params)


def _upsert_prompt(db: Session, text: str, theme: str) -> Prompt:
    row = db.execute(
        __import__("sqlalchemy").text(
            "SELECT id FROM prompts WHERE text = :t"
        ),
        {"t": text}
    ).fetchone()
    if row:
        return db.query(Prompt).get(row[0])
    p = Prompt(text=text, lang="en", theme=theme)
    db.add(p)
    db.flush()
    return p


# ── image generation ──────────────────────────────────────────────────────────

@router.post("/image", response_model=ImageGenerateResponse)
def generate_image(req: ImageGenerateRequest, db: Session = Depends(get_db)):
    """
    生成图片并写入数据库和文件系统。
    API 文档：ref/api/image/文生图.md
    """
    import requests as _requests

    settings = get_settings()
    ts = _ts_prefix()
    today = date.today().isoformat()
    run_id = f"{ts}__{req.theme}__{'t2i'}__{_slug(req.variant, 15)}__v001"

    try:
        # upsert prompt
        prompt_row = _upsert_prompt(db, req.prompt, req.theme)

        # 创建 run
        run = Run(
            id=run_id,
            theme=req.theme,
            category="t2i",
            model=req.model,
            variant=req.variant,
            status="running",
            quota_date=today,
            config_id=req.config_id,
            matrix_name=req.matrix_name,
        )
        db.add(run)
        db.flush()

        # 调用 MiniMax API
        payload = {
            "model": req.model,
            "prompt": req.prompt,
            "aspect_ratio": req.aspect_ratio,
            "n": req.n,
            "response_format": "url",
        }
        resp = _requests.post(
            "https://api.minimaxi.com/v1/image_generation",
            headers={
                "Authorization": f"Bearer {settings.minimax_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("base_resp", {}).get("status_code") != 0:
            raise Exception(f"API error: {data}")

        image_urls: list[str] = data.get("data", {}).get("image_urls", [])
        if not image_urls:
            raise Exception(f"No image URLs returned. API response: {data}")

        api_id = data.get("id", "")

        _mark_run(db, run_id, "success", api_resp_id=api_id)

        # 扣减额度
        _charge_quota(db, today, req.model, n=len(image_urls), category="t2i")

        # 保存目录
        proj_root = Path(__file__).parent.parent.parent
        out_dir = proj_root / "works" / today / "assets" / "images" / "t2i"
        out_dir.mkdir(parents=True, exist_ok=True)

        created_assets = []
        for i, url in enumerate(image_urls):
            fname = f"{run_id}_{i + 1}.png"
            out_path = out_dir / fname
            try:
                urllib.request.urlretrieve(url, out_path)
            except Exception as dl_err:
                print(f"[T2I] Download failed for {url}: {dl_err}")
                raise Exception(f"Failed to download image {i+1} from {url}: {dl_err}")

            rel_parts = out_path.relative_to(proj_root).parts
            rel = "/".join(rel_parts)  # includes 'works/' prefix for static file server

            asset = Asset(
                run_id=run_id,
                prompt_id=prompt_row.id,
                file_path=rel,
                modality="image",
                sub_type="t2i",
                aspect_ratio=req.aspect_ratio,
            )
            db.add(asset)
            db.flush()
            created_assets.append({
                "id": asset.id,
                "run_id": run_id,
                "file_path": rel,
                "modality": "image",
                "sub_type": "t2i",
                "aspect_ratio": req.aspect_ratio,
                "seed": None,
                "created_at": asset.created_at.isoformat() if asset.created_at else "",
                "external_url": None,
                "prompt_text": req.prompt,
            })
            print(f"[T2I] [{i + 1}/{len(image_urls)}] → {out_path}")

        db.commit()
        return ImageGenerateResponse(run_id=run_id, assets=created_assets)

    except Exception as exc:
        db.rollback()
        _mark_run(db, run_id, "failed", error_msg=str(exc))
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc))


# ── file upload ──────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    上传参考图片，返回文件路径（供 i2i/i2v/fl2v/s2v 任务使用）。
    文件保存到 works/uploads/ 目录。
    """
    proj_root = Path(__file__).parent.parent.parent
    upload_dir = proj_root / "works" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    ext = Path(file.filename or "image.png").suffix or ".png"
    safe_name = f"{ts}__{uuid.uuid4().hex[:8]}{ext}"
    out_path = upload_dir / safe_name

    content = await file.read()
    with open(out_path, "wb") as f:
        f.write(content)

    rel_path = f"works/uploads/{safe_name}"
    return {"file_path": rel_path, "url": f"/files/{rel_path}"}
