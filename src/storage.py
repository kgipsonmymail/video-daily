"""存储管理 - 规范化素材存储结构"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from enum import Enum


class MediaType(Enum):
    IMAGE = "image"
    VIDEO = "video"


class TaskType(Enum):
    T2V = "text-to-video"       # 文生视频
    I2V = "image-to-video"      # 图生视频
    FL2V = "first-last-video"  # 首尾帧视频
    S2V = "subject-video"      # 主体参考视频
    T2I = "text-to-image"      # 文生图
    I2I = "image-to-image"     # 图生图


@dataclass
class MediaMetadata:
    """素材元数据"""
    filename: str              # 文件名
    media_type: str            # image/video
    task_type: str             # 任务类型
    task_id: str               # API task_id
    prompt: str                # 使用的 prompt
    model: str                 # 使用的模型
    resolution: Optional[str] = None   # 分辨率
    duration: Optional[int] = None     # 时长(秒)，视频专属
    aspect_ratio: Optional[str] = None # 宽高比，图片专属
    source_url: Optional[str] = None   # 下载 URL
    file_size: Optional[int] = None    # 文件大小(bytes)
    sha256: Optional[str] = None        # 文件 SHA256 哈希
    created_at: Optional[str] = None   # 创建时间 ISO 格式
    local_path: Optional[str] = None   # 本地相对路径
    thumbnail: Optional[str] = None    # 缩略图路径(预留)
    tags: list = None                  # 自定义标签
    notes: str = ""                    # 备注

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class StorageManager:
    """
    规范化存储管理器
    
    目录结构:
    works/
    ├── YYYY-MM-DD/
    │   ├── images/
    │   │   ├── YYYY-MM-DD_HH-MM-SS_[task_type]_[prompt_hash].png
    │   │   └── metadata/
    │   │       └── YYYY-MM-DD_HH-MM-SS_[task_type]_[prompt_hash].json
    │   ├── videos/
    │   │   ├── YYYY-MM-DD_HH-MM-SS_[task_type]_[prompt_hash].mp4
    │   │   └── metadata/
    │   │       └── YYYY-MM-DD_HH-MM-SS_[task_type]_[prompt_hash].json
    │   └── source/           # 源文件/参考图
    ├── index.json            # 全局索引
    └── archive/              # 归档旧素材
    """

    def __init__(self, works_dir: Path):
        self.works_dir = Path(works_dir)
        self.today = datetime.now().strftime("%Y-%m-%d")
        self._ensure_base_dirs()

    def _ensure_base_dirs(self) -> None:
        """确保基础目录结构存在"""
        today_dir = self.works_dir / self.today
        today_dir.joinpath("images", "metadata").mkdir(parents=True, exist_ok=True)
        today_dir.joinpath("videos", "metadata").mkdir(parents=True, exist_ok=True)
        today_dir.joinpath("source").mkdir(parents=True, exist_ok=True)
        self.works_dir.joinpath("archive").mkdir(parents=True, exist_ok=True)
        
    def _generate_basename(self, task_type: TaskType, prompt: str, timestamp: datetime = None) -> str:
        """生成规范化文件名"""
        if timestamp is None:
            timestamp = datetime.now()
        ts = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        # 用 prompt 的哈希值确保唯一性，避免文件名冲突
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        return f"{ts}_{task_type.value}_{prompt_hash}"

    def _get_media_dir(self, media_type: MediaType) -> Path:
        """获取媒体类型目录"""
        return self.works_dir / self.today / (media_type.value + "s")

    def _get_metadata_dir(self, media_type: MediaType) -> Path:
        """获取元数据目录"""
        return self.works_dir / self.today / media_type.value + "s" / "metadata"

    def _save_metadata(self, metadata: MediaMetadata, media_type: MediaType) -> Path:
        """保存元数据 JSON"""
        metadata_dir = self._get_metadata_dir(media_type)
        metadata_path = metadata_dir / f"{metadata.filename}.json"
        
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(asdict(metadata), f, ensure_ascii=False, indent=2)
        
        return metadata_path

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件 SHA256 哈希"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def save_image(
        self,
        source_url: str,
        prompt: str,
        model: str = "image-01",
        aspect_ratio: str = "16:9",
        task_id: str = "",
        tags: list = None,
        notes: str = ""
    ) -> tuple[Path, Path]:
        """
        保存图片及元数据
        
        Returns: (file_path, metadata_path)
        """
        timestamp = datetime.now()
        basename = self._generate_basename(TaskType.T2I, prompt, timestamp)
        
        # 确定扩展名（默认 png）
        ext = ".png"
        if source_url and ".jpg" in source_url.lower():
            ext = ".jpg"
        elif source_url and ".jpeg" in source_url.lower():
            ext = ".jpeg"
        elif source_url and ".webp" in source_url.lower():
            ext = ".webp"
            
        filename = basename + ext
        media_dir = self._get_media_dir(MediaType.IMAGE)
        file_path = media_dir / filename
        
        # 下载文件
        import urllib.request
        urllib.request.urlretrieve(source_url, file_path)
        
        # 计算文件大小和哈希
        file_size = file_path.stat().st_size
        file_hash = self._calculate_file_hash(file_path)
        
        # 构建元数据
        metadata = MediaMetadata(
            filename=filename,
            media_type=MediaType.IMAGE.value,
            task_type=TaskType.T2I.value,
            task_id=task_id,
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            source_url=source_url,
            file_size=file_size,
            sha256=file_hash,
            created_at=timestamp.isoformat(),
            local_path=str(file_path.relative_to(self.works_dir)),
            tags=tags or [],
            notes=notes
        )
        
        metadata_path = self._save_metadata(metadata, MediaType.IMAGE)
        
        # 更新全局索引
        self._update_index(metadata)
        
        return file_path, metadata_path

    def save_video(
        self,
        source_url: str,
        prompt: str,
        task_type: TaskType,
        model: str = "MiniMax-Hailuo-2.3",
        resolution: str = "768P",
        duration: int = 6,
        task_id: str = "",
        tags: list = None,
        notes: str = ""
    ) -> tuple[Path, Path]:
        """
        保存视频及元数据
        
        Returns: (file_path, metadata_path)
        """
        timestamp = datetime.now()
        basename = self._generate_basename(task_type, prompt, timestamp)
        filename = basename + ".mp4"
        
        media_dir = self._get_media_dir(MediaType.VIDEO)
        file_path = media_dir / filename
        
        # 下载文件
        import urllib.request
        urllib.request.urlretrieve(source_url, file_path)
        
        # 计算文件大小和哈希
        file_size = file_path.stat().st_size
        file_hash = self._calculate_file_hash(file_path)
        
        # 构建元数据
        metadata = MediaMetadata(
            filename=filename,
            media_type=MediaType.VIDEO.value,
            task_type=task_type.value,
            task_id=task_id,
            prompt=prompt,
            model=model,
            resolution=resolution,
            duration=duration,
            source_url=source_url,
            file_size=file_size,
            sha256=file_hash,
            created_at=timestamp.isoformat(),
            local_path=str(file_path.relative_to(self.works_dir)),
            tags=tags or [],
            notes=notes
        )
        
        metadata_path = self._save_metadata(metadata, MediaType.VIDEO)
        
        # 更新全局索引
        self._update_index(metadata)
        
        return file_path, metadata_path

    def _get_index_path(self) -> Path:
        """获取全局索引文件路径"""
        return self.works_dir / "index.json"

    def _update_index(self, metadata: MediaMetadata) -> None:
        """更新全局索引"""
        index_path = self._get_index_path()
        
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
        else:
            index_data = {"items": [], "last_updated": None}
        
        # 检查是否已存在（通过 task_id）
        existing = False
        for i, item in enumerate(index_data["items"]):
            if item.get("task_id") == metadata.task_id and metadata.task_id:
                index_data["items"][i] = asdict(metadata)
                existing = True
                break
        
        if not existing:
            index_data["items"].append(asdict(metadata))
        
        index_data["last_updated"] = datetime.now().isoformat()
        
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

    def get_index(self) -> dict:
        """获取全局索引"""
        index_path = self._get_index_path()
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"items": [], "last_updated": None}

    def list_by_date(self, date: str = None) -> dict:
        """列出指定日期的所有素材"""
        if date is None:
            date = self.today
        
        date_dir = self.works_dir / date
        if not date_dir.exists():
            return {"images": [], "videos": []}
        
        result = {"images": [], "videos": []}
        
        # 读取图片元数据
        img_meta_dir = date_dir / "images" / "metadata"
        if img_meta_dir.exists():
            for meta_file in img_meta_dir.glob("*.json"):
                with open(meta_file, "r", encoding="utf-8") as f:
                    result["images"].append(json.load(f))
        
        # 读取视频元数据
        vid_meta_dir = date_dir / "videos" / "metadata"
        if vid_meta_dir.exists():
            for meta_file in vid_meta_dir.glob("*.json"):
                with open(meta_file, "r", encoding="utf-8") as f:
                    result["videos"].append(json.load(f))
        
        return result

    def list_all(self, media_type: MediaType = None) -> list:
        """列出所有素材索引"""
        index = self.get_index()
        items = index.get("items", [])
        
        if media_type:
            items = [i for i in items if i.get("media_type") == media_type.value]
        
        return items

    def get_stats(self) -> dict:
        """获取统计信息"""
        index = self.get_index()
        items = index.get("items", [])
        
        stats = {
            "total": len(items),
            "images": len([i for i in items if i.get("media_type") == "image"]),
            "videos": len([i for i in items if i.get("media_type") == "video"]),
            "total_size": sum(i.get("file_size", 0) for i in items),
            "last_updated": index.get("last_updated")
        }
        
        return stats


# 便捷函数
def get_storage() -> StorageManager:
    """获取存储管理器实例"""
    from .config import WORKS_DIR
    return StorageManager(WORKS_DIR)
