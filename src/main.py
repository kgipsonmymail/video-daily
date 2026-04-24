"""Video Daily 入口"""

from pathlib import Path
from config import ensure_dirs, get_api_key
from minimax_client import MiniMaxClient
from video_tasks import run_t2v_task, run_i2v_task, run_fl2v_task, run_s2v_task
from image_tasks import run_t2i_task

# 巨树世界主题
GIANT_TREE_PROMPT = (
    "A giant tree world where humans live on a massive leaf the size of a town. "
    "People farm and live on the leaf surface. The leaf has fields, houses, and paths. "
    "Normal-sized plants and trees surround the giant tree in the background."
)


def main() -> None:
    """主函数：运行 4 种视频生成任务测试"""
    print("=== Video Daily - 海螺视频生成测试 ===")

    # 检查 API Key
    try:
        api_key = get_api_key()
        print(f"API Key loaded: {api_key[:8]}...")
    except ValueError as e:
        print(f"Error: {e}")
        print("请复制 .env.example 到 .env 并填入您的 API Key")
        return

    # 确保目录存在
    ensure_dirs()

    # 初始化客户端
    client = MiniMaxClient()

    print("\n--- 生成图片（用于图生视频） ---")
    # 先生成一张图片，用于后续图生视频任务
    image_paths = run_t2i_task(client, GIANT_TREE_PROMPT, n=1)
    if not image_paths:
        print("图片生成失败，跳过依赖图片的任务")
        return

    test_image_url = f"file:///{image_paths[0].as_posix()}"

    print("\n--- 测试 4 种视频生成任务 ---")

    # 任务1: 文生视频 - Hailuo-2.3-Fast-768P
    try:
        path = run_t2v_task(
            client,
            GIANT_TREE_PROMPT,
            model="MiniMax-Hailuo-2.3-Fast"
        )
        print(f"Task 1 done: {path}")
    except Exception as e:
        print(f"Task 1 failed: {e}")

    # 任务2: 文生视频 - Hailuo-2.3-768P
    try:
        path = run_t2v_task(
            client,
            GIANT_TREE_PROMPT,
            model="MiniMax-Hailuo-2.3"
        )
        print(f"Task 2 done: {path}")
    except Exception as e:
        print(f"Task 2 failed: {e}")

    # 任务3: 图生视频 (需要先有图片)
    # 注：实际使用时图片需要是公网 URL，这里先用生成的图片测试
    try:
        # 由于本地文件无法直接作为 URL 使用，这里演示结构
        # 实际运行需要将图片上传到公网或使用其他方式
        print("[I2V] Skipped - 需要公网图片URL")
    except Exception as e:
        print(f"Task 3 failed: {e}")

    # 任务4: 首尾帧视频 (MiniMax-Hailuo-02)
    try:
        # 同上，需要公网 URL
        print("[FL2V] Skipped - 需要公网图片URL")
    except Exception as e:
        print(f"Task 4 failed: {e}")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()