"""测试图生图 + 音乐生成，结果写入 MySQL。"""

from pathlib import Path

from src.config import ensure_dirs, get_api_key
from src.minimax_client import MiniMaxClient
from src.db import init_db, use_mysql
from src.image_tasks import run_i2i_task
from src.music_tasks import run_music_task

GIANT_TREE_THEME = "giant-tree"

# 使用今天的 T2I 结果作为图生图源图
SOURCE_IMAGE = Path(__file__).parent / "works/2026-04-24/assets/images/t2i/20260424_015015__giant-tree__t2i__farmer-panorama__v001_1.png"


def main() -> None:
    print("=" * 60)
    print("  测试：图生图 + 音乐生成 → MySQL")
    print("=" * 60)

    try:
        key = get_api_key()
        print(f"  API Key: {key[:8]}...")
    except ValueError as e:
        print(f"[错误] {e}")
        return

    ensure_dirs()
    init_db()
    use_mysql(True)  # pipeline 写入 MySQL

    client = MiniMaxClient()

    # ── 图生图 ────────────────────────────────────────────────
    i2i_prompt = (
        "The same young farmer tending crops on the giant leaf, "
        "close-up side view, basket of harvest, warm golden hour sunlight, "
        "consistent character identity with the panoramic scene"
    )
    print("\n─── [I2I] 图生图 ───────────────────────────────────")
    try:
        i2i_paths, i2i_run_id = run_i2i_task(
            client, i2i_prompt,
            subject_image=SOURCE_IMAGE,
            variant="farmer-closeup",
            model="image-01",
            n=1,
            aspect_ratio="16:9",
            theme=GIANT_TREE_THEME,
        )
        print(f"  [OK] 图生图完成  run_id={i2i_run_id}")
    except Exception as e:
        print(f"  [FAIL] 图生图失败: {e}")
        i2i_paths = []

    # ── 音乐生成 ──────────────────────────────────────────────
    music_prompt = (
        "Ambient folk music, gentle acoustic guitar, soft percussion, "
        "peaceful village atmosphere, nature documentary mood, "
        "morning field recordings with distant bird songs"
    )
    music_lyrics = (
        "[Verse]\n"
        "Under the giant leaf we sow\n"
        "Sunlight filters soft and low\n"
        "Fields of green on bark so wide\n"
        "Peaceful days here we reside\n"
        "[Chorus]\n"
        "Oh giant tree, our leafy home\n"
        "Where tiny feet dare roam\n"
        "In this world of wonder tall\n"
        "We answer nature's call"
    )
    print("\n─── [MUSIC] 音乐生成 ────────────────────────────────")
    try:
        music_path, music_run_id = run_music_task(
            client, music_prompt,
            lyrics=music_lyrics,
            variant="giant-tree-folk",
            model="music-2.6",
            theme=GIANT_TREE_THEME,
            is_instrumental=False,
            lyrics_optimizer=False,
        )
        print(f"  [OK] 音乐生成完成  run_id={music_run_id}")
    except Exception as e:
        print(f"  [FAIL] 音乐生成失败: {e}")

    print("\n" + "=" * 60)
    print("  测试完成，打开前端 http://localhost:5173 查看结果")
    print("=" * 60)


if __name__ == "__main__":
    main()
