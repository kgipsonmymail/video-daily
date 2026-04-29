"""视频生成任务，所有结果写入 SQLite 数据库。"""

import base64
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy import text

from .config import assets_dir, prompts_dir, today_str, get_quota_bucket, log_quota_usage
from .db import (
    create_run, create_asset, upsert_prompt,
    get_or_create_quota, get_session, init_db, use_mysql,
)
from .client import MiniMaxClient


# ── defaults ──────────────────────────────────────────────────────────────────

DEFAULT_T2V_MODEL    = "MiniMax-Hailuo-2.3"     # T2V 标准画质 6s
DEFAULT_I2V_MODEL    = "MiniMax-Hailuo-2.3-Fast" # I2V 快速
DEFAULT_FLF_MODEL   = "MiniMax-Hailuo-02"       # 首尾帧
DEFAULT_S2V_MODEL    = "S2V-01"                  # 主体参考

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


# ── helpers ───────────────────────────────────────────────────────────────────

def _prompt_slug(prompt: str, max_len: int = 40) -> str:
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


def _local_to_data_url(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    suffix = "png" if image_path.suffix.lower() in (".png", "") else "jpeg"
    return f"data:image/{suffix};base64,{b64}"


def _image_arg(val: Path | str) -> str:
    if isinstance(val, Path) or not val.startswith("http"):
        return _local_to_data_url(Path(val))
    return val


def _download_video(url: str, out_path: Path) -> None:
    urllib.request.urlretrieve(url, out_path)


def _mark_run(session, run_id: str, status: str,
              api_resp_id: str | None = None, error_msg: str | None = None):
    session.execute(
        text("UPDATE runs SET status = :s, api_resp_id = :aid, error_msg = :e WHERE id = :rid"),
        {"s": status, "aid": api_resp_id or "", "e": error_msg or "", "rid": run_id},
    )


def _save_prompt(session, run_id: str, prompt: str, category: str) -> int:
    prompt_subdir = prompts_dir(today_str()) / category
    prompt_subdir.mkdir(parents=True, exist_ok=True)
    (prompt_subdir / f"{run_id}.txt").write_text(prompt, encoding="utf-8")
    row = upsert_prompt(session, prompt)
    return row.id


def _check_and_charge_quota(session, model: str, run_id: str = "") -> None:
    today = today_str()
    bucket_name, limit = get_quota_bucket(model)
    quota = get_or_create_quota(session, today, model, bucket_name, limit)
    if quota.used >= quota.daily_limit:
        raise RuntimeError(
            f"每日额度耗尽：{bucket_name} ({quota.used}/{quota.daily_limit})"
        )
    quota.used += 1
    log_quota_usage(
        quota_date=today,
        model=model,
        bucket_name=bucket_name,
        n_used=1,
        source="tools",
        run_id=run_id,
        category="t2v",
    )


# ── core task functions ───────────────────────────────────────────────────────

def run_t2v_task(
    client: MiniMaxClient,
    prompt: str,
    variant: str = "default",
    model: str = DEFAULT_T2V_MODEL,
    duration: int = 6,
    resolution: str = "768P",
    theme: str = "giant-tree",
) -> tuple[Path, str]:
    """
    文生视频。
    返回 (本地视频路径, run_id)。
    """
    init_db()
    use_mysql(True)
    session = get_session()
    ts = _ts_prefix()
    today = today_str()
    run_id = _build_run_id(ts, theme, "t2v", variant)

    try:
        prompt_id = _save_prompt(session, run_id, prompt, "t2v")
        _check_and_charge_quota(session, model)
        create_run(session, run_id=run_id, category="t2v", model=model,
                   variant=variant, theme=theme, status="running")

        task_id = client.create_video_task(
            model=model, prompt=prompt, duration=duration, resolution=resolution,
        )
        print(f"[T2V] Task created: {task_id}")
        result = client.wait_for_task(task_id)
        file_id = result["file_id"]
        download_url = client.get_file_download_url(file_id)

        _mark_run(session, run_id, "success", api_resp_id=task_id)

        out_dir = assets_dir(today) / "videos" / "t2v"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{run_id}.mp4"
        _download_video(download_url, out_path)

        proj_root = Path(__file__).parent.parent.parent
        rel_parts = out_path.relative_to(proj_root).parts
        rel = str(Path(*rel_parts[1:]))
        create_asset(session, run_id=run_id, file_path=str(rel),
                     modality="video", sub_type="t2v", prompt_id=prompt_id)
        print(f"[T2V] → {out_path}")
        session.commit()
        return out_path, run_id

    except Exception as exc:
        session.rollback()
        _mark_run(session, run_id, "failed", error_msg=str(exc))
        session.commit()
        raise


def run_i2v_task(
    client: MiniMaxClient,
    prompt: str,
    first_frame: Path | str,
    variant: str = "default",
    model: str = DEFAULT_I2V_MODEL,
    duration: int = 6,
    resolution: str = "768P",
    theme: str = "giant-tree",
) -> tuple[Path, str]:
    """
    图生视频。
    first_frame 可以是本地 Path（转为 Data URL）或公网 URL。
    """
    init_db()
    use_mysql(True)
    session = get_session()
    ts = _ts_prefix()
    today = today_str()
    run_id = _build_run_id(ts, theme, "i2v", variant)

    try:
        prompt_id = _save_prompt(session, run_id, prompt, "i2v")
        _check_and_charge_quota(session, model)
        create_run(session, run_id=run_id, category="i2v", model=model,
                   variant=variant, theme=theme, status="running")

        frame_url = _image_arg(first_frame)
        task_id = client.create_video_task(
            model=model, prompt=prompt, duration=duration, resolution=resolution,
            first_frame_image=frame_url,
        )
        print(f"[I2V] Task created: {task_id}")
        result = client.wait_for_task(task_id)
        file_id = result["file_id"]
        download_url = client.get_file_download_url(file_id)

        _mark_run(session, run_id, "success", api_resp_id=task_id)

        out_dir = assets_dir(today) / "videos" / "i2v"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{run_id}.mp4"
        _download_video(download_url, out_path)

        proj_root = Path(__file__).parent.parent.parent
        rel_parts = out_path.relative_to(proj_root).parts
        rel = str(Path(*rel_parts[1:]))
        create_asset(session, run_id=run_id, file_path=str(rel),
                     modality="video", sub_type="i2v", prompt_id=prompt_id)
        print(f"[I2V] → {out_path}")
        session.commit()
        return out_path, run_id

    except Exception as exc:
        session.rollback()
        _mark_run(session, run_id, "failed", error_msg=str(exc))
        session.commit()
        raise


def run_fl2v_task(
    client: MiniMaxClient,
    prompt: str,
    first_frame: Path | str,
    last_frame: Path | str,
    variant: str = "default",
    model: str = DEFAULT_FLF_MODEL,
    duration: int = 6,
    resolution: str = "768P",
    theme: str = "giant-tree",
) -> tuple[Path, str]:
    """首尾帧视频（MiniMax-Hailuo-02）。"""
    init_db()
    use_mysql(True)
    session = get_session()
    ts = _ts_prefix()
    today = today_str()
    run_id = _build_run_id(ts, theme, "fl2v", variant)

    try:
        prompt_id = _save_prompt(session, run_id, prompt, "t2v")
        _check_and_charge_quota(session, model)
        create_run(session, run_id=run_id, category="fl2v", model=model,
                   variant=variant, theme=theme, status="running")

        task_id = client.create_video_task(
            model=model, prompt=prompt, duration=duration, resolution=resolution,
            first_frame_image=_image_arg(first_frame),
            last_frame_image=_image_arg(last_frame),
        )
        print(f"[FL2V] Task created: {task_id}")
        result = client.wait_for_task(task_id)
        file_id = result["file_id"]
        download_url = client.get_file_download_url(file_id)

        _mark_run(session, run_id, "success", api_resp_id=task_id)

        out_dir = assets_dir(today) / "videos" / "flf"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{run_id}.mp4"
        _download_video(download_url, out_path)

        proj_root = Path(__file__).parent.parent.parent
        rel_parts = out_path.relative_to(proj_root).parts
        rel = str(Path(*rel_parts[1:]))
        create_asset(session, run_id=run_id, file_path=str(rel),
                     modality="video", sub_type="flf", prompt_id=prompt_id)
        print(f"[FL2V] → {out_path}")
        session.commit()
        return out_path, run_id

    except Exception as exc:
        session.rollback()
        _mark_run(session, run_id, "failed", error_msg=str(exc))
        session.commit()
        raise


def run_s2v_task(
    client: MiniMaxClient,
    prompt: str,
    subject_image: Path | str,
    variant: str = "default",
    model: str = DEFAULT_S2V_MODEL,
    duration: int = 6,
    resolution: str = "768P",
    theme: str = "giant-tree",
) -> tuple[Path, str]:
    """主体参考视频（S2V-01）。"""
    init_db()
    use_mysql(True)
    session = get_session()
    ts = _ts_prefix()
    today = today_str()
    run_id = _build_run_id(ts, theme, "s2v", variant)

    try:
        prompt_id = _save_prompt(session, run_id, prompt, "t2v")
        _check_and_charge_quota(session, model)
        create_run(session, run_id=run_id, category="s2v", model=model,
                   variant=variant, theme=theme, status="running")

        img_url = _image_arg(subject_image)
        task_id = client.create_video_task(
            model=model, prompt=prompt, duration=duration, resolution=resolution,
            subject_reference=[{"type": "character", "image": [img_url]}],
        )
        print(f"[S2V] Task created: {task_id}")
        result = client.wait_for_task(task_id)
        file_id = result["file_id"]
        download_url = client.get_file_download_url(file_id)

        _mark_run(session, run_id, "success", api_resp_id=task_id)

        out_dir = assets_dir(today) / "videos" / "s2v"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{run_id}.mp4"
        _download_video(download_url, out_path)

        proj_root = Path(__file__).parent.parent.parent
        rel_parts = out_path.relative_to(proj_root).parts
        rel = str(Path(*rel_parts[1:]))
        create_asset(session, run_id=run_id, file_path=str(rel),
                     modality="video", sub_type="s2v", prompt_id=prompt_id)
        print(f"[S2V] → {out_path}")
        session.commit()
        return out_path, run_id

    except Exception as exc:
        session.rollback()
        _mark_run(session, run_id, "failed", error_msg=str(exc))
        session.commit()
        raise
