"""
音乐生成路由 /api/music
"""

from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
import urllib.request

from backend.database import get_db
from backend.models import Run, Asset, Prompt, Quota
from backend.config import get_settings, get_quota_bucket
from backend.quota_logger import log_quota_usage

router = APIRouter()

PROJECT_ROOT = Path(__file__).parent.parent.parent


def _ts_prefix() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _slug(prompt: str, max_len: int = 30) -> str:
    return (
        prompt[:max_len]
        .replace(" ", "_")
        .replace(",", "")
        .replace("/", "-")
        .replace("\n", "_")
    )


def _charge_quota(db: Session, quota_date: str, model: str):
    bucket_name, limit = get_quota_bucket(model)
    row = db.execute(
        text("SELECT id FROM quotas WHERE quota_date = :d AND model = :m"),
        {"d": quota_date, "m": model},
    ).fetchone()
    if row:
        db.execute(
            text("UPDATE quotas SET used = used + 1 WHERE id = :id"),
            {"id": row[0]},
        )
    else:
        q = Quota(
            quota_date=quota_date,
            model=model,
            bucket_name=bucket_name,
            daily_limit=limit,
            used=1,
        )
        db.add(q)
    db.flush()
    log_quota_usage(
        quota_date=quota_date,
        model=model,
        bucket_name=bucket_name,
        n_used=1,
        source="backend",
        category="music",
    )


def _upsert_prompt(db: Session, text: str, theme: str) -> Prompt:
    row = db.execute(
        text("SELECT id FROM prompts WHERE text = :t"),
        {"t": text}
    ).fetchone()
    if row:
        return db.query(Prompt).get(row[0])
    p = Prompt(text=text, lang="en", theme=theme)
    db.add(p)
    db.flush()
    return p


def _mark_run(db: Session, run_id: str, status: str, error_msg: str | None = None):
    if error_msg:
        db.execute(
            text("UPDATE runs SET status = :s, error_msg = :e WHERE id = :rid"),
            {"s": status, "e": error_msg, "rid": run_id},
        )
    else:
        db.execute(
            text("UPDATE runs SET status = :s WHERE id = :rid"),
            {"s": status, "rid": run_id},
        )


# ── schemas ─────────────────────────────────────────────────────────────────

class MusicGenerateRequest(BaseModel):
    prompt: str
    model: str = "music-2.6"
    lyrics: str = ""
    is_instrumental: bool = False
    lyrics_optimizer: bool = False
    output_format: str = "url"
    aigc_watermark: bool = False
    audio_url: str = ""
    audio_setting: dict | None = None
    variant: str = "default"
    theme: str = "giant-tree"


class MusicGenerateResponse(BaseModel):
    run_id: str
    assets: list[dict]


# ── music generation ─────────────────────────────────────────────────────────

@router.post("/generate", response_model=MusicGenerateResponse)
def generate_music(req: MusicGenerateRequest, db: Session = Depends(get_db)):
    """
    生成音乐并写入数据库和文件系统。
    API 文档：ref/api/music/音乐生成_Music_Generation.md
    """
    import requests as _requests

    settings = get_settings()
    ts = _ts_prefix()
    today = date.today().isoformat()
    run_id = f"{ts}__{req.theme}__{'music'}__{_slug(req.variant, 20)}__v001"

    try:
        prompt_row = _upsert_prompt(db, req.prompt, req.theme)

        run = Run(
            id=run_id,
            theme=req.theme,
            category="music",
            model=req.model,
            variant=req.variant,
            status="running",
            quota_date=today,
        )
        db.add(run)
        db.flush()

        payload: dict = {
            "model": req.model,
            "prompt": req.prompt,
            "lyrics": req.lyrics,
            "is_instrumental": req.is_instrumental,
            "lyrics_optimizer": req.lyrics_optimizer,
            "output_format": req.output_format,
            "aigc_watermark": req.aigc_watermark,
        }
        if req.audio_setting:
            payload["audio_setting"] = req.audio_setting
        if req.audio_url:
            payload["audio_url"] = req.audio_url

        resp = _requests.post(
            "https://api.minimaxi.com/v1/music_generation",
            headers={
                "Authorization": f"Bearer {settings.minimax_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("base_resp", {}).get("status_code") != 0:
            raise Exception(f"API error: {data}")

        music_data = data.get("data", {})
        status = music_data.get("status")
        if status != 2:
            raise Exception(f"Music generation not complete: status={status}")

        out_dir = PROJECT_ROOT / "works" / today / "assets" / "music"
        out_dir.mkdir(parents=True, exist_ok=True)

        created_assets = []

        if req.output_format == "hex":
            hex_audio = music_data.get("audio", "")
            if not hex_audio:
                raise Exception("No audio data in response")
            fname = f"{run_id}.mp3"
            out_path = out_dir / fname
            audio_bytes = bytes.fromhex(hex_audio)
            out_path.write_bytes(audio_bytes)
            rel_parts = out_path.relative_to(PROJECT_ROOT).parts
            rel = str(Path(*rel_parts[1:]))
        else:
            audio_url = music_data.get("audio", "")
            if not audio_url:
                raise Exception("No audio URL in response")
            fname = f"{run_id}.mp3"
            out_path = out_dir / fname
            try:
                urllib.request.urlretrieve(audio_url, out_path)
            except Exception as dl_err:
                raise Exception(f"Failed to download audio from {audio_url}: {dl_err}")
            rel_parts = out_path.relative_to(PROJECT_ROOT).parts
            rel = str(Path(*rel_parts[1:]))

        asset = Asset(
            run_id=run_id,
            prompt_id=prompt_row.id,
            file_path=rel,
            modality="music",
            sub_type="song",
        )
        db.add(asset)
        db.flush()

        _mark_run(db, run_id, "success")
        _charge_quota(db, today, req.model)

        created_assets.append({
            "id": asset.id,
            "run_id": run_id,
            "file_path": rel,
            "modality": "music",
            "sub_type": "song",
            "aspect_ratio": None,
            "seed": None,
            "created_at": asset.created_at.isoformat() if asset.created_at else "",
            "external_url": None,
            "prompt_text": req.prompt,
        })
        print(f"[MUSIC] → {out_path}")

        db.commit()
        return MusicGenerateResponse(run_id=run_id, assets=created_assets)

    except Exception as exc:
        db.rollback()
        _mark_run(db, run_id, "failed", error_msg=str(exc))
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc))


# ── lyrics generation ─────────────────────────────────────────────────────────

class LyricsGenerateRequest(BaseModel):
    prompt: str = ""
    mode: str = "write_full_song"
    title: str = ""
    lyrics: str = ""


class LyricsGenerateResponse(BaseModel):
    song_title: str = ""
    style_tags: str = ""
    lyrics: str = ""


@router.post("/lyrics", response_model=LyricsGenerateResponse)
def generate_lyrics(req: LyricsGenerateRequest, db: Session = Depends(get_db)):
    """
    生成歌词并写入数据库和文件系统。
    API 文档：ref/api/music/歌词生成_Lyrics_Generation.md
    """
    import requests as _requests

    settings = get_settings()
    ts = _ts_prefix()
    today = date.today().isoformat()
    run_id = f"{ts}__lyrics__{_slug(req.title or req.prompt or 'default', 20)}__v001"

    try:
        # 创建 run 记录
        run = Run(
            id=run_id,
            theme="lyrics",
            category="lyrics",
            model="lyrics_generation",
            variant=req.mode,
            status="running",
            quota_date=today,
        )
        db.add(run)
        db.flush()

        payload: dict = {"mode": req.mode}
        if req.prompt:
            payload["prompt"] = req.prompt
        if req.title:
            payload["title"] = req.title
        if req.mode == "edit" and req.lyrics:
            payload["lyrics"] = req.lyrics

        resp = _requests.post(
            "https://api.minimaxi.com/v1/lyrics_generation",
            headers={
                "Authorization": f"Bearer {settings.minimax_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("base_resp", {}).get("status_code") != 0:
            raise HTTPException(status_code=400, detail=f"歌词生成失败: {data.get('base_resp', {}).get('status_msg')}")

        song_title = data.get("song_title") or ""
        style_tags = data.get("style_tags") or ""
        lyrics_text = data.get("lyrics") or ""

        # 保存歌词到 txt 文件
        prompt_dir = PROJECT_ROOT / "works" / today / "prompts" / "lyrics"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = prompt_dir / f"{run_id}.txt"
        content_lines = []
        if song_title:
            content_lines.append(f"Title: {song_title}")
        if style_tags:
            content_lines.append(f"Style: {style_tags}")
        content_lines.append(f"Mode: {req.mode}")
        content_lines.append("")
        content_lines.append(lyrics_text)
        prompt_file.write_text("\n".join(content_lines), encoding="utf-8")

        # 关联 prompt
        prompt_text = f"[{req.mode}] {req.prompt or req.title or ''}"
        prompt_row = _upsert_prompt(db, prompt_text, theme="lyrics")

        # 写入 asset 记录
        rel_parts = prompt_file.relative_to(PROJECT_ROOT).parts
        rel = str(Path(*rel_parts[1:]))
        asset = Asset(
            run_id=run_id,
            prompt_id=prompt_row.id,
            file_path=rel,
            modality="text",
            sub_type="lyrics",
        )
        db.add(asset)
        db.flush()

        _mark_run(db, run_id, "success")

        # 扣减 lyrics_generation 额度
        bucket_name, limit = get_quota_bucket("lyrics_generation")
        row = db.execute(
            text("SELECT id, used FROM quotas WHERE quota_date = :d AND model = :m"),
            {"d": today, "m": "lyrics_generation"},
        ).fetchone()
        if row:
            db.execute(
                text("UPDATE quotas SET used = used + 1 WHERE id = :id"),
                {"id": row[0]},
            )
        else:
            q = Quota(
                quota_date=today,
                model="lyrics_generation",
                bucket_name=bucket_name,
                daily_limit=limit,
                used=1,
            )
            db.add(q)
        db.flush()
        log_quota_usage(
            quota_date=today,
            model="lyrics_generation",
            bucket_name=bucket_name,
            n_used=1,
            source="backend",
            category="lyrics",
        )

        db.commit()

        return LyricsGenerateResponse(
            song_title=song_title,
            style_tags=style_tags,
            lyrics=lyrics_text,
        )

    except HTTPException:
        db.rollback()
        _mark_run(db, run_id, "failed")
        db.commit()
        raise
    except Exception as exc:
        db.rollback()
        _mark_run(db, run_id, "failed", error_msg=str(exc))
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc))
