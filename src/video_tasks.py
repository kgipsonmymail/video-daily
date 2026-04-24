"""视频生成任务"""

import base64
import urllib.request
from pathlib import Path
from .config import VIDEO_DIR, PHOTO_DIR, ensure_dirs
from .minimax_client import MiniMaxClient


def local_image_to_data_url(image_path: Path) -> str:
    """将本地图片转为 Base64 Data URL，供 API 使用"""
    with open(image_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/png;base64,{b64}"


# 巨树世界主题 prompt
GIANT_TREE_PROMPT = (
    "A giant tree world where humans live on a massive leaf the size of a town. "
    "People farm and live on the leaf surface. The leaf has fields, houses, and paths. "
    "Normal-sized plants and trees surround the giant tree in the background."
)

GIANT_TREE_SCENES = [
    "Panoramic view of a town built on a giant leaf, with farms and houses",
    "Close-up of farmers cultivating fields on a massive leaf surface",
    "Aerial view showing the contrast between the giant tree and normal-sized plants",
    "People walking on a leaf surface with normal trees visible at the edge",
]


def get_prompt_filename(prompt: str) -> str:
    """从 prompt 生成文件名（取前40字符，替换空格）"""
    clean = prompt[:40].replace(" ", "_").replace(",", "").replace("/", "-")
    return clean


def download_video(url: str, output_path: Path) -> None:
    """下载视频到本地"""
    urllib.request.urlretrieve(url, output_path)


def run_t2v_task(client: MiniMaxClient, prompt: str, model: str = "MiniMax-Hailuo-2.3") -> Path:
    """文生视频任务"""
    print(f"[T2V] Creating text-to-video with {model}: {prompt[:50]}...")
    task_id = client.create_video_task(model=model, prompt=prompt, duration=6, resolution="768P")
    print(f"[T2V] Task created: {task_id}")
    result = client.wait_for_task(task_id)
    file_id = result["file_id"]
    download_url = client.get_file_download_url(file_id)

    filename = get_prompt_filename(prompt)
    output_path = VIDEO_DIR / f"{filename}.mp4"
    download_video(download_url, output_path)
    print(f"[T2V] Saved to: {output_path}")
    return output_path


def run_i2v_task(
    client: MiniMaxClient,
    prompt: str,
    image_url: str,
    model: str = "MiniMax-Hailuo-2.3"
) -> Path:
    """图生视频任务"""
    print(f"[I2V] Creating image-to-video with {model}: {prompt[:50]}...")
    task_id = client.create_video_task(
        model=model,
        prompt=prompt,
        duration=6,
        resolution="768P",
        first_frame_image=image_url
    )
    print(f"[I2V] Task created: {task_id}")
    result = client.wait_for_task(task_id)
    file_id = result["file_id"]
    download_url = client.get_file_download_url(file_id)

    filename = get_prompt_filename(prompt)
    output_path = VIDEO_DIR / f"{filename}_i2v.mp4"
    download_video(download_url, output_path)
    print(f"[I2V] Saved to: {output_path}")
    return output_path


def run_fl2v_task(
    client: MiniMaxClient,
    prompt: str,
    first_frame_url: str,
    last_frame_url: str
) -> Path:
    """首尾帧视频任务 (MiniMax-Hailuo-02)"""
    print(f"[FL2V] Creating first-last-frame video: {prompt[:50]}...")
    task_id = client.create_video_task(
        model="MiniMax-Hailuo-02",
        prompt=prompt,
        duration=6,
        resolution="768P",
        first_frame_image=first_frame_url,
        last_frame_image=last_frame_url
    )
    print(f"[FL2V] Task created: {task_id}")
    result = client.wait_for_task(task_id)
    file_id = result["file_id"]
    download_url = client.get_file_download_url(file_id)

    filename = get_prompt_filename(prompt)
    output_path = VIDEO_DIR / f"{filename}_fl2v.mp4"
    download_video(download_url, output_path)
    print(f"[FL2V] Saved to: {output_path}")
    return output_path


def run_s2v_task(
    client: MiniMaxClient,
    prompt: str,
    subject_image_url: str
) -> Path:
    """主体参考视频任务 (S2V-01)"""
    print(f"[S2V] Creating subject-reference video: {prompt[:50]}...")
    task_id = client.create_video_task(
        model="S2V-01",
        prompt=prompt,
        duration=6,
        resolution="768P",
        subject_reference=[{
            "type": "character",
            "image": [subject_image_url]
        }]
    )
    print(f"[S2V] Task created: {task_id}")
    result = client.wait_for_task(task_id)
    file_id = result["file_id"]
    download_url = client.get_file_download_url(file_id)

    filename = get_prompt_filename(prompt)
    output_path = VIDEO_DIR / f"{filename}_s2v.mp4"
    download_video(download_url, output_path)
    print(f"[S2V] Saved to: {output_path}")
    return output_path