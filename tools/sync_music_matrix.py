#!/usr/bin/env python3.11
"""
音乐矩阵同步工具

将磁盘上已有的音乐文件同步到数据库。
解决独立脚本生成后前端显示 pending 的问题。

用法：
  python3.11 tools/sync_music_matrix.py <config_id>
  python3.11 tools/sync_music_matrix.py <config_id> --check  # 只检查，不修改
"""

import argparse
import pathlib
import sys
from datetime import datetime

PROJECT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT))


def main():
    parser = argparse.ArgumentParser(description="音乐矩阵数据库同步工具")
    parser.add_argument("config_id", type=int, help="音乐矩阵配置 ID")
    parser.add_argument("--check", action="store_true", help="只检查不修改")
    args = parser.parse_args()

    from backend.database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        # 查配置
        cfg = db.execute(
            text("SELECT id, name, prompts_text, theme FROM music_matrix_configs WHERE id = :id"),
            {"id": args.config_id},
        ).fetchone()
        if not cfg:
            print(f"Config ID {args.config_id} not found!")
            sys.exit(1)

        print(f"Config: {cfg[1]} (theme: {cfg[3]})")

        # 解析 tracks
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

        print(f"Total tracks: {len(tracks)}")

        # 查找已有 records
        existing_runs = {}
        rows = db.execute(
            text("SELECT id, variant, status FROM runs WHERE matrix_name = :name"),
            {"name": f"music-matrix-{args.config_id}"},
        )
        for row in rows:
            existing_runs[row[1]] = {"id": row[0], "status": row[2]}

        existing_assets = set()
        rows = db.execute(
            text("""
                SELECT r.variant FROM assets a JOIN runs r ON r.id = a.run_id
                WHERE r.matrix_name = :name AND a.modality = 'music'
            """),
            {"name": f"music-matrix-{args.config_id}"},
        )
        for row in rows:
            existing_assets.add(row[0])

        print(f"Existing runs: {len(existing_runs)}, assets: {len(existing_assets)}")

        # 检查磁盘文件
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        theme = cfg[3] or "game-bgm"
        proj_root = PROJECT

        disk_files = {}
        for t in tracks:
            variant = f"r{t['row']}c{t['col']}"
            possible_paths = [
                proj_root / "works" / "music" / today / f"matrix-music-matrix-{args.config_id}" / f"{variant}.mp3",
                proj_root / "works" / "music" / today / f"{today}__{theme}__music__{variant}__v001.mp3",
            ]
            for p in possible_paths:
                if p.exists() and p.stat().st_size > 0:
                    disk_files[variant] = p
                    break

        print(f"Files on disk: {len(disk_files)}")

        # 分析状态
        needs_sync = []
        already_ok = []
        missing = []

        for t in tracks:
            variant = f"r{t['row']}c{t['col']}"
            has_run = variant in existing_runs and existing_runs[variant]["status"] == "success"
            has_asset = variant in existing_assets
            has_file = variant in disk_files

            if has_run and has_asset:
                already_ok.append(variant)
            elif has_file:
                needs_sync.append(variant)
            else:
                missing.append(variant)

        print(f"\nStatus:")
        print(f"  ✓ Already synced: {len(already_ok)}")
        print(f"  ⚠ Need sync: {len(needs_sync)}")
        print(f"  ✗ Missing files: {len(missing)}")

        if missing:
            print(f"\nMissing tracks: {', '.join(missing)}")

        if args.check or not needs_sync:
            if needs_sync:
                print(f"\nRun without --check to sync {len(needs_sync)} tracks")
            return

        # 执行同步
        created_at = now.strftime("%Y-%m-%d %H:%M:%S")
        synced = 0

        for variant in needs_sync:
            run_id = f"{today}__{theme}__music__{variant}__v001"
            file_path = str(disk_files[variant].relative_to(proj_root)).replace("\\", "/")

            if variant in existing_runs:
                if existing_runs[variant]["status"] != "success":
                    db.execute(
                        text("UPDATE runs SET status = 'success', error_msg = NULL WHERE id = :rid"),
                        {"rid": existing_runs[variant]["id"]},
                    )
                if variant not in existing_assets:
                    db.execute(
                        text("INSERT INTO assets (run_id, file_path, modality, created_at) VALUES (:rid, :fp, 'music', :ca)"),
                        {"rid": existing_runs[variant]["id"], "fp": file_path, "ca": created_at},
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
                        "mn": f"music-matrix-{args.config_id}", "cid": args.config_id,
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


if __name__ == "__main__":
    main()
