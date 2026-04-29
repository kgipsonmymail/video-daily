"""克隆音色并生成演讲音频"""

import time
import requests
from src.config import get_api_key, API_BASE_URL

API_KEY = get_api_key()
BASE_URL = API_BASE_URL

def headers(json=True):
    if json:
        return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    return {"Authorization": f"Bearer {API_KEY}"}

AUDIO_PATH = r"C:\Users\Sunny\Documents\010工作台\program\claudecode\video-daily\ref\api\voice\音色-wind.mp3"
SCRIPT_PATH = r"C:\Users\Sunny\Documents\010工作台\program\claudecode\video-daily\ref\api\voice\讲稿.txt"
OUTPUT_PATH = r"C:\Users\Sunny\Documents\010工作台\program\claudecode\video-daily\ref\api\voice\wind演讲.mp3"

# ============================================================
# Step 1: 上传待复刻音频 (purpose=voice_clone)
# ============================================================
print("[Step 1] 上传复刻音频...")
with open(AUDIO_PATH, "rb") as f:
    files = {"file": ("音色-wind.mp3", f, "audio/mpeg")}
    data = {"purpose": "voice_clone"}
    resp = requests.post(
        f"{BASE_URL}/v1/files/upload",
        headers=headers(json=False),
        data=data,
        files=files
    )
resp.raise_for_status()
result = resp.json()
print("上传结果:", result)

if result.get("base_resp", {}).get("status_code") != 0:
    raise Exception(f"上传失败: {result}")

file_id = result["file"]["file_id"]
print(f"file_id: {file_id}")

# ============================================================
# Step 2: 克隆音色
# ============================================================
print("\n[Step 2] 克隆音色...")
payload = {
    "file_id": file_id,
    "voice_id": "wind_voice_001",
    "model": "speech-2.8-hd",
}
resp = requests.post(
    f"{BASE_URL}/v1/voice_clone",
    headers=headers(json=True),
    json=payload
)
resp.raise_for_status()
clone_result = resp.json()
print("克隆结果:", clone_result)

if clone_result.get("base_resp", {}).get("status_code") != 0:
    raise Exception(f"克隆失败: {clone_result}")

demo_audio = clone_result.get("demo_audio", "")
if demo_audio:
    print(f"试听地址: {demo_audio}")

# ============================================================
# Step 3: 读取讲稿
# ============================================================
print("\n[Step 3] 读取讲稿...")
with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
    script = f.read().strip()
print(f"讲稿长度: {len(script)} 字符")
print(f"讲稿预览: {script[:80]}...")

# ============================================================
# Step 4: 用克隆的音色生成 T2S 音频
# ============================================================
print("\n[Step 4] 创建语音合成任务...")
payload = {
    "model": "speech-2.8-hd",
    "text": script,
    "voice_setting": {
        "voice_id": "wind_voice_001",
        "speed": 1.0,
        "vol": 1.0,
        "pitch": 0,
    },
    "audio_setting": {
        "audio_sample_rate": 32000,
        "bitrate": 128000,
        "format": "mp3",
        "channel": 1,
    },
}
resp = requests.post(
    f"{BASE_URL}/v1/t2a_async_v2",
    headers=headers(json=True),
    json=payload
)
resp.raise_for_status()
t2a_result = resp.json()
print("T2S 创建结果:", t2a_result)

if t2a_result.get("base_resp", {}).get("status_code") != 0:
    raise Exception(f"T2S 创建失败: {t2a_result}")

task_id = t2a_result["task_id"]
file_id_output = t2a_result["file_id"]
print(f"task_id: {task_id}, file_id: {file_id_output}")

# ============================================================
# Step 5: 轮询等待任务完成
# ============================================================
print("\n[Step 5] 等待任务完成（轮询中）...")
for i in range(60):  # 最多等5分钟
    time.sleep(5)
    resp = requests.get(
        f"{BASE_URL}/v1/t2a_async_v2",
        headers=headers(json=False),
        params={"task_id": task_id}
    )
    resp.raise_for_status()
    status_result = resp.json()
    status = status_result.get("status", "Pending")
    print(f"  [{i+1}] status = {status}")
    if status == "Success":
        print("任务成功完成!")
        break
    elif status == "Fail":
        raise Exception(f"任务失败: {status_result}")
else:
    raise TimeoutError("任务超时（5分钟）")

# ============================================================
# Step 6: 下载音频
# ============================================================
print("\n[Step 6] 获取下载链接...")
resp = requests.get(
    f"{BASE_URL}/v1/files/retrieve",
    headers=headers(json=False),
    params={"file_id": file_id_output}
)
resp.raise_for_status()
download_result = resp.json()
print("下载响应:", download_result)

download_url = download_result.get("file", {}).get("download_url", "")
if not download_url:
    print("警告: 未返回下载链接，响应如下:")
    print(download_result)
else:
    print(f"下载链接: {download_url}")

    # 下载并保存
    audio_resp = requests.get(download_url)
    audio_resp.raise_for_status()
    with open(OUTPUT_PATH, "wb") as f:
        f.write(audio_resp.content)
    print(f"\n音频已保存至: {OUTPUT_PATH}")
    print(f"文件大小: {len(audio_resp.content) / 1024 / 1024:.2f} MB")
