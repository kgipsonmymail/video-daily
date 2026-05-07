"""
音频工坊路由 /api/audio
精细化 T2S 生成，完整透传 speech-2.8-hd 所有参数
"""

import asyncio
import os
import tarfile
import uuid
import requests
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.models import VoiceSample, Quota
from backend.schemas import VoiceSampleResponse
from backend.quota_logger import log_quota_usage
from backend.config import get_quota_bucket

API_BASE_URL = "https://api.minimaxi.com"

router = APIRouter()

PROJECT_ROOT = Path(__file__).parent.parent.parent
AUDIO_OUTPUT_DIR = PROJECT_ROOT / "ref" / "api" / "voice" / "audio_studio"
AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Request/Response models ────────────────────────────────────────────

class VoiceModify(BaseModel):
    pitch: int | None = None          # [-100, 100]
    intensity: int | None = None      # [-100, 100]
    timbre: int | None = None          # [-100, 100]
    sound_effects: str | None = None   # spacious_echo / auditorium_echo / lofi_telephone / robotic


class AudioSetting(BaseModel):
    audio_sample_rate: int = 32000
    bitrate: int = 128000
    format: str = "mp3"               # mp3 / pcm / flac
    channel: int = 1                  # 1=单声道 2=双声道


class AudioGenerateRequest(BaseModel):
    text: str
    voice_id: str
    model: str = "speech-2.8-hd"
    speed: float = 1.0               # [0.5, 2.0]
    vol: float = 1.0                 # (0, 10]
    pitch: int = 0                  # [-12, 12]
    emotion: str | None = None       # happy / sad / angry / fearful / disgusted / surprised / calm / fluent
    voice_modify: VoiceModify | None = None
    audio_setting: AudioSetting | None = None
    language_boost: str | None = None
    pronunciation_dict: dict | None = None
    aigc_watermark: bool = False
    notes: str | None = None


class AudioGenerateResponse(BaseModel):
    id: int
    file_url: str
    voice_id: str
    voice_name: str
    lang: str
    model: str
    script_text: str


# ── Helpers ────────────────────────────────────────────────────────────

def get_audio_url(file_path: str) -> str:
    return f"http://localhost:8000/files/{file_path}"


# ── Endpoints ──────────────────────────────────────────────────────────

def _build_payload(req: AudioGenerateRequest, text: str) -> dict:
    """Build API payload for a single line of text."""
    voice_setting = {
        "voice_id": req.voice_id,
        "speed": req.speed,
        "vol": req.vol,
        "pitch": req.pitch,
    }
    if req.emotion:
        voice_setting["emotion"] = req.emotion
    audio_setting = (req.audio_setting or AudioSetting()).model_dump()
    payload: dict = {
        "model": req.model,
        "text": text,
        "voice_setting": voice_setting,
        "audio_setting": audio_setting,
    }
    if req.voice_modify:
        payload["voice_modify"] = req.voice_modify.model_dump(exclude_none=True)
    if req.language_boost:
        payload["language_boost"] = req.language_boost
    if req.pronunciation_dict:
        payload["pronunciation_dict"] = req.pronunciation_dict
    if req.aigc_watermark:
        payload["aigc_watermark"] = True
    return payload


def _poll_task(task_id: str, headers: dict) -> None:
    for _ in range(180):
        time.sleep(5)
        q = requests.get(
            f"{API_BASE_URL}/v1/query/t2a_async_query_v2?task_id={task_id}",
            headers=headers,
        )
        q.raise_for_status()
        r = q.json()
        status = r.get("status", "Processing")
        if status == "Success":
            return
        if status in ("Failed", "Expired"):
            raise HTTPException(status_code=400, detail=f"T2S任务失败: {r}")
    raise HTTPException(status_code=408, detail="T2S任务超时")


def _extract_tar(tar_resp: requests.Response, run_id: str) -> tuple[Path, str]:
    sample_dir = AUDIO_OUTPUT_DIR / run_id
    sample_dir.mkdir(parents=True, exist_ok=True)
    tar_path = sample_dir / "output.tar"
    with open(tar_path, "wb") as f:
        f.write(tar_resp.content)
    mp3_name = None
    with tarfile.open(tar_path, "r") as tar:
        for member in tar.getmembers():
            if member.name.endswith(".mp3"):
                member.name = os.path.basename(member.name)
                tar.extract(member, sample_dir)
                mp3_name = member.name
                break
        if not mp3_name:
            for member in tar.getmembers():
                if member.name.endswith((".pcm", ".flac")):
                    member.name = os.path.basename(member.name)
                    tar.extract(member, sample_dir)
                    mp3_name = member.name
                    break
    if not mp3_name:
        raise HTTPException(status_code=500, detail="解压音频文件失败")
    return sample_dir, mp3_name


def _charge_quota(db: Session, model: str) -> None:
    today = date.today().isoformat()
    bucket_name, limit = get_quota_bucket(model)
    row = db.execute(
        text("SELECT id, used FROM quotas WHERE quota_date = :d AND model = :m"),
        {"d": today, "m": model},
    ).fetchone()
    if row:
        db.execute(text("UPDATE quotas SET used = used + 1 WHERE id = :id"), {"id": row[0]})
    else:
        q = Quota(quota_date=today, model=model, bucket_name=bucket_name, daily_limit=limit, used=1)
        db.add(q)
    db.flush()
    log_quota_usage(quota_date=today, model=model, bucket_name=bucket_name, n_used=1, source="backend", category="tts")


def _generate_single(db: Session, req: AudioGenerateRequest, text: str, index: int) -> AudioGenerateResponse:
    """Generate audio for a single line of text."""
    api_key = os.getenv("MINIMAX_API_KEY", "")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = _build_payload(req, text)

    resp = requests.post(f"{API_BASE_URL}/v1/t2a_async_v2", headers=headers, json=payload)
    resp.raise_for_status()
    result = resp.json()
    if result.get("base_resp", {}).get("status_code") != 0:
        raise HTTPException(status_code=400, detail=f"T2S创建失败: {result}")

    _poll_task(result["task_id"], headers)

    dl = requests.get(f"{API_BASE_URL}/v1/files/retrieve?file_id={result['file_id']}", headers=headers)
    dl.raise_for_status()
    download_url = dl.json().get("file", {}).get("download_url", "")
    if not download_url:
        raise HTTPException(status_code=400, detail="获取下载链接失败")

    tar_resp = requests.get(download_url)
    tar_resp.raise_for_status()

    run_id = f"{str(uuid.uuid4())[:8]}-{index}"
    _, mp3_name = _extract_tar(tar_resp, run_id)

    _charge_quota(db, req.model)

    import json
    gen_params = {
        "speed": req.speed,
        "vol": req.vol,
        "pitch": req.pitch,
        "emotion": req.emotion,
        "voice_modify": req.voice_modify.model_dump(exclude_none=True) if req.voice_modify else None,
        "audio_setting": req.audio_setting.model_dump() if req.audio_setting else None,
        "language_boost": req.language_boost,
        "model": req.model,
    }

    relative_path = f"ref/api/voice/audio_studio/{run_id}/{mp3_name}"
    voice_name = req.notes or req.voice_id
    v = VoiceSample(
        voice_id=req.voice_id,
        voice_name=voice_name,
        lang="zh",
        model=req.model,
        script_text=text,
        file_path=relative_path,
        notes="audio_studio",
        generation_params=json.dumps(gen_params),
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return AudioGenerateResponse(
        id=v.id,
        file_url=get_audio_url(relative_path),
        voice_id=req.voice_id,
        voice_name=voice_name,
        lang="zh",
        model=req.model,
        script_text=text,
    )


@router.post("/generate", response_model=list[AudioGenerateResponse])
async def generate_audio(req: AudioGenerateRequest, db: Session = Depends(get_db)):
    """
    生成音频，支持多行文本拆分。
    每行视为独立任务，并发调用 MiniMax API 并生成独立的历史记录。
    """
    lines = [line.strip() for line in req.text.split("\n") if line.strip()]
    if not lines:
        raise HTTPException(status_code=400, detail="文本不能为空")

    async def run_one(line: str, i: int) -> AudioGenerateResponse:
        return await asyncio.to_thread(_generate_single, db, req, line, i)

    results = await asyncio.gather(*[run_one(line, i) for i, line in enumerate(lines)])
    return list(results)


@router.get("/history", response_model=list[VoiceSampleResponse])
def list_audio_history(
    limit: int = 100,
    lang: str | None = None,
    db: Session = Depends(get_db),
):
    """List audio studio history (only records with notes='audio_studio')."""
    import json
    sql = "SELECT * FROM voice_samples WHERE notes = :note"
    params: dict = {"note": "audio_studio", "limit": limit}
    if lang:
        sql += " AND lang = :lang"
        params["lang"] = lang
    sql += " ORDER BY created_at DESC LIMIT :limit"
    rows = db.execute(text(sql), params).fetchall()
    records = []
    for row in rows:
        mapping = row._mapping
        if mapping.get("generation_params") and isinstance(mapping["generation_params"], str):
            mapping = {**mapping, "generation_params": json.loads(mapping["generation_params"])}
        records.append(VoiceSampleResponse.model_validate(mapping))
    return records