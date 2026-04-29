"""音乐生成任务，结果写入 MySQL 数据库。"""

import base64
import binascii
import urllib.request
from datetime import datetime
from pathlib import Path

from .config import assets_dir, prompts_dir, today_str, get_quota_bucket, log_quota_usage
from .db import (
    create_run, create_asset, upsert_prompt,
    get_or_create_quota, get_session, init_db,
)
from .client import MiniMaxClient


DEFAULT_MUSIC_MODEL = "music-2.6"

MUSIC_QUOTA_BUCKETS = {
    DEFAULT_MUSIC_MODEL: ("music-2.6", 100),
    "music-2.6-free": ("music-2.6-free", 4),
    "music-cover": ("music-cover", 100),
    "music-cover-free": ("music-cover-free", 4),
}
# Keep for reference but use get_quota_bucket() for actual lookups


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


def _hex_to_file(hex_str: str, out_path: Path) -> None:
    """将 hex 编码的音频写入文件。"""
    audio_data = bytes.fromhex(hex_str)
    out_path.write_bytes(audio_data)


def _check_and_charge_quota(session, model: str, run_id: str = "") -> None:
    today = today_str()
    bucket_name, limit = get_quota_bucket(model)
    quota = get_or_create_quota(session, today, model, bucket_name, limit)
    if quota.used >= quota.daily_limit:
        raise RuntimeError(f"每日额度耗尽：{bucket_name} ({quota.used}/{quota.daily_limit})")
    quota.used += 1
    log_quota_usage(
        quota_date=today,
        model=model,
        bucket_name=bucket_name,
        n_used=1,
        source="tools",
        run_id=run_id,
        category="music",
    )


def run_music_task(
    client: MiniMaxClient,
    prompt: str,
    lyrics: str = "",
    variant: str = "default",
    model: str = DEFAULT_MUSIC_MODEL,
    theme: str = "giant-tree",
    is_instrumental: bool = False,
    lyrics_optimizer: bool = False,
) -> tuple[Path, str]:
    """
    音乐生成：调用 MiniMax 音乐生成 API，结果写入 MySQL 数据库和 works/ 目录。
    返回 (本地音频路径, run_id)。

    API 文档：ref/api/music/音乐生成_Music_Generation.md
    """
    init_db()
    session = get_session()
    ts = _ts_prefix()
    today = today_str()
    run_id = _build_run_id(ts, theme, "music", variant)

    try:
        # 保存 prompt 文件
        prompt_subdir = prompts_dir(today) / "music"
        prompt_subdir.mkdir(parents=True, exist_ok=True)
        prompt_file = prompt_subdir / f"{run_id}.txt"
        prompt_file.write_text(f"prompt: {prompt}\nlyrics:\n{lyrics}", encoding="utf-8")

        prompt_row = upsert_prompt(session, prompt, theme=theme)

        _check_and_charge_quota(session, model)

        create_run(session, run_id=run_id, category="music", model=model,
                   variant=variant, theme=theme, status="running")

        result = client.create_music_task(
            model=model,
            prompt=prompt,
            lyrics=lyrics,
            is_instrumental=is_instrumental,
            lyrics_optimizer=lyrics_optimizer,
            output_format="hex",
        )

        data = result.get("data", {})
        status = data.get("status")
        if status != 2:
            raise Exception(f"Music generation not complete: status={status}")

        hex_audio = data.get("audio", "")
        if not hex_audio:
            raise Exception("No audio data in response")

        out_dir = assets_dir(today) / "music"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{run_id}.mp3"
        _hex_to_file(hex_audio, out_path)

        # 更新 run 为成功
        session.execute(
            __import__("sqlalchemy").text(
                "UPDATE runs SET status = 'success' WHERE id = :rid"
            ),
            {"rid": run_id},
        )

        proj_root = Path(__file__).parent.parent.parent
        rel_parts = out_path.relative_to(proj_root).parts
        rel = str(Path(*rel_parts[1:]))
        create_asset(
            session, run_id=run_id, file_path=str(rel),
            modality="music", sub_type="song", prompt_id=prompt_row.id,
        )
        print(f"[MUSIC] → {out_path}")
        session.commit()
        return out_path, run_id

    except Exception as exc:
        session.rollback()
        try:
            from sqlalchemy import text
            session.execute(
                text("UPDATE runs SET status = 'failed', error_msg = :e WHERE id = :rid"),
                {"e": str(exc), "rid": run_id},
            )
            session.commit()
        except Exception:
            session.rollback()
        raise
