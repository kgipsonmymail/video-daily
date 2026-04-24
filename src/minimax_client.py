"""MiniMax API 客户端"""

import time
import requests
from typing import Optional
from .config import API_BASE_URL, get_api_key


class MiniMaxClient:
    """MiniMax API 客户端封装"""

    def __init__(self) -> None:
        self.api_key = get_api_key()
        self.base_url = API_BASE_URL

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_video_task(
        self,
        model: str,
        prompt: str,
        duration: int = 6,
        resolution: str = "768P",
        first_frame_image: Optional[str] = None,
        last_frame_image: Optional[str] = None,
        subject_reference: Optional[list] = None,
    ) -> str:
        """创建视频生成任务，返回 task_id"""
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
        }
        if first_frame_image:
            payload["first_frame_image"] = first_frame_image
        if last_frame_image:
            payload["last_frame_image"] = last_frame_image
        if subject_reference:
            payload["subject_reference"] = subject_reference

        resp = requests.post(
            f"{self.base_url}/v1/video_generation",
            headers=self._headers(),
            json=payload
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("base_resp", {}).get("status_code") != 0:
            raise Exception(f"API error: {data}")
        return data["task_id"]

    def query_video_task(self, task_id: str) -> dict:
        """查询视频生成任务状态"""
        resp = requests.get(
            f"{self.base_url}/v1/query/video_generation",
            headers=self._headers(),
            params={"task_id": task_id}
        )
        resp.raise_for_status()
        return resp.json()

    def get_file_download_url(self, file_id: str) -> str:
        """获取文件下载链接"""
        resp = requests.get(
            f"{self.base_url}/v1/files/retrieve",
            headers=self._headers(),
            params={"file_id": file_id}
        )
        resp.raise_for_status()
        data = resp.json()
        return data["file"]["download_url"]

    def wait_for_task(
        self,
        task_id: str,
        poll_interval: int = 5,
        timeout: int = 300
    ) -> dict:
        """等待任务完成（轮询）"""
        start_time = time.time()
        while True:
            result = self.query_video_task(task_id)
            status = result.get("status")
            if status == "Success":
                return result
            if status == "Fail":
                raise Exception(f"Task failed: {result}")
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Task timeout after {timeout}s")
            time.sleep(poll_interval)

    def create_image_task(
        self,
        model: str,
        prompt: str,
        aspect_ratio: str = "16:9",
        n: int = 1,
        response_format: str = "url",
    ) -> dict:
        """创建图片生成任务"""
        payload = {
            "model": model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "n": n,
            "response_format": response_format,
        }
        resp = requests.post(
            f"{self.base_url}/v1/image_generation",
            headers=self._headers(),
            json=payload
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("base_resp", {}).get("status_code") != 0:
            raise Exception(f"API error: {data}")
        return data