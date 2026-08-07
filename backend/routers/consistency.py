"""
一致性测试路由 /api/consistency
"""

import threading
from datetime import datetime, date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database import get_db

router = APIRouter()

PROJECT_ROOT = Path(__file__).parent.parent.parent


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("/tests")
def list_tests(db: Session = Depends(get_db)):
    """列出所有一致性测试"""
    rows = db.execute(text(
        "SELECT id, name, status, notes, created_at FROM consistency_tests ORDER BY created_at DESC"
    )).fetchall()
    return [{"id": r[0], "name": r[1], "status": r[2], "notes": r[3], "created_at": r[4]} for r in rows]


@router.post("/tests")
def create_test(data: dict, db: Session = Depends(get_db)):
    """创建一致性测试"""
    name = data.get("name", f"一致性测试-{datetime.now().strftime('%m-%d %H:%M')}")
    notes = data.get("notes", "")
    characters = data.get("characters", [])  # [{"name": "角色A", "prompt": "..."}]
    variation_types = data.get("variation_types", ["表情", "动作", "装备"])  # 变体类型列表
    # style_prefix: 风格+构图前缀，会自动加到每个 variation prompt 前面
    # 例如 "pixel art style, 16-bit retro game character, full body shot"
    # 这样变体只描述变化部分，但风格和构图保持一致
    style_prefix = data.get("style_prefix", "")

    if not characters:
        raise HTTPException(status_code=400, detail="至少需要一个角色")
    if not variation_types:
        raise HTTPException(status_code=400, detail="至少需要一个变体类型")

    # 创建测试
    cur = db.execute(text(
        "INSERT INTO consistency_tests (name, status, notes) VALUES (:name, 'draft', :notes)"
    ), {"name": name, "notes": notes})
    test_id = cur.lastrowid

    # 创建角色
    for i, char in enumerate(characters):
        cur = db.execute(text(
            "INSERT INTO consistency_characters (test_id, name, base_prompt, order_index) "
            "VALUES (:test_id, :name, :prompt, :idx)"
        ), {"test_id": test_id, "name": char["name"], "prompt": char["prompt"], "idx": i})
        char_id = cur.lastrowid

        # 为每个角色创建变体占位
        for j, vtype in enumerate(variation_types):
            # 变体 prompt = 风格前缀 + 变化描述
            # 不包含角色外貌，让 subject_reference 承担一致性
            vprompt = f"{style_prefix}, {vtype}" if style_prefix else vtype
            db.execute(text(
                "INSERT INTO consistency_variations (character_id, variation_type, variation_prompt, order_index) "
                "VALUES (:char_id, :vtype, :vprompt, :idx)"
            ), {"char_id": char_id, "vtype": vtype, "vprompt": vprompt, "idx": j})

    db.commit()
    return {"id": test_id, "message": f"创建成功，{len(characters)} 角色 × {len(variation_types)} 变体"}


@router.get("/tests/{test_id}")
def get_test(test_id: int, db: Session = Depends(get_db)):
    """获取测试详情（含所有角色和变体）"""
    test = db.execute(text(
        "SELECT id, name, status, notes, created_at FROM consistency_tests WHERE id = :id"
    ), {"id": test_id}).fetchone()
    if not test:
        raise HTTPException(status_code=404, detail="测试不存在")

    # 获取角色
    chars = db.execute(text(
        "SELECT id, name, base_prompt, base_image, order_index FROM consistency_characters "
        "WHERE test_id = :test_id ORDER BY order_index"
    ), {"test_id": test_id}).fetchall()

    characters = []
    for c in chars:
        # 获取变体
        vars_ = db.execute(text(
            "SELECT id, variation_type, variation_prompt, image_path, score, user_notes, order_index "
            "FROM consistency_variations WHERE character_id = :char_id ORDER BY order_index"
        ), {"char_id": c[0]}).fetchall()

        variations = [{
            "id": v[0], "type": v[1], "prompt": v[2], "image": v[3],
            "score": v[4], "notes": v[5], "order": v[6]
        } for v in vars_]

        characters.append({
            "id": c[0], "name": c[1], "prompt": c[2],
            "base_image": c[3], "order": c[4],
            "variations": variations,
        })

    return {
        "id": test[0], "name": test[1], "status": test[2],
        "notes": test[3], "created_at": test[4],
        "characters": characters,
    }


@router.delete("/tests/{test_id}")
def delete_test(test_id: int, db: Session = Depends(get_db)):
    """删除测试"""
    db.execute(text("DELETE FROM consistency_tests WHERE id = :id"), {"id": test_id})
    db.commit()
    return {"ok": True}


# ── 生成 ──────────────────────────────────────────────────────────────────────

@router.post("/tests/{test_id}/generate-base")
def generate_base_images(test_id: int, db: Session = Depends(get_db)):
    """生成角色基础图（后台执行）"""
    test = db.execute(text(
        "SELECT id, status FROM consistency_tests WHERE id = :id"
    ), {"id": test_id}).fetchone()
    if not test:
        raise HTTPException(status_code=404, detail="测试不存在")

    chars = db.execute(text(
        "SELECT id, name, base_prompt FROM consistency_characters WHERE test_id = :test_id ORDER BY order_index"
    ), {"test_id": test_id}).fetchall()

    if not chars:
        raise HTTPException(status_code=400, detail="没有角色")

    # 更新状态
    db.execute(text("UPDATE consistency_tests SET status = 'generating_base' WHERE id = :id"), {"id": test_id})
    db.commit()

    # 后台生成
    def _generate():
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        from tools.client import MiniMaxClient
        from backend.database import SessionLocal as SL

        client = MiniMaxClient()
        session = SL()

        today = date.today().isoformat()
        out_dir = PROJECT_ROOT / "works" / "t2i" / today
        out_dir.mkdir(parents=True, exist_ok=True)

        for char in chars:
            char_id, name, prompt = char[0], char[1], char[2]
            try:
                result = client.create_image_task(
                    model="image-01",
                    prompt=prompt,
                    aspect_ratio="1:1",
                    n=1,
                )
                urls = result.get("data", {}).get("image_urls", [])
                if urls:
                    # 下载图片
                    import requests as req
                    resp = req.get(urls[0], timeout=60)
                    if resp.status_code == 200:
                        filename = f"consistency-base-{char_id}.png"
                        filepath = out_dir / filename
                        filepath.write_bytes(resp.content)
                        print(f"[BASE] {name} → {filepath} ({len(resp.content)} bytes)")
                    else:
                        print(f"[BASE] {name} DOWNLOAD FAILED: HTTP {resp.status_code}")
                        continue

                    rel_path = str(filepath.relative_to(PROJECT_ROOT)).replace("\\", "/")
                    session.execute(text(
                        "UPDATE consistency_characters SET base_image = :img WHERE id = :id"
                    ), {"img": rel_path, "id": char_id})
                    session.commit()
                else:
                    print(f"[BASE] {name} FAILED: no image_urls in response")
            except Exception as e:
                print(f"[BASE] {name} FAILED: {e}")

        session.execute(text(
            "UPDATE consistency_tests SET status = 'base_done' WHERE id = :id"
        ), {"id": test_id})
        session.commit()
        session.close()

    threading.Thread(target=_generate, daemon=True).start()
    return {"message": f"开始生成 {len(chars)} 个角色基础图"}


@router.post("/tests/{test_id}/generate-variations")
def generate_variations(test_id: int, db: Session = Depends(get_db)):
    """生成变体图（使用 subject_reference 保持一致性）"""
    test = db.execute(text(
        "SELECT id, status FROM consistency_tests WHERE id = :id"
    ), {"id": test_id}).fetchone()
    if not test:
        raise HTTPException(status_code=404, detail="测试不存在")

    # 检查基础图是否完成
    chars = db.execute(text(
        "SELECT id, name, base_prompt, base_image FROM consistency_characters "
        "WHERE test_id = :test_id AND base_image IS NOT NULL ORDER BY order_index"
    ), {"test_id": test_id}).fetchall()

    if not chars:
        raise HTTPException(status_code=400, detail="请先生成基础图")

    # 获取所有变体
    all_vars = []
    for char in chars:
        vars_ = db.execute(text(
            "SELECT id, variation_type, variation_prompt FROM consistency_variations "
            "WHERE character_id = :char_id AND image_path IS NULL ORDER BY order_index"
        ), {"char_id": char[0]}).fetchall()
        for v in vars_:
            all_vars.append((char[0], char[1], char[3], v[0], v[1], v[2]))

    if not all_vars:
        return {"message": "所有变体已生成"}

    # 更新状态
    db.execute(text("UPDATE consistency_tests SET status = 'generating_variations' WHERE id = :id"), {"id": test_id})
    db.commit()

    # 后台生成
    def _generate():
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        from tools.client import MiniMaxClient
        from backend.database import SessionLocal as SL
        import requests as req

        client = MiniMaxClient()
        session = SL()

        today = date.today().isoformat()
        out_dir = PROJECT_ROOT / "works" / "i2i" / today
        out_dir.mkdir(parents=True, exist_ok=True)

        for char_id, char_name, base_image, var_id, var_type, var_prompt in all_vars:
            try:
                # 使用 base64 编码参考图（API 不支持需要认证的 URL）
                import base64
                if base_image and not base_image.startswith("http"):
                    img_path = PROJECT_ROOT / base_image
                    if img_path.exists():
                        with open(img_path, "rb") as f:
                            img_b64 = base64.b64encode(f.read()).decode()
                        ref_data = f"data:image/png;base64,{img_b64}"
                    else:
                        print(f"[VAR] {char_name} × {var_type} SKIP: base image not found at {img_path}")
                        continue
                else:
                    ref_data = base_image

                result = client.create_image_task(
                    model="image-01",
                    prompt=var_prompt,
                    aspect_ratio="1:1",
                    n=1,
                    subject_reference=[{"type": "character", "image_file": ref_data}],
                )
                urls = result.get("data", {}).get("image_urls", [])
                if urls:
                    resp = req.get(urls[0], timeout=60)
                    if resp.status_code == 200:
                        filename = f"consistency-var-{var_id}.png"
                        filepath = out_dir / filename
                        filepath.write_bytes(resp.content)
                        print(f"[VAR] {char_name} × {var_type} → {filepath} ({len(resp.content)} bytes)")
                    else:
                        print(f"[VAR] {char_name} × {var_type} DOWNLOAD FAILED: HTTP {resp.status_code}")
                        continue
                else:
                    print(f"[VAR] {char_name} × {var_type} FAILED: no image_urls in response")
                    continue

                rel_path = str(filepath.relative_to(PROJECT_ROOT)).replace("\\", "/")
                session.execute(text(
                    "UPDATE consistency_variations SET image_path = :img WHERE id = :id"
                ), {"img": rel_path, "id": var_id})
                session.commit()
            except Exception as e:
                print(f"[VAR] {char_name} × {var_type} FAILED: {e}")

        session.execute(text(
            "UPDATE consistency_tests SET status = 'variations_done' WHERE id = :id"
        ), {"id": test_id})
        session.commit()
        session.close()

    threading.Thread(target=_generate, daemon=True).start()
    return {"message": f"开始生成 {len(all_vars)} 个变体图"}


# ── 评分 ──────────────────────────────────────────────────────────────────────

@router.put("/variations/{variation_id}/score")
def update_score(variation_id: int, data: dict, db: Session = Depends(get_db)):
    """更新变体评分"""
    score = data.get("score")
    notes = data.get("notes", "")

    if score is not None and (score < 1 or score > 5):
        raise HTTPException(status_code=400, detail="评分范围 1-5")

    db.execute(text(
        "UPDATE consistency_variations SET score = :score, user_notes = :notes WHERE id = :id"
    ), {"score": score, "notes": notes, "id": variation_id})
    db.commit()
    return {"ok": True}


# ── 汇总 ──────────────────────────────────────────────────────────────────────

@router.get("/tests/{test_id}/summary")
def get_summary(test_id: int, db: Session = Depends(get_db)):
    """获取测试评分汇总"""
    chars = db.execute(text(
        "SELECT id, name FROM consistency_characters WHERE test_id = :test_id ORDER BY order_index"
    ), {"test_id": test_id}).fetchall()

    result = []
    for c in chars:
        stats = db.execute(text(
            "SELECT variation_type, AVG(score), COUNT(score), MIN(score), MAX(score) "
            "FROM consistency_variations WHERE character_id = :char_id AND score IS NOT NULL "
            "GROUP BY variation_type"
        ), {"char_id": c[0]}).fetchall()

        variations = [{
            "type": s[0], "avg_score": round(float(s[1]), 1),
            "count": s[2], "min": s[3], "max": s[4]
        } for s in stats]

        result.append({"id": c[0], "name": c[1], "variations": variations})

    return {"characters": result}
