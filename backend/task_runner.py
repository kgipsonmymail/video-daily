"""
后台任务执行器 — 负责立即执行用户提交的任务
使用线程在后台运行，不阻塞 API 响应
"""

import threading
from datetime import date
from tools.client import MiniMaxClient
from tools.db import get_mysql_session, use_mysql
from tools.image_tasks import run_t2i_task, run_i2i_task
from tools.video_tasks import run_t2v_task, run_i2v_task
from tools.music_tasks import run_music_task
import base64, tempfile, os, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _resolve_image_path(image_val: str | None) -> tuple[str | None, bool]:
    """将文件路径或 base64 字符串转为文件路径。Returns (path, is_temp)."""
    if not image_val:
        return None, False
    if image_val.startswith("data:"):
        import base64, tempfile
        header, data = image_val.split(",", 1)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(base64.b64decode(data))
            return f.name, True
    proj_root = Path(__file__).parent.parent
    full_path = proj_root / image_val
    if full_path.exists():
        return str(full_path), False
    print(f"[WARN] Image file not found: {full_path}")
    return None, False


def _category_modality(category: str) -> str:
    if category in ("t2i", "i2i"):
        return "image"
    if category in ("t2v", "i2v", "fl2v", "s2v"):
        return "video"
    if category == "music":
        return "music"
    return "image"


def _run_task(task: dict) -> str | None:
    """执行单个任务，返回 run_id 或 None。"""
    cat = task["category"]
    prompt = task["prompt_text"]
    model = task["model"]
    theme = task.get("theme", "giant-tree")

    client = MiniMaxClient()
    try:
        if cat == "t2i":
            paths, rid = run_t2i_task(client, prompt, variant="user-submit", model=model,
                                      theme=theme, n=1, aspect_ratio="16:9")
            return rid
        elif cat == "i2i":
            img_path, is_temp = _resolve_image_path(task.get("image"))
            if not img_path:
                print("[SKIP] i2i missing image")
                return None
            try:
                paths, rid = run_i2i_task(client, prompt, img_path, variant="user-submit",
                                          model=model, theme=theme)
                return rid
            finally:
                if is_temp:
                    os.unlink(img_path)
        elif cat == "t2v":
            path, rid = run_t2v_task(client, prompt, variant="user-submit",
                                      model=model, theme=theme, duration=6, resolution="768P")
            return rid
        elif cat == "i2v":
            img_path, is_temp = _resolve_image_path(task.get("image"))
            if not img_path:
                print("[SKIP] i2v missing image")
                return None
            try:
                path, rid = run_i2v_task(client, prompt, img_path, variant="user-submit",
                                          model=model, theme=theme, duration=6, resolution="768P")
                return rid
            finally:
                if is_temp:
                    os.unlink(img_path)
        elif cat == "music":
            path, rid = run_music_task(client, prompt, variant="user-submit",
                                        model=model, theme=theme, is_instrumental=False)
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


def _check_quota(model: str) -> bool:
    """检查模型今日是否有剩余额度"""
    from tools.db import get_quota_status
    today = date.today().isoformat()
    session = get_mysql_session()
    quotas = get_quota_status(session, today)
    session.close()
    for q in quotas:
        if model in (q.model, q.bucket_name):
            return q.used < q.daily_limit
    # 未记录过额度的模型默认允许
    return True


def run_task_async(task_id: int, task_data: dict):
    """后台线程执行的函数"""
    use_mysql(True)
    model = task_data["model"]

    # 再次检查额度（可能创建后额度被其他任务消耗）
    if not _check_quota(model):
        print(f"[QUOTA] Task {task_id}: {model} quota exhausted, skipping")
        session = get_mysql_session()
        _update_task_status(session, task_id, "failed", error_msg="额度已用尽")
        session.close()
        return

    print(f"[BG] Task {task_id} starting: {task_data['category']} - {model}")
    run_id = _run_task(task_data)

    session = get_mysql_session()
    if run_id:
        _update_task_status(session, task_id, "done", run_id=run_id)
        print(f"[BG] Task {task_id} done → run_id={run_id}")
    else:
        _update_task_status(session, task_id, "failed", error_msg="执行失败")
        print(f"[BG] Task {task_id} failed")
    session.close()


def submit_task_async(task_id: int, task_data: dict):
    """提交任务到后台线程池执行"""
    t = threading.Thread(target=run_task_async, args=(task_id, task_data), daemon=True)
    t.start()
    return t


# ── Music Matrix ───────────────────────────────────────────────────────────────

def _run_single_music_track(args) -> dict:
    """执行单个音乐 track，返回 (row, col, run_id, file_path, error)"""
    row, col, prompt, variant, model, theme, config_id = args
    use_mysql(True)

    from tools.client import MiniMaxClient
    from tools.db import get_mysql_session, upsert_prompt, create_run, create_asset
    from tools.config import get_quota_bucket, log_quota_usage, assets_dir, today_str
    from tools.music_tasks import _hex_to_file
    import base64, pathlib

    client = MiniMaxClient()
    session = get_mysql_session()
    today = today_str()
    run_id = f"{today}__game-bgm__music__{variant}__v001"

    try:
        # 检查额度
        bucket_name, limit = get_quota_bucket(model)
        from tools.db import get_or_create_quota
        quota = get_or_create_quota(session, today, model, bucket_name, limit)
        if quota.used >= quota.daily_limit:
            raise RuntimeError(f"额度耗尽: {bucket_name}")

        # upsert prompt
        prompt_row = upsert_prompt(session, prompt, theme=theme)

        # 创建 run
        create_run(session, run_id=run_id, category="music", model=model,
                   variant=variant, theme=theme, status="running",
                   matrix_name=f"music-matrix-{config_id}")

        # 扣额度
        quota.used += 1
        log_quota_usage(quota_date=today, model=model, bucket_name=bucket_name,
                        n_used=1, source="backend", run_id=run_id, category="music")

        # 调用 API（最多重试 3 次，2151 是服务端临时故障）
        result = None
        last_err = None
        for attempt in range(3):
            try:
                result = client.create_music_task(
                    model=model, prompt=prompt, is_instrumental=True,
                    output_format="hex", lyrics_optimizer=False,
                )
                data = result.get("data", {})
                status = data.get("status")
                bc = result.get("base_resp", {}).get("status_code", 0)
                if bc != 0:
                    # 2151 = 服务端准备失败，可重试
                    if bc == 2151 and attempt < 2:
                        import time; time.sleep(5)
                        continue
                    raise Exception(f"API error: {result}")
                if status == 2:
                    break
                if status == 1 and attempt < 2:
                    import time; time.sleep(5)
                    continue
                raise Exception(f"Unexpected status={status}")
            except Exception as e:
                last_err = e
                if attempt < 2:
                    import time; time.sleep(5)
                    continue
                raise last_err
        data = result.get("data", {})

        hex_audio = data.get("audio", "")
        if not hex_audio:
            raise Exception("No audio in response")

        # 保存文件
        out_dir = pathlib.Path(assets_dir(today)) / "music"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{run_id}.mp3"
        _hex_to_file(hex_audio, out_path)

        # 更新 run
        session.execute(
            __import__("sqlalchemy").text(
                "UPDATE runs SET status = 'success' WHERE id = :rid"
            ),
            {"rid": run_id},
        )

        # 写入 asset
        proj_root = pathlib.Path(__file__).parent.parent
        rel = str(out_path.relative_to(proj_root)).replace("\\", "/")
        create_asset(session, run_id=run_id, file_path=rel,
                     modality="music", sub_type="song", prompt_id=prompt_row.id)

        session.commit()
        print(f"[MUSIC] r{row}c{col} → {out_path}")
        return {"row": row, "col": col, "run_id": run_id, "file_path": rel, "error": None}

    except Exception as exc:
        session.rollback()
        try:
            session.execute(
                __import__("sqlalchemy").text(
                    "UPDATE runs SET status = 'failed', error_msg = :e WHERE id = :rid"
                ),
                {"e": str(exc), "rid": run_id},
            )
            session.commit()
        except Exception:
            session.rollback()
        print(f"[MUSIC] r{row}c{col} FAILED: {exc}")
        return {"row": row, "col": col, "run_id": run_id, "file_path": "", "error": str(exc)}
    finally:
        session.close()


def submit_music_matrix_async(config_id: int, prompts: list, base_prompt: str):
    """后台线程执行 36 个音乐生成任务"""
    _config_id = config_id  # capture for closure
    def _run():
        import concurrent.futures
        from tools.client import MiniMaxClient
        from tools.db import use_mysql
        use_mysql(True)

        model = "music-2.6"
        theme = "game-bgm"

        tasks = []
        for (r, c, prompt) in prompts:
            variant = f"r{r}c{c}"
            tasks.append((r, c, prompt, variant, model, theme, _config_id))

        # 并发执行（最多 4 个同时）
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(_run_single_music_track, t): t for t in tasks}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                print(f"[MUSIC] r{result['row']}c{result['col']} done")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t