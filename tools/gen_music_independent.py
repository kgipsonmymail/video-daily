#!/usr/bin/env python3.11
"""
独立音乐矩阵生成脚本（带自动数据库同步）

用途：绕过后端线程池并发锁问题，直接调 MiniMax API 生成音乐。
生成完成后自动同步到数据库，前端可直接查看。

用法：
  python3.11 tools/gen_music_independent.py <config_id> [--workers 2] [--dry-run]

示例：
  python3.11 tools/gen_music_independent.py 2
  python3.11 tools/gen_music_independent.py 2 --workers 3
  python3.11 tools/gen_music_independent.py 2 --dry-run  # 只检查缺失的 tracks
"""

import argparse
import concurrent.futures
import pathlib
import sys
import time
import requests
from datetime import date

PROJECT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT))

from backend.config import get_settings

settings = get_settings()
API_KEY = settings.minimax_api_key

# MiniMax API 配置
API_URL = "https://api.minimaxi.com/v1/music_generation"
TIMEOUT = 180  # 音乐生成慢，必须 180 秒


def get_config_from_db(config_id: int) -> dict:
    """从数据库读取音乐矩阵配置"""
    from backend.database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        cfg = db.execute(
            text("SELECT id, name, prompts_text, theme, notes FROM music_matrix_configs WHERE id = :id"),
            {"id": config_id},
        ).fetchone()
        if not cfg:
            raise ValueError(f"Config ID {config_id} not found")

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

        return {
            "id": cfg[0],
            "name": cfg[1],
            "theme": cfg[3] or "game-bgm",
            "tracks": tracks,
        }
    finally:
        db.close()


def get_existing_variants(config_id: int) -> set:
    """查询数据库中已完成的 variants"""
    from backend.database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT r.variant FROM runs r
                WHERE r.matrix_name = :name AND r.status = 'success'
            """),
            {"name": f"music-matrix-{config_id}"},
        ).fetchall()
        return {row[0] for row in rows}
    finally:
        db.close()


def gen_track(row: int, col: int, prompt: str, out_dir: pathlib.Path, variant: str) -> dict:
    """生成单首音乐，返回结果 dict"""
    try:
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "music-2.6",
                "prompt": prompt,
                "is_instrumental": True,
                "output_format": "hex",
                "lyrics_optimizer": False,
                "aigc_watermark": False,
            },
            timeout=TIMEOUT,
        )
        data = resp.json()
        bc = data.get("base_resp", {})
        if bc.get("status_code") != 0:
            return {"variant": variant, "ok": False, "error": f"API error: {bc.get('status_msg', '')}"}

        hex_audio = data.get("data", {}).get("audio", "")
        if not hex_audio:
            return {"variant": variant, "ok": False, "error": "No audio returned"}

        # 保存文件
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{variant}.mp3"
        out_path.write_bytes(bytes.fromhex(hex_audio))

        return {"variant": variant, "ok": True, "path": str(out_path)}
    except Exception as e:
        return {"variant": variant, "ok": False, "error": str(e)[:200]}


def sync_to_db(config_id: int, config: dict, generated: dict):
    """将生成的文件同步到数据库"""
    from backend.database import SessionLocal
    from sqlalchemy import text
    from datetime import datetime

    db = SessionLocal()
    try:
        now = datetime.now()
        created_at = now.strftime("%Y-%m-%d %H:%M:%S")
        today = now.strftime("%Y-%m-%d")
        theme = config["theme"]

        # 查找已有的 runs
        existing = {}
        rows = db.execute(
            text("SELECT id, variant, status FROM runs WHERE matrix_name = :name"),
            {"name": f"music-matrix-{config_id}"},
        )
        for row in rows:
            existing[row[1]] = {"id": row[0], "status": row[2]}

        # 查找已有的 assets
        existing_assets = set()
        rows = db.execute(
            text("""
                SELECT r.variant FROM assets a JOIN runs r ON r.id = a.run_id
                WHERE r.matrix_name = :name AND a.modality = 'music'
            """),
            {"name": f"music-matrix-{config_id}"},
        )
        for row in rows:
            existing_assets.add(row[0])

        synced = 0
        for variant, info in generated.items():
            if not info["ok"]:
                continue

            run_id = f"{today}__{theme}__music__{variant}__v001"
            file_path = str(pathlib.Path(info["path"]).relative_to(PROJECT)).replace("\\", "/")

            if variant in existing:
                if existing[variant]["status"] != "success":
                    db.execute(
                        text("UPDATE runs SET status = 'success', error_msg = NULL WHERE id = :rid"),
                        {"rid": existing[variant]["id"]},
                    )
                if variant not in existing_assets:
                    db.execute(
                        text("INSERT INTO assets (run_id, file_path, modality, created_at) VALUES (:rid, :fp, 'music', :ca)"),
                        {"rid": existing[variant]["id"], "fp": file_path, "ca": created_at},
                    )
            else:
                db.execute(
                    text("""
                        INSERT INTO runs (id, theme, category, model, variant, status, is_favorite,
                                          created_at, quota_date, matrix_name, config_id)
                        VALUES (:rid, :theme, 'music', 'music-2.6', :variant, 'success', 0,
                                :ca, :qd, :mn, :cid)
                    """),
                    {
                        "rid": run_id, "theme": theme, "variant": variant,
                        "ca": created_at, "qd": today,
                        "mn": f"music-matrix-{config_id}", "cid": config_id,
                    },
                )
                db.execute(
                    text("INSERT INTO assets (run_id, file_path, modality, created_at) VALUES (:rid, :fp, 'music', :ca)"),
                    {"rid": run_id, "fp": file_path, "ca": created_at},
                )
            synced += 1

        db.commit()
        print(f"\n✓ Synced {synced} tracks to database")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="独立音乐矩阵生成脚本")
    parser.add_argument("config_id", type=int, help="音乐矩阵配置 ID")
    parser.add_argument("--workers", type=int, default=2, help="并发 worker 数 (default: 2)")
    parser.add_argument("--dry-run", action="store_true", help="只检查缺失的 tracks，不生成")
    parser.add_argument("--no-sync", action="store_true", help="不同步到数据库")
    args = parser.parse_args()

    # 读取配置
    print(f"Loading config ID {args.config_id}...")
    config = get_config_from_db(args.config_id)
    print(f"Name: {config['name']}, Theme: {config['theme']}, Tracks: {len(config['tracks'])}")

    # 检查已完成的
    existing = get_existing_variants(args.config_id)
    print(f"Already completed in DB: {len(existing)}")

    # 筛选需要生成的
    pending = []
    for t in config["tracks"]:
        variant = f"r{t['row']}c{t['col']}"
        if variant not in existing:
            pending.append(t)

    if not pending:
        print("All tracks already completed!")
        return

    print(f"Pending: {len(pending)} tracks")

    if args.dry_run:
        for t in pending:
            print(f"  - r{t['row']}c{t['col']}")
        return

    # 准备输出目录
    today = date.today().isoformat()
    out_dir = PROJECT / "works" / "music" / today / f"matrix-music-matrix-{args.config_id}"

    # 生成
    print(f"\nStarting generation with {args.workers} workers...")
    start = time.time()
    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}
        for t in pending:
            variant = f"r{t['row']}c{t['col']}"
            f = executor.submit(gen_track, t["row"], t["col"], t["prompt"], out_dir, variant)
            futures[f] = variant

        done_count = 0
        for f in concurrent.futures.as_completed(futures):
            result = f.result()
            done_count += 1
            variant = result["variant"]
            results[variant] = result
            status = "✓" if result["ok"] else "✗"
            msg = result.get("path", result.get("error", ""))
            print(f"[{done_count}/{len(pending)}] {status} {variant}: {msg}", flush=True)

    elapsed = time.time() - start
    success = sum(1 for r in results.values() if r["ok"])
    failed = sum(1 for r in results.values() if not r["ok"])
    print(f"\nDone in {elapsed:.0f}s | Success: {success} | Failed: {failed}")

    # 同步到数据库
    if not args.no_sync and success > 0:
        sync_to_db(args.config_id, config, results)

    # 显示失败的
    if failed > 0:
        print("\nFailed tracks:")
        for v, r in results.items():
            if not r["ok"]:
                print(f"  ✗ {v}: {r['error']}")


if __name__ == "__main__":
    main()
