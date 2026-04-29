"""Video Daily 入口：巨树世界主题，4 种视频生成任务 + 文生图/图生图测试。"""

from pathlib import Path

from .config import ensure_dirs, get_api_key
from .client import MiniMaxClient
from .db import init_db
from .image_tasks import run_t2i_task, run_i2i_task
from .video_tasks import (
    run_t2v_task, run_i2v_task, run_fl2v_task, run_s2v_task,
    GIANT_TREE_PROMPT, GIANT_TREE_SCENES,
    DEFAULT_T2V_MODEL, DEFAULT_I2V_MODEL, DEFAULT_FLF_MODEL, DEFAULT_S2V_MODEL,
)


GIANT_TREE_THEME = "giant-tree"


def main() -> None:
    print("=" * 60)
    print("  Video Daily — 巨树世界生成管线")
    print("=" * 60)

    # 检查 API Key
    try:
        key = get_api_key()
        print(f"  API Key: {key[:8]}...")
    except ValueError as e:
        print(f"[错误] {e}\n请复制 .env.example 到 .env 并填入您的 API Key")
        return

    # 初始化目录和数据库
    ensure_dirs()
    init_db()

    client = MiniMaxClient()
    today = __import__('datetime').date.today().isoformat()
    print(f"\n  日期：{today}\n")

    # ── 任务 1 & 2：文生图 + 图生图（同时生成图片素材备用）─────────────
    print("─── [任务 A] 文生图 ───────────────────────────────────")
    t2i_prompt = GIANT_TREE_PROMPT
    try:
        t2i_paths, t2i_run_id = run_t2i_task(
            client, t2i_prompt,
            variant="farmer-panorama",
            model="image-01",
            n=2,
            aspect_ratio="16:9",
            theme=GIANT_TREE_THEME,
        )
        print(f"  [OK] 文生图完成  run_id={t2i_run_id}\n")
    except Exception as e:
        print(f"  [FAIL] 文生图失败: {e}\n")
        t2i_paths, t2i_run_id = [], ""

    print("─── [任务 B] 图生图（基于文生图结果） ──────────────────")
    i2i_prompt = (
        "The same young farmer walking through a market built on the giant leaf, "
        "side view, basket of seeds, warm sunset light, consistent character identity"
    )
    source_img = t2i_paths[0] if t2i_paths else None
    if source_img:
        try:
            i2i_paths, i2i_run_id = run_i2i_task(
                client, i2i_prompt,
                subject_image=source_img,
                variant="farmer-market",
                model="image-01",
                n=1,
                aspect_ratio="16:9",
                theme=GIANT_TREE_THEME,
            )
            print(f"  [OK] 图生图完成  run_id={i2i_run_id}\n")
        except Exception as e:
            print(f"  [FAIL] 图生图失败: {e}\n")
            i2i_paths = []
    else:
        print("  [SKIP] 跳过（无源图）\n")
        i2i_paths = []

    # ── 任务 3 & 4：文生视频（两种模型）──────────────────────────────
    print(f"─── [任务 C] 文生视频 — {DEFAULT_T2V_MODEL} ───────────────────────────")
    try:
        t2v_path, t2v_run_id = run_t2v_task(
            client, GIANT_TREE_PROMPT,
            variant="leaf-town-standard",
            model=DEFAULT_T2V_MODEL,
            duration=6,
            resolution="768P",
            theme=GIANT_TREE_THEME,
        )
        print(f"  [OK] 文生视频完成  run_id={t2v_run_id}\n")
    except Exception as e:
        print(f"  [FAIL] 文生视频失败: {e}\n")
        t2v_path, t2v_run_id = None, ""

    print(f"─── [任务 D] 文生视频 — {DEFAULT_I2V_MODEL} ───────────────────────────")
    try:
        t2v_fast_path, t2v_fast_run_id = run_t2v_task(
            client, GIANT_TREE_PROMPT,
            variant="leaf-town-fast",
            model=DEFAULT_I2V_MODEL,  # I2V 模型也可用于纯 T2V
            duration=6,
            resolution="768P",
            theme=GIANT_TREE_THEME,
        )
        print(f"  [OK] 文生视频完成  run_id={t2v_fast_run_id}\n")
    except Exception as e:
        print(f"  [FAIL] 文生视频（Fast）失败: {e}\n")
        t2v_fast_path = None

    # ── 任务 5：图生视频（用第一张文生图做首帧）─────────────────────
    print("─── [任务 E] 图生视频（文生图 → 首帧） ──────────────────")
    if t2i_paths:
        try:
            i2v_path, i2v_run_id = run_i2v_task(
                client,
                "A slow pan across the giant leaf town at golden hour, cinematic drone shot",
                first_frame=t2i_paths[0],
                variant="t2i-to-video",
                model=DEFAULT_I2V_MODEL,
                duration=6,
                theme=GIANT_TREE_THEME,
            )
            print(f"  [OK] 图生视频完成  run_id={i2v_run_id}\n")
        except Exception as e:
            print(f"  [FAIL] 图生视频失败: {e}\n")
    else:
        print("  [SKIP] 跳过（无源图）\n")

    # ── 任务 6：首尾帧视频（需要两张图，文生图+图生图）─────────────
    if t2i_paths and len(t2i_paths) >= 2:
        print("─── [任务 F] 首尾帧视频 ────────────────────────────────")
        try:
            flf_path, flf_run_id = run_fl2v_task(
                client,
                "Time-lapse of a day on the giant leaf: sunrise to market bustle to sunset",
                first_frame=t2i_paths[0],
                last_frame=t2i_paths[1] if len(t2i_paths) > 1 else t2i_paths[0],
                variant="leaf-day-cycle",
                model=DEFAULT_FLF_MODEL,
                duration=6,
                theme=GIANT_TREE_THEME,
            )
            print(f"  [OK] 首尾帧视频完成  run_id={flf_run_id}\n")
        except Exception as e:
            print(f"  [FAIL] 首尾帧视频失败: {e}\n")

    print("=" * 60)
    print("  管线结束")
    print("  运行 'streamlit run streamlit_viewer.py' 查看结果")
    print("=" * 60)


if __name__ == "__main__":
    main()
