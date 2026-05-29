"""
矩阵配置路由 /api/matrix
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database import get_db
from backend.schemas import MatrixConfigCreate, MatrixConfigResponse, MusicMatrixConfigCreate, MusicMatrixConfigResponse, MusicTrackResponse

router = APIRouter()


@router.get("/configs", response_model=list[MatrixConfigResponse])
def list_configs(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT id, name, subjects_text, styles_text, theme, notes, created_at, COALESCE(prompt_base, ''), category, COALESCE(reference_image, ''), COALESCE(rows_count, 6), COALESCE(cols_count, 6) FROM matrix_configs ORDER BY created_at DESC")).fetchall()
    return [
        MatrixConfigResponse(
            id=r[0], name=r[1], subjects_text=r[2], styles_text=r[3],
            theme=r[4] or "giant-tree", notes=r[5], created_at=r[6],
            prompt_base=r[7] if len(r) > 7 else "",
            category=r[8] if len(r) > 8 else "t2i",
            reference_image=r[9] if len(r) > 9 else None,
            rows_count=r[10] if len(r) > 10 else 6,
            cols_count=r[11] if len(r) > 11 else 6,
        )
        for r in rows
    ]


@router.post("/configs", response_model=MatrixConfigResponse)
def create_config(data: MatrixConfigCreate, db: Session = Depends(get_db)):
    prompt_base = getattr(data, "prompt_base", None) or ""
    category = getattr(data, "category", None) or "t2i"
    reference_image = getattr(data, "reference_image", None) or ""
    rows_count = getattr(data, "rows_count", None) or 6
    cols_count = getattr(data, "cols_count", None) or 6
    cur = db.execute(
        text(
            "INSERT INTO matrix_configs (name, subjects_text, styles_text, theme, notes, prompt_base, category, reference_image, rows_count, cols_count) "
            "VALUES (:name, :sub, :sty, :theme, :notes, :pb, :cat, :ref, :rc, :cc)"
        ),
        {"name": data.name, "sub": data.subjects_text, "sty": data.styles_text,
         "theme": data.theme, "notes": data.notes or "", "pb": prompt_base,
         "cat": category, "ref": reference_image, "rc": rows_count, "cc": cols_count},
    )
    db.commit()
    row = db.execute(
        text("SELECT id, name, subjects_text, styles_text, theme, notes, created_at, COALESCE(prompt_base, ''), category, COALESCE(reference_image, ''), COALESCE(rows_count, 6), COALESCE(cols_count, 6) FROM matrix_configs WHERE id = :id"),
        {"id": cur.lastrowid},
    ).fetchone()
    return MatrixConfigResponse(
        id=row[0], name=row[1], subjects_text=row[2], styles_text=row[3],
        theme=row[4] or "giant-tree", notes=row[5], created_at=row[6],
        prompt_base=row[7] if len(row) > 7 else "",
        category=row[8] if len(row) > 8 else "t2i",
        reference_image=row[9] if len(row) > 9 else None,
        rows_count=row[10] if len(row) > 10 else 6,
        cols_count=row[11] if len(row) > 11 else 6,
    )


@router.delete("/configs/{config_id}")
def delete_config(config_id: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM matrix_configs WHERE id = :id"), {"id": config_id})
    db.commit()
    return {"ok": True}


@router.get("/configs/{config_id}/assets")
def get_config_assets(config_id: int, db: Session = Depends(get_db)):
    """获取某个矩阵配置对应的所有生成的资产"""
    rows = db.execute(
        text("""
            SELECT a.id, a.run_id, a.file_path, a.modality, a.sub_type,
                   a.aspect_ratio, a.seed, a.created_at, a.external_url,
                   r.variant, r.category, r.model, r.status,
                   p.text as prompt_text
            FROM assets a
            JOIN runs r ON r.id = a.run_id
            LEFT JOIN prompts p ON p.id = a.prompt_id
            WHERE r.config_id = :cid
            ORDER BY a.created_at ASC
        """),
        {"cid": config_id},
    ).fetchall()
    return [
        {
            "id": r[0], "run_id": r[1], "file_path": r[2], "modality": r[3],
            "sub_type": r[4], "aspect_ratio": r[5], "seed": r[6],
            "created_at": r[7], "external_url": r[8],
            "variant": r[9], "category": r[10], "model": r[11], "status": r[12],
            "prompt_text": r[13] or "",
        }
        for r in rows
    ]


# ── Music Matrix ───────────────────────────────────────────────────────────────

@router.get("/music/configs", response_model=list[MusicMatrixConfigResponse])
def list_music_configs(db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT id, name, prompts_text, theme, notes, created_at FROM music_matrix_configs ORDER BY created_at DESC")
    ).fetchall()
    return [
        MusicMatrixConfigResponse(
            id=r[0], name=r[1], prompts_text=r[2],
            theme=r[3] or "game-bgm", notes=r[4], created_at=r[5],
        )
        for r in rows
    ]


@router.post("/music/generate")
def generate_music_matrix(data: MusicMatrixConfigCreate, db: Session = Depends(get_db)):
    """
    生成 6×6 音乐矩阵，36 个任务后台执行。
    返回配置 ID，前端通过 /music/configs/{id}/tracks 轮询状态。
    """
    if len(data.row_styles) != 6 or len(data.col_styles) != 6:
        raise HTTPException(status_code=400, detail="row_styles 和 col_styles 必须各 6 个")

    # 构建 36 个 prompt
    lines = []
    prompts = []
    for r in range(6):
        for c in range(6):
            full_prompt = f"{data.base_prompt}, {data.row_styles[r]}, {data.col_styles[c]}"
            lines.append(f"{r},{c}::{full_prompt}")
            prompts.append((r, c, full_prompt))

    prompts_text = "\n".join(lines)

    # 保存配置
    cur = db.execute(
        text(
            "INSERT INTO music_matrix_configs (name, prompts_text, theme, notes) "
            "VALUES (:name, :prompts, :theme, :notes)"
        ),
        {"name": data.name, "prompts": prompts_text, "theme": "game-bgm", "notes": data.notes or ""},
    )
    db.commit()
    config_id = cur.lastrowid

    # 启动后台生成
    from backend.task_runner import submit_music_matrix_async
    submit_music_matrix_async(config_id, prompts, data.base_prompt)

    return {"config_id": config_id, "total": 36, "message": "后台生成中，请通过 /music/configs/{id}/tracks 轮询状态"}


@router.get("/music/configs/{config_id}/tracks")
def get_music_config_tracks(config_id: int, db: Session = Depends(get_db)):
    """获取某个音乐矩阵配置下所有 track 的状态"""
    # 查配置
    cfg = db.execute(
        text("SELECT id, name, prompts_text, theme, notes, created_at FROM music_matrix_configs WHERE id = :id"),
        {"id": config_id},
    ).fetchone()
    if not cfg:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 解析 prompts_text
    tracks = []
    for line in cfg[2].strip().split("\n"):
        line = line.strip()
        if "::" not in line:
            continue
        idx_part, prompt = line.split("::", 1)
        try:
            r, c = idx_part.split(",")
            tracks.append({"row": int(r), "col": int(c), "prompt": prompt.strip()})
        except ValueError:
            continue

    # 查找已完成的 assets
    rows = db.execute(
        text("""
            SELECT a.file_path, r.variant, r.status, r.error_msg
            FROM assets a
            JOIN runs r ON r.id = a.run_id
            WHERE r.matrix_name = :name AND a.modality = 'music'
            ORDER BY a.created_at ASC
        """),
        {"name": f"music-matrix-{config_id}"},
    ).fetchall()

    # 建立 variant → asset 映射
    done_map = {}
    for r in rows:
        variant = r[1]  # r.variant = "r0c0", "r1c3" etc.
        if variant:
            done_map[variant] = {"file_path": r[0], "status": r[2], "error": r[3]}

    # 合并状态
    result = []
    for t in tracks:
        variant = f"r{t['row']}c{t['col']}"
        file_path = ""
        status = "pending"
        error = None
        if variant in done_map:
            file_path = done_map[variant]["file_path"]
            status = "done" if done_map[variant]["status"] == "success" else "failed"
            error = done_map[variant]["error"]
        result.append({
            "row": t["row"],
            "col": t["col"],
            "prompt": t["prompt"],
            "file_path": file_path,
            "status": status,
            "error": error,
        })

    return result


@router.delete("/music/configs/{config_id}")
def delete_music_config(config_id: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM music_matrix_configs WHERE id = :id"), {"id": config_id})
    db.commit()
    return {"ok": True}


@router.post("/music/retry/{config_id}")
def retry_music_matrix(config_id: int, db: Session = Depends(get_db)):
    """重新生成指定配置中失败/未完成的任务"""
    cfg = db.execute(
        text("SELECT id, name, prompts_text, theme FROM music_matrix_configs WHERE id = :id"),
        {"id": config_id},
    ).fetchone()
    if not cfg:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 解析 prompts，找出 pending/failed 的 track
    all_tracks = []
    for line in cfg[2].strip().split("\n"):
        line = line.strip()
        if "::" not in line:
            continue
        idx_part, prompt = line.split("::", 1)
        try:
            r, c = idx_part.split(",")
            all_tracks.append((int(r), int(c), prompt.strip()))
        except ValueError:
            continue

    # 查询已完成的任务
    done_rows = db.execute(
        text("SELECT r.variant FROM assets a JOIN runs r ON r.id = a.run_id WHERE r.matrix_name = :name AND a.modality = 'music' AND r.status = 'success'"),
        {"name": f"music-matrix-{config_id}"},
    ).fetchall()
    done_variants = {row[0] for row in done_rows}

    # 只保留未完成的
    pending = [(r, c, p) for (r, c, p) in all_tracks if f"r{r}c{c}" not in done_variants]

    if not pending:
        return {"ok": True, "message": "全部已完成"}

    # 启动后台重试
    from backend.task_runner import submit_music_matrix_async
    submit_music_matrix_async(config_id, pending, "")

    return {"ok": True, "pending": len(pending), "message": f"重启 {len(pending)} 个任务"}


@router.post("/music/sync/{config_id}")
def sync_music_matrix(config_id: int, db: Session = Depends(get_db)):
    """
    扫描磁盘上已有的音乐文件，同步到数据库。
    解决独立脚本生成后前端显示 pending 的问题。
    """
    import pathlib
    from datetime import datetime

    # 查配置
    cfg = db.execute(
        text("SELECT id, name, prompts_text, theme, notes, created_at FROM music_matrix_configs WHERE id = :id"),
        {"id": config_id},
    ).fetchone()
    if not cfg:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 解析 prompts_text 获取所有 track
    tracks = []
    for line in cfg[2].strip().split("\n"):
        line = line.strip()
        if "::" not in line:
            continue
        idx_part, prompt = line.split("::", 1)
        try:
            r, c = idx_part.split(",")
            tracks.append({"row": int(r), "col": int(c), "prompt": prompt.strip()})
        except ValueError:
            continue

    # 查找已有的 runs
    existing = {}
    result = db.execute(text("SELECT id, variant, status FROM runs WHERE matrix_name = :name"),
                        {"name": f"music-matrix-{config_id}"})
    for row in result:
        existing[row[1]] = {"id": row[0], "status": row[2]}

    # 查找已有的 assets
    existing_assets = set()
    result = db.execute(text("""
        SELECT r.variant FROM assets a JOIN runs r ON r.id = a.run_id
        WHERE r.matrix_name = :name AND a.modality = 'music'
    """), {"name": f"music-matrix-{config_id}"})
    for row in result:
        existing_assets.add(row[0])

    now = datetime.now()
    created_at = now.strftime("%Y-%m-%d %H:%M:%S")
    today = now.strftime("%Y-%m-%d")
    theme = cfg[3] or "game-bgm"

    # 可能的文件路径模式
    proj_root = pathlib.Path(__file__).parent.parent.parent
    synced = []
    skipped = []
    errors = []

    for t in tracks:
        variant = f"r{t['row']}c{t['col']}"
        run_id = f"{today}__{theme}__music__{variant}__v001"

        # 检查多种可能的文件路径
        possible_paths = [
            proj_root / "works" / "music" / today / f"matrix-music-matrix-{config_id}" / f"{variant}.mp3",
            proj_root / "works" / "music" / today / f"{run_id}.mp3",
        ]

        file_path = None
        for p in possible_paths:
            if p.exists() and p.stat().st_size > 0:
                file_path = p
                break

        if not file_path:
            skipped.append(variant)
            continue

        # 计算相对路径
        rel_path = str(file_path.relative_to(proj_root)).replace("\\", "/")

        try:
            if variant in existing:
                # 更新现有 run
                if existing[variant]["status"] != "success":
                    db.execute(text("UPDATE runs SET status = 'success', error_msg = NULL WHERE id = :rid"),
                               {"rid": existing[variant]["id"]})

                # 检查 asset 是否存在
                if variant not in existing_assets:
                    db.execute(text("""
                        INSERT INTO assets (run_id, file_path, modality, created_at)
                        VALUES (:run_id, :file_path, 'music', :created_at)
                    """), {"run_id": existing[variant]["id"], "file_path": rel_path, "created_at": created_at})
            else:
                # 创建新 run
                db.execute(text("""
                    INSERT INTO runs (id, theme, category, model, variant, status, is_favorite,
                                      created_at, quota_date, matrix_name, config_id)
                    VALUES (:run_id, :theme, 'music', 'music-2.6', :variant, 'success', 0,
                            :created_at, :quota_date, :matrix_name, :config_id)
                """), {
                    "run_id": run_id, "theme": theme, "variant": variant,
                    "created_at": created_at, "quota_date": today,
                    "matrix_name": f"music-matrix-{config_id}", "config_id": config_id
                })

                # 创建 asset
                db.execute(text("""
                    INSERT INTO assets (run_id, file_path, modality, created_at)
                    VALUES (:run_id, :file_path, 'music', :created_at)
                """), {"run_id": run_id, "file_path": rel_path, "created_at": created_at})

            synced.append(variant)
        except Exception as e:
            errors.append({"variant": variant, "error": str(e)})

    db.commit()

    return {
        "ok": True,
        "synced": len(synced),
        "skipped": len(skipped),
        "errors": len(errors),
        "details": {
            "synced": synced,
            "skipped": skipped,
            "errors": errors,
        }
    }
