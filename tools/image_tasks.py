"""图片生成任务（文生图 / 图生图），结果写入 MySQL 数据库。"""

import base64
import urllib.request
from datetime import datetime
from pathlib import Path
from sqlalchemy import text

from .config import assets_dir, prompts_dir, today_str, get_quota_bucket, log_quota_usage
from .db import (
    create_run, create_asset, upsert_prompt,
    get_or_create_quota, get_session, init_db, use_mysql,
)
from .client import MiniMaxClient

use_mysql(True)  # 写入 MySQL 与后端保持一致


def _prompt_slug(prompt: str, max_len: int = 40) -> str:
    """从 prompt 生成短 slug 用于文件名。"""
    return (
        prompt[:max_len]
        .replace(" ", "_")
        .replace(",", "")
        .replace("/", "-")
        .replace("\n", "_")
    )


def _ts_prefix() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _build_run_id(ts: str, theme: str, category: str, variant: str) -> str:
    slug = _prompt_slug(variant, 20)
    return f"{ts}__{theme}__{category}__{slug}__v001"


def _local_image_to_data_url(image_path: Path) -> str:
    """将本地图片转为 Base64 Data URL。"""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    suffix = "png" if image_path.suffix.lower() in (".png", "") else "jpeg"
    return f"data:image/{suffix};base64,{b64}"


def _mark_run(session, run_id: str, status: str, api_resp_id: str | None = None, error_msg: str | None = None):
    session.execute(
        text("UPDATE runs SET status = :s, api_resp_id = :aid, error_msg = :e WHERE id = :rid"),
        {"s": status, "aid": api_resp_id or "", "e": error_msg or "", "rid": run_id},
    )


def run_t2i_task(
    client: MiniMaxClient,
    prompt: str,
    variant: str = "default",
    model: str = "image-01",
    n: int = 1,
    aspect_ratio: str = "16:9",
    theme: str = "giant-tree",
    seed: int | None = None,
    prompt_optimizer: bool = False,
) -> tuple[list[Path], str]:
    """
    文生图：调用 MiniMax 文生图 API，结果存入数据库和 works/ 目录。
    返回 (产物路径列表, run_id)。
    """
    init_db()
    session = get_session()
    ts = _ts_prefix()
    today = today_str()
    run_id = _build_run_id(ts, theme, "t2i", variant)

    try:
        # 保存 prompt 文件
        prompt_subdir = prompts_dir(today) / "t2i"
        prompt_subdir.mkdir(parents=True, exist_ok=True)
        (prompt_subdir / f"{run_id}.txt").write_text(prompt, encoding="utf-8")

        # upsert prompt 记录（去重）
        prompt_row = upsert_prompt(session, prompt, theme=theme)

        # 扣减额度
        bucket_name, limit = get_quota_bucket(model)
        quota = get_or_create_quota(session, today, model, bucket_name=bucket_name, daily_limit=limit)
        quota.used += 1
        log_quota_usage(
            quota_date=today, model=model, bucket_name=bucket_name,
            n_used=1, source="tools", run_id=run_id, category="t2i",
        )

        # 创建 run 记录（初始状态 running）
        create_run(session, run_id=run_id, category="t2i", model=model,
                   variant=variant, theme=theme, status="running")

        # 调用 API
        result = client.create_image_task(
            model=model, prompt=prompt, aspect_ratio=aspect_ratio,
            n=n, response_format="url", seed=seed, prompt_optimizer=prompt_optimizer,
        )
        api_id = result.get("id", "")
        image_urls: list[str] = result.get("data", {}).get("image_urls", [])

        # 更新 run 为成功
        _mark_run(session, run_id, "success", api_resp_id=api_id)

        # 下载并写 asset 记录
        out_dir = assets_dir(today) / "images" / "t2i"
        out_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for i, url in enumerate(image_urls):
            fname = f"{run_id}_{i+1}.png"
            out_path = out_dir / fname
            urllib.request.urlretrieve(url, out_path)
            # Use POSIX slashes for cross-platform DB compatibility
            proj_root = Path(__file__).parent.parent.parent
            rel_parts = out_path.relative_to(proj_root).parts
            rel = str(Path(*rel_parts[1:]))  # drop first component (project dir name)
            create_asset(
                session, run_id=run_id, file_path=str(rel),
                modality="image", sub_type="t2i", prompt_id=prompt_row.id,
                aspect_ratio=aspect_ratio, seed=seed,
            )
            paths.append(out_path)
            print(f"[T2I]  [{i+1}/{len(image_urls)}] → {out_path}")

        session.commit()
        return paths, run_id

    except Exception as exc:
        session.rollback()
        _mark_run(session, run_id, "failed", error_msg=str(exc))
        session.commit()
        raise


def run_i2i_task(
    client: MiniMaxClient,
    prompt: str,
    subject_image: Path | str,
    variant: str = "default",
    model: str = "image-01",
    n: int = 1,
    aspect_ratio: str = "16:9",
    theme: str = "giant-tree",
    seed: int | None = None,
) -> tuple[list[Path], str]:
    """
    图生图：基于参考图（本地路径或 URL）做图生图，结果写入数据库。
    返回 (产物路径列表, run_id)。
    """
    init_db()
    session = get_session()
    ts = _ts_prefix()
    today = today_str()
    run_id = _build_run_id(ts, theme, "i2i", variant)

    try:
        # 保存 prompt 文件
        prompt_subdir = prompts_dir(today) / "i2i"
        prompt_subdir.mkdir(parents=True, exist_ok=True)
        (prompt_subdir / f"{run_id}.txt").write_text(prompt, encoding="utf-8")

        prompt_row = upsert_prompt(session, prompt, theme=theme)

        # 扣减额度
        bucket_name, limit = get_quota_bucket(model)
        quota = get_or_create_quota(session, today, model, bucket_name=bucket_name, daily_limit=limit)
        quota.used += 1
        log_quota_usage(
            quota_date=today, model=model, bucket_name=bucket_name,
            n_used=1, source="tools", run_id=run_id, category="i2i",
        )

        create_run(session, run_id=run_id, category="i2i", model=model,
                   variant=variant, theme=theme, status="running")

        # 转换参考图
        if str(subject_image).startswith("http"):
            subject_url = str(subject_image)
        else:
            subject_url = _local_image_to_data_url(Path(subject_image))

        result = client.create_image_task(
            model=model, prompt=prompt, aspect_ratio=aspect_ratio,
            n=n, response_format="url", seed=seed,
            subject_reference=[{"type": "character", "image_file": subject_url}],
        )
        api_id = result.get("id", "")
        image_urls: list[str] = result.get("data", {}).get("image_urls", [])

        _mark_run(session, run_id, "success", api_resp_id=api_id)

        out_dir = assets_dir(today) / "images" / "i2i"
        out_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for i, url in enumerate(image_urls):
            fname = f"{run_id}_{i+1}.png"
            out_path = out_dir / fname
            urllib.request.urlretrieve(url, out_path)
            # Use POSIX slashes for cross-platform DB compatibility
            proj_root = Path(__file__).parent.parent.parent
            rel_parts = out_path.relative_to(proj_root).parts
            rel = str(Path(*rel_parts[1:]))  # drop first component (project dir name)
            create_asset(
                session, run_id=run_id, file_path=str(rel),
                modality="image", sub_type="i2i", prompt_id=prompt_row.id,
                aspect_ratio=aspect_ratio, seed=seed,
            )
            paths.append(out_path)
            print(f"[I2I]  [{i+1}/{len(image_urls)}] → {out_path}")

        session.commit()
        return paths, run_id

    except Exception as exc:
        session.rollback()
        _mark_run(session, run_id, "failed", error_msg=str(exc))
        session.commit()
        raise
