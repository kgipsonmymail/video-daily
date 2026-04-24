"""图片生成任务"""

import urllib.request
from pathlib import Path
from .config import PHOTO_DIR, ensure_dirs
from .minimax_client import MiniMaxClient


def download_image(url: str, output_path: Path) -> None:
    """下载图片到本地"""
    urllib.request.urlretrieve(url, output_path)


def run_t2i_task(
    client: MiniMaxClient,
    prompt: str,
    model: str = "image-01",
    n: int = 1,
    aspect_ratio: str = "16:9"
) -> list[Path]:
    """文生图任务"""
    print(f"[T2I] Creating text-to-image with {model}: {prompt[:50]}...")
    result = client.create_image_task(
        model=model,
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        n=n,
        response_format="url"
    )

    image_urls = result.get("data", {}).get("image_urls", [])
    paths = []

    base_filename = prompt[:40].replace(" ", "_").replace(",", "").replace("/", "-")

    for i, url in enumerate(image_urls):
        output_path = PHOTO_DIR / f"{base_filename}{i+1}.png"
        download_image(url, output_path)
        paths.append(output_path)
        print(f"[T2I] Saved to: {output_path}")

    return paths


def run_i2i_task(
    client: MiniMaxClient,
    prompt: str,
    subject_image_url: str,
    model: str = "image-01",
    n: int = 1,
    aspect_ratio: str = "16:9"
) -> list[Path]:
    """图生图任务（主体参考）"""
    print(f"[I2I] Creating image-to-image with {model}: {prompt[:50]}...")
    result = client.create_image_task(
        model=model,
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        n=n,
        response_format="url",
        subject_reference=[{
            "type": "character",
            "image_file": subject_image_url
        }]
    )

    image_urls = result.get("data", {}).get("image_urls", [])
    paths = []

    base_filename = prompt[:40].replace(" ", "_").replace(",", "").replace("/", "-")

    for i, url in enumerate(image_urls):
        output_path = PHOTO_DIR / f"{base_filename}_i2i{i+1}.png"
        download_image(url, output_path)
        paths.append(output_path)
        print(f"[I2I] Saved to: {output_path}")

    return paths