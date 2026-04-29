"""
任务队列路由 /api/tasks
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import TaskQueue, PromptHistory
from backend.schemas import (
    TaskQueueCreate, TaskQueueUpdate, TaskQueueResponse,
    PromptHistoryCreate, PromptHistoryResponse,
    AutoPromptRequest,
)
from backend.config import get_settings
from backend.task_runner import submit_task_async, _check_quota

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────────

def _category_modality(category: str) -> str:
    if category in ("t2i", "i2i"):
        return "image"
    if category in ("t2v", "i2v", "fl2v", "s2v"):
        return "video"
    if category == "music":
        return "music"
    return "image"


# ── task queue CRUD ───────────────────────────────────────────────────────────

@router.get("", response_model=list[TaskQueueResponse])
def list_tasks(
    quota_date: str | None = None,
    task_type: str | None = None,
    status: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """查询任务队列（支持按日期/类型/状态过滤）"""
    q = db.query(TaskQueue)
    if quota_date:
        q = q.filter(TaskQueue.quota_date == quota_date)
    if task_type:
        q = q.filter(TaskQueue.task_type == task_type)
    if status:
        q = q.filter(TaskQueue.status == status)
    return q.order_by(TaskQueue.priority.asc(), TaskQueue.created_at.asc()).limit(limit).all()


@router.post("", response_model=TaskQueueResponse)
def create_task(data: TaskQueueCreate, db: Session = Depends(get_db)):
    """创建用户任务（有额度时立即后台执行，否则加入队列等待调度）"""
    today = date.today().isoformat()
    task = TaskQueue(
        task_type="user",
        category=data.category,
        prompt_text=data.prompt_text,
        model=data.model,
        modality=_category_modality(data.category),
        status="pending",
        priority=1,   # user = 优先
        notes=data.notes,
        image=data.image,
        image2=data.image2,
        quota_date=today,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 立即检查额度，有额度则后台执行
    if _check_quota(data.model):
        task_data = {
            "category": task.category,
            "prompt_text": task.prompt_text,
            "model": task.model,
            "image": task.image,
            "image2": task.image2,
            "theme": "giant-tree",
        }
        submit_task_async(task.id, task_data)
        # 立即更新状态为 running，前端可感知
        task.status = "running"
        db.commit()
        db.refresh(task)

    return task


@router.patch("/{task_id}", response_model=TaskQueueResponse)
def update_task(task_id: int, data: TaskQueueUpdate, db: Session = Depends(get_db)):
    """更新任务状态（scheduler 使用）"""
    task = db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if data.status is not None:
        task.status = data.status
    if data.run_id is not None:
        task.run_id = data.run_id
    if data.error_msg is not None:
        task.error_msg = data.error_msg
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """删除任务"""
    task = db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.delete(task)
    db.commit()
    return {"ok": True}


# ── prompt history ────────────────────────────────────────────────────────────

@router.get("/history", response_model=list[PromptHistoryResponse])
def list_prompt_history(
    direction: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """查询 prompt 历史（用于去重参考）"""
    q = db.query(PromptHistory)
    if direction:
        q = q.filter(PromptHistory.direction == direction)
    return q.order_by(PromptHistory.created_at.desc()).limit(limit).all()


@router.post("/history", response_model=PromptHistoryResponse)
def add_prompt_history(data: PromptHistoryCreate, db: Session = Depends(get_db)):
    """记录已使用的 prompt（自动由 scheduler 调用）"""
    # 查重
    existing = db.query(PromptHistory).filter(PromptHistory.text == data.text).first()
    if existing:
        return existing
    row = PromptHistory(
        text=data.text,
        direction=data.direction,
        lang=data.lang,
        theme=data.theme,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/directions", response_model=list[str])
def list_directions(db: Session = Depends(get_db)):
    """查询所有已用方向（用于 UI 下拉选择）"""
    rows = db.query(PromptHistory.direction).distinct().all()
    return [r[0] for r in rows]


# ── auto prompt 生成 ─────────────────────────────────────────────────────────

@router.post("/auto/generate")
def generate_auto_prompts(req: AutoPromptRequest, db: Session = Depends(get_db)):
    """
    调用 LLM 根据方向生成 Auto 任务 prompt。
    会自动过滤掉与历史 prompt 重复的结果。
    API 文档：ref/api/text/文本对话（OpenAI_API_兼容）.md
    """
    import requests as _requests

    settings = get_settings()
    categories = req.categories or ["t2i", "t2v", "i2v", "music"]
    category_str = ", ".join(categories)

    # 拉取历史 prompt 用于去重
    all_history = db.query(PromptHistory.text).all()
    all_texts = set(r[0] for r in all_history)

    history_same_dir = db.query(PromptHistory.text).filter(
        PromptHistory.direction == req.direction
    ).all()
    history_texts = [r[0] for r in history_same_dir[-20:]]
    history_context = "\n".join(f"- {t}" for t in history_texts) or "(none yet)"

    system_prompt = (
        "You are a creative prompt generator for a giant-tree world theme. "
        "Generate vivid, specific image/video/music generation prompts. "
        "Each prompt must be unique and different from all previous ones."
    )
    user_prompt = (
        f"Direction: {req.direction}\n"
        f"Theme: {req.theme}\n"
        f"Allowed types: {category_str}\n"
        f"Generate exactly {req.count} prompts, each on its own line.\n"
        f"Format: CATEGORY::PROMPT_TEXT (e.g. t2i::A majestic griffin knight...)\n"
        f"Previous prompts in this direction (avoid these):\n{history_context}"
    )

    resp = _requests.post(
        "https://api.minimaxi.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.minimax_api_key}", "Content-Type": "application/json"},
        json={
            "model": "MiniMax-M2.7",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 1024,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]

    # 解析每行 CATEGORY::PROMPT
    created = []
    for line in content.strip().split("\n"):
        line = line.strip()
        if "::" not in line:
            continue
        cat, _, prompt_text = line.partition("::")
        cat = cat.strip().lower()
        prompt_text = prompt_text.strip()

        if not prompt_text or cat not in categories:
            continue
        if prompt_text in all_texts:
            continue
        all_texts.add(prompt_text)

        task = TaskQueue(
            task_type="auto",
            category=cat,
            prompt_text=prompt_text,
            model=_default_model(cat),
            modality=_category_modality(cat),
            status="pending",
            priority=10,
            quota_date=date.today().isoformat(),
        )
        db.add(task)

        hist = PromptHistory(
            text=prompt_text,
            direction=req.direction,
            theme=req.theme,
        )
        db.add(hist)
        created.append(cat)

    db.commit()
    return {"ok": True, "created": len(created), "categories": created}


def _default_model(category: str) -> str:
    defaults = {
        "t2i": "image-01",
        "i2i": "image-01",
        "t2v": "MiniMax-Hailuo-2.3",
        "i2v": "MiniMax-Hailuo-2.3-Fast",
        "fl2v": "MiniMax-Hailuo-02",
        "s2v": "S2V-01",
        "music": "music-2.6",
    }
    return defaults.get(category, "image-01")
