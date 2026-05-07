"""
每日 8 点调度器 — 由 Windows 任务计划程序启动
逻辑：
  1. 优先执行所有 user 任务（按优先级排队）
  2. user 任务消耗完额度后，执行 auto 任务（直到当日额度耗尽）
  3. 每执行完一个任务，更新 task_queue.status
  4. 所有 prompt 记录写入 prompt_history（去重）

用法（Windows 任务计划程序）：
  操作：启动程序
  程序：python
  参数：F:\sys\...\video-daily\src\scheduler.py
  起始位置：F:\sys\...\video-daily

API 文档：ref/api/
"""

from datetime import date
import sys
from pathlib import Path

# 将项目根目录加入 import 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.config import ensure_dirs, get_api_key
from tools.client import MiniMaxClient
from tools.db import init_db, use_mysql, get_mysql_session, get_quota_status
from tools.image_tasks import run_t2i_task, run_i2i_task
from tools.video_tasks import run_t2v_task, run_i2v_task, run_fl2v_task, run_s2v_task
from tools.music_tasks import run_music_task

# ── 额度映射 ──────────────────────────────────────────────────────────────────

QUOTA_BUCKETS = {
    "image-01": {"name": "image-01", "daily": 120},
    "MiniMax-Hailuo-2.3": {"name": "Hailuo-2.3-768P 6s", "daily": 2},
    "MiniMax-Hailuo-2.3-Fast": {"name": "Hailuo-2.3-Fast-768P 6s", "daily": 2},
    "MiniMax-Hailuo-02": {"name": "Hailuo-02-768P 6s", "daily": 2},
    "S2V-01": {"name": "S2V-01 6s", "daily": 2},
    "music-2.6": {"name": "music-2.6", "daily": 100},
}


def _remaining(model: str) -> int:
    today = date.today().isoformat()
    session = get_mysql_session()
    quotas = get_quota_status(session, today)
    session.close()
    for q in quotas:
        if model in (q.model, q.bucket_name):
            return max(0, q.daily_limit - q.used)
    return QUOTA_BUCKETS.get(model, {}).get("daily", 999)


def _run_task(task: dict, client: MiniMaxClient) -> str | None:
    """执行单个任务，返回 run_id 或 None。"""
    cat = task["category"]
    prompt = task["prompt_text"]
    model = task["model"]
    theme = task.get("theme", "giant-tree")
    import base64, tempfile, os

    def _resolve_image_path(image_val: str | None) -> tuple[str | None, bool]:
        """将文件路径或 base64 字符串转为文件路径。Returns (path, is_temp)."""
        if not image_val:
            return None, False
        if image_val.startswith("data:"):
            # 兼容旧的 base64 格式 → 生成临时文件
            import base64, tempfile
            header, data = image_val.split(",", 1)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
                f.write(base64.b64decode(data))
                return f.name, True
        # 新的文件路径格式: works/uploads/xxx.png → 真实文件，不删
        proj_root = Path(__file__).parent.parent
        full_path = proj_root / image_val
        if full_path.exists():
            return str(full_path), False
        print(f"[WARN] Image file not found: {full_path}")
        return None, False

    try:
        if cat == "t2i":
            aspect_ratio = task.get("aspect_ratio", "16:9")
            paths, rid = run_t2i_task(client, prompt, variant="scheduler", model=model,
                                       theme=theme, n=1, aspect_ratio=aspect_ratio)
            return rid
        elif cat == "i2i":
            img_path, is_temp = _resolve_image_path(task.get("image"))
            if not img_path:
                print("[SKIP] i2i missing image")
                return None
            aspect_ratio = task.get("aspect_ratio", "16:9")
            try:
                paths, rid = run_i2i_task(client, prompt, img_path, variant="scheduler",
                                          model=model, theme=theme, aspect_ratio=aspect_ratio)
                return rid
            finally:
                if is_temp:
                    os.unlink(img_path)
        elif cat == "t2v":
            duration = task.get("duration") or 6
            resolution = task.get("resolution") or "768P"
            path, rid = run_t2v_task(client, prompt, variant="scheduler",
                                      model=model, theme=theme, duration=duration, resolution=resolution)
            return rid
        elif cat == "i2v":
            img_path, is_temp = _resolve_image_path(task.get("image"))
            if not img_path:
                print("[SKIP] i2v missing image")
                return None
            duration = task.get("duration") or 6
            resolution = task.get("resolution") or "768P"
            try:
                path, rid = run_i2v_task(client, prompt, img_path, variant="scheduler",
                                          model=model, theme=theme, duration=duration, resolution=resolution)
                return rid
            finally:
                if is_temp:
                    os.unlink(img_path)
        elif cat == "fl2v":
            img1, is_temp1 = _resolve_image_path(task.get("image"))
            img2, is_temp2 = _resolve_image_path(task.get("image2"))
            if not img1 or not img2:
                print("[SKIP] fl2v missing frames")
                return None
            duration = task.get("duration") or 6
            resolution = task.get("resolution") or "768P"
            try:
                path, rid = run_fl2v_task(client, prompt, img1, img2, variant="scheduler",
                                           model=model, theme=theme, duration=duration, resolution=resolution)
                return rid
            finally:
                if is_temp1:
                    os.unlink(img1)
                if is_temp2:
                    os.unlink(img2)
        elif cat == "s2v":
            img_path, is_temp = _resolve_image_path(task.get("image"))
            if not img_path:
                print("[SKIP] s2v missing subject image")
                return None
            duration = task.get("duration") or 6
            resolution = task.get("resolution") or "768P"
            try:
                path, rid = run_s2v_task(client, prompt, img_path, variant="scheduler",
                                          model=model, theme=theme, duration=duration, resolution=resolution)
                return rid
            finally:
                if is_temp:
                    os.unlink(img_path)
        elif cat == "music":
            is_instrumental = bool(task.get("is_instrumental"))
            path, rid = run_music_task(client, prompt, variant="scheduler",
                                        model=model, theme=theme,
                                        is_instrumental=is_instrumental)
            return rid
        else:
            print(f"[SKIP] unsupported category: {cat}")
            return None
    except Exception as e:
        print(f"[ERROR] {cat} task failed: {e}")
        return None


def _update_task_status(session, task_id: int, status: str, run_id: str | None = None,
                        error_msg: str | None = None):
    from sqlalchemy import text
    params = {"sid": status, "tid": task_id}
    if run_id:
        params["rid"] = run_id
    if error_msg:
        params["err"] = error_msg
    set_clause = "status = :sid"
    if run_id:
        set_clause += ", run_id = :rid"
    if error_msg:
        set_clause += ", error_msg = :err"
    session.execute(text(f"UPDATE task_queue SET {set_clause} WHERE id = :tid"), params)
    session.commit()


def run_scheduler():
    print("=" * 60)
    print(f"  Video Daily Scheduler — {date.today()}")
    print("=" * 60)

    try:
        key = get_api_key()
        print(f"  API Key: {key[:8]}...")
    except ValueError as e:
        print(f"[ERROR] {e}")
        return

    ensure_dirs()
    init_db()
    use_mysql(True)

    session = get_mysql_session()
    today = date.today().isoformat()

    # 按 priority 升序（user=1 先，auto=10 后），取所有 pending 任务
    tasks = session.execute(
        __import__("sqlalchemy").text(
            "SELECT id, task_type, category, prompt_text, model, modality, image, image2, "
            "COALESCE(aspect_ratio, '16:9') as aspect_ratio, "
            "duration, resolution, is_instrumental "
            "FROM task_queue "
            "WHERE quota_date = :qd AND status = 'pending' "
            "ORDER BY priority ASC, created_at ASC"
        ),
        {"qd": today}
    ).fetchall()
    session.close()

    if not tasks:
        print("  [EMPTY] 今日无待执行任务")
        return

    print(f"\n  发现 {len(tasks)} 个待执行任务")

    client = MiniMaxClient()
    done_count = 0

    for task_row in tasks:
        task = dict(task_row._mapping)
        model = task["model"]

        # 检查额度
        remaining = _remaining(model)
        if remaining <= 0:
            print(f"  [QUOTA] {model} 额度已用尽，跳过 task_id={task['id']}")
            continue

        print(f"\n  [{task['task_type']}] {task['category']} - {model}")
        print(f"         {task['prompt_text'][:60]}...")

        run_id = _run_task(task, client)
        session = get_mysql_session()
        if run_id:
            _update_task_status(session, task["id"], "done", run_id=run_id)
            print(f"  [OK] done → run_id={run_id}")
        else:
            _update_task_status(session, task["id"], "failed",
                                error_msg="执行失败或被跳过")
            print(f"  [FAIL] task_id={task['id']}")
        session.close()
        done_count += 1

    print(f"\n{'=' * 60}")
    print(f"  调度完成，执行了 {done_count} 个任务")
    print("=" * 60)


if __name__ == "__main__":
    run_scheduler()
