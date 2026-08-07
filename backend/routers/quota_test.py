"""
额度测试路由 - 测试各种 MiniMax API 的消耗
"""
import os
import uuid
import time
import httpx
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/quota-test", tags=["quota-test"])

# MiniMax API 配置
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
MINIMAX_BASE_URL = "https://api.minimaxi.com"

# 作品存储目录
WORKS_DIR = Path(__file__).parent.parent.parent / "works"


class TestResult(BaseModel):
    """测试结果"""
    test_type: str  # image, music, video, tts, text
    model: str
    prompt: str
    status: str  # success, error
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: str
    api_response_raw: Optional[dict] = None


class TestResponse(BaseModel):
    """测试响应"""
    results: list[TestResult]
    summary: dict


def get_today_dir(modality: str) -> Path:
    """获取今天的存储目录"""
    today = datetime.now().strftime("%Y-%m-%d")
    dir_path = WORKS_DIR / modality / today
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


async def test_image_generation(prompt: str) -> TestResult:
    """测试图片生成"""
    start_time = time.time()
    run_id = str(uuid.uuid4())[:8]
    
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{MINIMAX_BASE_URL}/v1/image_generation",
                headers={"Authorization": f"Bearer {MINIMAX_API_KEY}"},
                json={
                    "model": "image-01",
                    "prompt": prompt,
                    "aspect_ratio": "1:1",
                    "n": 1,
                    "response_format": "url"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # 下载图片
            if data.get("data", {}).get("image_urls"):
                image_url = data["data"]["image_urls"][0]
                img_response = await client.get(image_url)
                img_response.raise_for_status()
                
                # 保存文件
                today_dir = get_today_dir("t2i")
                file_path = today_dir / f"{run_id}.png"
                file_path.write_bytes(img_response.content)
                
                # 保存提示词
                prompt_path = today_dir / f"{run_id}.prompt.txt"
                prompt_path.write_text(prompt, encoding="utf-8")
                
                duration = time.time() - start_time
                return TestResult(
                    test_type="image",
                    model="image-01",
                    prompt=prompt,
                    status="success",
                    file_path=str(file_path.relative_to(WORKS_DIR)),
                    file_size_bytes=len(img_response.content),
                    duration_seconds=round(duration, 2),
                    timestamp=datetime.now().isoformat(),
                    api_response_raw=data
                )
            else:
                raise Exception("No image URLs in response")
                
    except Exception as e:
        duration = time.time() - start_time
        return TestResult(
            test_type="image",
            model="image-01",
            prompt=prompt,
            status="error",
            duration_seconds=round(duration, 2),
            error_message=str(e),
            timestamp=datetime.now().isoformat()
        )


async def test_music_generation(prompt: str, instrumental: bool = True) -> TestResult:
    """测试音乐生成"""
    start_time = time.time()
    run_id = str(uuid.uuid4())[:8]
    
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{MINIMAX_BASE_URL}/v1/music_generation",
                headers={"Authorization": f"Bearer {MINIMAX_API_KEY}"},
                json={
                    "model": "music-2.6",
                    "prompt": prompt,
                    "is_instrumental": instrumental,
                    "output_format": "hex"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # 保存音频文件
            if data.get("data", {}).get("audio"):
                audio_hex = data["data"]["audio"]
                audio_bytes = bytes.fromhex(audio_hex)
                
                today_dir = get_today_dir("music")
                file_path = today_dir / f"{run_id}.mp3"
                file_path.write_bytes(audio_bytes)
                
                # 保存提示词
                prompt_path = today_dir / f"{run_id}.prompt.txt"
                prompt_path.write_text(prompt, encoding="utf-8")
                
                duration = time.time() - start_time
                return TestResult(
                    test_type="music",
                    model="music-2.6",
                    prompt=prompt,
                    status="success",
                    file_path=str(file_path.relative_to(WORKS_DIR)),
                    file_size_bytes=len(audio_bytes),
                    duration_seconds=round(duration, 2),
                    timestamp=datetime.now().isoformat(),
                    api_response_raw={k: v for k, v in data.items() if k != "data"}
                )
            else:
                raise Exception("No audio data in response")
                
    except Exception as e:
        duration = time.time() - start_time
        return TestResult(
            test_type="music",
            model="music-2.6",
            prompt=prompt,
            status="error",
            duration_seconds=round(duration, 2),
            error_message=str(e),
            timestamp=datetime.now().isoformat()
        )


async def test_video_generation(prompt: str) -> TestResult:
    """测试视频生成"""
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            # 提交视频生成任务
            response = await client.post(
                f"{MINIMAX_BASE_URL}/v1/video_generation",
                headers={"Authorization": f"Bearer {MINIMAX_API_KEY}"},
                json={
                    "model": "MiniMax-Hailuo-2.3",
                    "prompt": prompt,
                    "duration": 6
                }
            )
            response.raise_for_status()
            data = response.json()
            
            duration = time.time() - start_time
            
            if data.get("task_id"):
                return TestResult(
                    test_type="video",
                    model="MiniMax-Hailuo-2.3",
                    prompt=prompt,
                    status="success",
                    duration_seconds=round(duration, 2),
                    timestamp=datetime.now().isoformat(),
                    api_response_raw=data
                )
            else:
                raise Exception(f"No task_id in response: {data}")
                
    except Exception as e:
        duration = time.time() - start_time
        return TestResult(
            test_type="video",
            model="MiniMax-Hailuo-2.3",
            prompt=prompt,
            status="error",
            duration_seconds=round(duration, 2),
            error_message=str(e),
            timestamp=datetime.now().isoformat()
        )


async def test_tts_generation(text: str) -> TestResult:
    """测试语音合成"""
    start_time = time.time()
    run_id = str(uuid.uuid4())[:8]
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{MINIMAX_BASE_URL}/v1/t2a_v2",
                headers={"Authorization": f"Bearer {MINIMAX_API_KEY}"},
                json={
                    "model": "speech-01-turbo",
                    "text": text,
                    "voice_setting": {
                        "voice_id": "male-qn-qingse",
                        "speed": 1.0
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # 保存音频文件
            if data.get("data", {}).get("audio"):
                audio_hex = data["data"]["audio"]
                audio_bytes = bytes.fromhex(audio_hex)
                
                today_dir = get_today_dir("tts")
                file_path = today_dir / f"{run_id}.mp3"
                file_path.write_bytes(audio_bytes)
                
                duration = time.time() - start_time
                return TestResult(
                    test_type="tts",
                    model="speech-02",
                    prompt=text,
                    status="success",
                    file_path=str(file_path.relative_to(WORKS_DIR)),
                    file_size_bytes=len(audio_bytes),
                    duration_seconds=round(duration, 2),
                    timestamp=datetime.now().isoformat(),
                    api_response_raw={k: v for k, v in data.items() if k != "data"}
                )
            else:
                raise Exception("No audio data in response")
                
    except Exception as e:
        duration = time.time() - start_time
        return TestResult(
            test_type="tts",
            model="speech-02",
            prompt=text,
            status="error",
            duration_seconds=round(duration, 2),
            error_message=str(e),
            timestamp=datetime.now().isoformat()
        )


async def test_text_generation(prompt: str) -> TestResult:
    """测试文本生成（M2.7）"""
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{MINIMAX_BASE_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {MINIMAX_API_KEY}"},
                json={
                    "model": "MiniMax-M2.7",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500
                }
            )
            response.raise_for_status()
            data = response.json()
            
            duration = time.time() - start_time
            
            # 提取使用量
            usage = data.get("usage", {})
            
            return TestResult(
                test_type="text",
                model="MiniMax-M2.7",
                prompt=prompt,
                status="success",
                duration_seconds=round(duration, 2),
                timestamp=datetime.now().isoformat(),
                api_response_raw={
                    "usage": usage,
                    "model": data.get("model"),
                    "finish_reason": data.get("choices", [{}])[0].get("finish_reason")
                }
            )
                
    except Exception as e:
        duration = time.time() - start_time
        return TestResult(
            test_type="text",
            model="MiniMax-M2.7",
            prompt=prompt,
            status="error",
            duration_seconds=round(duration, 2),
            error_message=str(e),
            timestamp=datetime.now().isoformat()
        )


@router.post("/run-all", response_model=TestResponse)
async def run_all_tests():
    """运行所有类型的测试"""
    results = []
    
    # 测试提示词
    test_prompts = {
        "image": "A cute cat sitting on a windowsill, watching the sunset, warm colors",
        "music": "Peaceful ambient music, relaxing and calm, piano and strings",
        "video": "A cat walking slowly across a sunny garden",
        "tts": "你好，这是一段测试语音，用于检查 MiniMax 的语音合成功能。",
        "text": "用一句话描述今天的天气。"
    }
    
    # 依次执行测试
    results.append(await test_image_generation(test_prompts["image"]))
    results.append(await test_music_generation(test_prompts["music"]))
    results.append(await test_video_generation(test_prompts["video"]))
    results.append(await test_tts_generation(test_prompts["tts"]))
    results.append(await test_text_generation(test_prompts["text"]))
    
    # 统计
    success_count = sum(1 for r in results if r.status == "success")
    error_count = sum(1 for r in results if r.status == "error")
    
    return TestResponse(
        results=results,
        summary={
            "total": len(results),
            "success": success_count,
            "error": error_count,
            "timestamp": datetime.now().isoformat()
        }
    )


@router.post("/run-single/{test_type}", response_model=TestResult)
async def run_single_test(test_type: str, prompt: Optional[str] = None):
    """运行单个类型的测试"""
    default_prompts = {
        "image": "A beautiful sunset over mountains",
        "music": "Upbeat electronic dance music",
        "video": "Waves crashing on a beach",
        "tts": "这是一段测试语音。",
        "text": "你好"
    }
    
    test_prompt = prompt or default_prompts.get(test_type, "Test")
    
    if test_type == "image":
        return await test_image_generation(test_prompt)
    elif test_type == "music":
        return await test_music_generation(test_prompt)
    elif test_type == "video":
        return await test_video_generation(test_prompt)
    elif test_type == "tts":
        return await test_tts_generation(test_prompt)
    elif test_type == "text":
        return await test_text_generation(test_prompt)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown test type: {test_type}")


@router.get("/history")
async def get_test_history():
    """获取测试历史（从本地 JSON 文件读取）"""
    history_file = WORKS_DIR / "quota_test_history.json"
    if history_file.exists():
        import json
        return json.loads(history_file.read_text(encoding="utf-8"))
    return {"tests": []}


@router.post("/save-history")
async def save_test_history(data: dict):
    """保存测试历史和用户输入的实际消耗"""
    import json
    history_file = WORKS_DIR / "quota_test_history.json"
    
    # 读取现有历史
    history = {"tests": []}
    if history_file.exists():
        history = json.loads(history_file.read_text(encoding="utf-8"))
    
    # 添加新记录
    history["tests"].append({
        **data,
        "saved_at": datetime.now().isoformat()
    })
    
    # 保存
    history_file.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    
    return {"status": "ok", "total_records": len(history["tests"])}
