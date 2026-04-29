"""
音色示例路由 /api/voices
"""

import os
import tarfile
import uuid
import requests
import time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.models import VoiceSample
from backend.schemas import VoiceSampleCreate, VoiceSampleUpdate, VoiceSampleResponse

API_BASE_URL = "https://api.minimaxi.com"

router = APIRouter()

PROJECT_ROOT = Path(__file__).parent.parent.parent
VOICE_SAMPLES_DIR = PROJECT_ROOT / "ref" / "api" / "voice" / "samples"
VOICE_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


class VoicePreviewRequest(BaseModel):
    voice_id: str
    voice_name: str
    lang: str = "zh"
    model: str = "speech-2.8-hd"
    script_text: str | None = None


@router.get("", response_model=list[VoiceSampleResponse])
def list_voices(
    lang: str | None = None,
    favorites_only: bool = False,
    limit: int = 300,
    db: Session = Depends(get_db),
):
    sql = "SELECT * FROM voice_samples WHERE 1=1"
    params = {}
    if lang:
        sql += " AND lang = :lang"
        params["lang"] = lang
    if favorites_only:
        sql += " AND is_favorite = 1"
    sql += " ORDER BY created_at DESC LIMIT :limit"
    params["limit"] = limit
    rows = db.execute(text(sql), params).fetchall()
    return [VoiceSampleResponse.model_validate(row._mapping) for row in rows]


# ⚠️ /preview 必须在 /{sample_id} 之前，否则 /preview 会被当作 sample_id="preview"
@router.post("/preview")
def preview_voice(req: VoicePreviewRequest, http_request: Request, db: Session = Depends(get_db)):
    api_key = os.getenv("MINIMAX_API_KEY", "")
    script_text = req.script_text or (
        "欢迎收听本期期货投资教育节目。今天我们来聊一聊甲醇市场的近期走势与核心逻辑，"
        "帮助投资者更好地把握行情方向，做好风险管理。"
    )

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # 1. 创建 T2S 任务
    payload = {
        "model": req.model,
        "text": script_text,
        "voice_setting": {"voice_id": req.voice_id, "speed": 1.0, "vol": 1.0, "pitch": 0},
        "audio_setting": {"audio_sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
    }
    resp = requests.post(f"{API_BASE_URL}/v1/t2a_async_v2", headers=headers, json=payload)
    resp.raise_for_status()
    result = resp.json()
    if result.get("base_resp", {}).get("status_code") != 0:
        raise HTTPException(status_code=400, detail=f"T2S创建失败: {result}")
    task_id = result["task_id"]
    file_id = result["file_id"]

    # 2. 轮询等待完成（最多 15 分钟）
    for _ in range(180):
        time.sleep(5)
        q = requests.get(
            f"{API_BASE_URL}/v1/query/t2a_async_query_v2?task_id={task_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        q.raise_for_status()
        r = q.json()
        status = r.get("status", "Processing")
        if status == "Success":
            break
        if status in ("Failed", "Expired"):
            raise HTTPException(status_code=400, detail=f"T2S任务失败: {r}")
    else:
        raise HTTPException(status_code=408, detail="T2S任务超时")

    # 3. 获取下载链接
    dl = requests.get(
        f"{API_BASE_URL}/v1/files/retrieve?file_id={file_id}",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    dl.raise_for_status()
    download_url = dl.json().get("file", {}).get("download_url", "")
    if not download_url:
        raise HTTPException(status_code=400, detail="获取下载链接失败")

    # 4. 下载 tar 并解压出 mp3
    tar_resp = requests.get(download_url)
    tar_resp.raise_for_status()

    run_id = str(uuid.uuid4())[:8]
    sample_dir = VOICE_SAMPLES_DIR / run_id
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
        raise HTTPException(status_code=500, detail="解压MP3失败")

    # 5. 写入数据库
    relative_path = f"ref/api/voice/samples/{run_id}/{mp3_name}"
    v = VoiceSample(
        voice_id=req.voice_id,
        voice_name=req.voice_name,
        lang=req.lang,
        model=req.model,
        script_text=script_text,
        file_path=relative_path,
    )
    db.add(v)
    db.commit()
    db.refresh(v)

    # 静态文件服务固定在 8002
    origin = "http://localhost:8002"
    file_url = f"{origin}/files/{relative_path}"
    return {"id": v.id, "download_url": file_url, "voice_id": req.voice_id, "voice_name": req.voice_name}


@router.get("/{sample_id}", response_model=VoiceSampleResponse)
def get_voice(sample_id: int, db: Session = Depends(get_db)):
    v = db.query(VoiceSample).filter(VoiceSample.id == sample_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="音色示例不存在")
    return v


@router.post("", response_model=VoiceSampleResponse)
def create_voice(data: VoiceSampleCreate, db: Session = Depends(get_db)):
    v = VoiceSample(
        voice_id=data.voice_id,
        voice_name=data.voice_name,
        lang=data.lang,
        model=data.model,
        script_text=data.script_text,
        file_path=data.file_path,
        file_url=data.file_url,
        notes=data.notes,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@router.patch("/{sample_id}", response_model=VoiceSampleResponse)
def update_voice(sample_id: int, data: VoiceSampleUpdate, db: Session = Depends(get_db)):
    v = db.query(VoiceSample).filter(VoiceSample.id == sample_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="音色示例不存在")
    if data.notes is not None:
        v.notes = data.notes
    if data.is_favorite is not None:
        v.is_favorite = 1 if data.is_favorite else 0
    db.commit()
    db.refresh(v)
    return v


@router.delete("/{sample_id}")
def delete_voice(sample_id: int, db: Session = Depends(get_db)):
    v = db.query(VoiceSample).filter(VoiceSample.id == sample_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="音色示例不存在")
    db.delete(v)
    db.commit()
    return {"ok": True}
