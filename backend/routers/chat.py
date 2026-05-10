"""
文本对话路由 /api/chat
调用 MiniMax Anthropic 兼容 API，生成对话回复
"""

import os
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

API_BASE_URL = "https://api.minimaxi.com"
router = APIRouter()


class HistoryMsg(BaseModel):
    role: str   # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    text: str
    voice_id: str = "Chinese (Mandarin)_Sweet_Lady"
    prompt: str = "你是一个温柔体贴的对话伙伴，友善地回应每一句话。"
    model: str = "MiniMax-M2.7"
    history: list[HistoryMsg] = []     # 最近 N 轮对话历史


class ChatResponse(BaseModel):
    text: str
    trace_id: str = ""


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest):
    api_key = os.getenv("MINIMAX_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="MINIMAX_API_KEY 未设置")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.text})

    payload = {
        "model": req.model,
        "stream": False,
        "system": req.prompt,
        "messages": messages,
    }

    try:
        resp = requests.post(
            f"{API_BASE_URL}/anthropic/v1/messages",
            headers=headers,
            json=payload,
            timeout=60,
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"请求失败: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=f"API错误: {resp.text[:200]}")

    result = resp.json()

    # 提取 assistant 回复文本
    reply_text = ""
    trace_id = result.get("id", "")

    content_blocks = result.get("content", [])
    if isinstance(content_blocks, list):
        for block in content_blocks:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    reply_text = block.get("text", "")
                    break
                # 跳过 thinking 块
                elif block.get("type") == "thinking":
                    continue

    if not reply_text:
        # 兜底：返回用户原文
        reply_text = req.text

    return ChatResponse(text=reply_text, trace_id=trace_id)