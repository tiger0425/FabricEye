"""
FabricEye 级联检测引擎 - 主引擎
Flash + Plus 双阶段检测流水线调度器。
"""

import queue
import threading
import time
import asyncio
import os
from typing import Dict
from datetime import datetime

from app.core.config import settings
from app.services.video_capture import VideoCaptureService
from app.services.ai_analyzer import AIAnalyzerService
from app.core.database import SessionLocal
from app.models.video import Video, VideoStatus
from app.services.cascade.types import PendingDefect
from app.services.cascade.deduplicator import DetectionDeduplicator
from app.services.cascade.capture_worker import CaptureWorker
from app.services.cascade.flash_worker import FlashWorker
from app.services.cascade.plus_worker import PlusWorker


class CascadeEngine:
    """级联检测引擎主控制器。"""
    
    def __init__(self, roll_id: int):
        self.roll_id = roll_id
        self.video_service = VideoCaptureService()
        self.analyzer = AIAnalyzerService()
        
        # 共享状态
        from collections import deque
        self.frame_buffer = deque(maxlen=settings.FRAME_BUFFER_SIZE)
        self.verification_queue = queue.Queue(maxsize=settings.VERIFICATION_QUEUE_SIZE)
        self._pending_lock = threading.Lock()
        self.pending_defects: Dict[int, PendingDefect] = {}
        self.deduplicator = DetectionDeduplicator(
            settings.DEDUP_IOU_THRESHOLD,
            settings.DEDUP_TIME_WINDOW
        )
        
        # 工作线程
        self._capture_worker = CaptureWorker(self.video_service, self.frame_buffer)
        self._flash_worker = FlashWorker(
            self.frame_buffer, self.verification_queue,
            self.pending_defects, self._pending_lock, self.deduplicator
        )
        self._plus_worker = PlusWorker(
            self.verification_queue, self.pending_defects,
            self._pending_lock, self.roll_id
        )
        
        # 状态
        self.is_running = False
        self.video_path = None
        self.video_id = None
        self.recording_start_time = None

    async def start(self) -> bool:
        """启动引擎。"""
        if self.is_running:
            return True
        if not self.video_service.start_capture():
            return False
        
        self.analyzer.load_model()
        self.is_running = True
        
        await self._init_video_recording()
        
        self._capture_worker.start(self.video_path)
        self._flash_worker.start(self.analyzer)
        self._plus_worker.start(self.analyzer, self.video_id, self.recording_start_time)
        
        print(f"--- CascadeEngine started for roll {self.roll_id} ---", flush=True)
        return True

    def stop(self) -> None:
        """停止引擎。"""
        self.is_running = False
        self._capture_worker.stop()
        self._flash_worker.stop()
        self._plus_worker.stop()
        
        if self.video_id:
            try:
                loop = asyncio.get_event_loop()
                asyncio.run_coroutine_threadsafe(self._save_video_info(), loop)
            except:
                pass
        
        print(f"--- CascadeEngine stopping for roll {self.roll_id} ---", flush=True)

    async def _init_video_recording(self):
        """初始化视频录制。"""
        timestamp = int(time.time())
        video_dir = "storage/videos"
        os.makedirs(video_dir, exist_ok=True)
        self.video_path = os.path.join(video_dir, f"roll_{self.roll_id}_{timestamp}.mp4")
        self.recording_start_time = time.time()
        
        async with SessionLocal() as session:
            v = Video(
                roll_id=self.roll_id,
                file_path=self.video_path,
                status=VideoStatus.RECORDING,
                started_at=datetime.utcnow()
            )
            session.add(v)
            await session.commit()
            await session.refresh(v)
            self.video_id = v.id

    async def _save_video_info(self):
        """保存视频元数据。"""
        if not self.video_id:
            return
        
        duration = time.time() - self.recording_start_time if self.recording_start_time else 0
        file_size = os.path.getsize(self.video_path) if self.video_path and os.path.exists(self.video_path) else 0
        
        async with SessionLocal() as session:
            from sqlalchemy import select
            res = await session.execute(select(Video).where(Video.id == self.video_id))
            v = res.scalar_one_or_none()
            if v:
                v.status = VideoStatus.COMPLETED
                v.duration_seconds = duration
                v.file_size = file_size
                v.completed_at = datetime.utcnow()
                await session.commit()

    def get_status(self) -> dict:
        """获取引擎状态。"""
        with self._pending_lock:
            p = sum(1 for d in self.pending_defects.values() if d.status == "pending")
            c = sum(1 for d in self.pending_defects.values() if d.status == "confirmed")
            r = sum(1 for d in self.pending_defects.values() if d.status == "rejected")
            e = sum(1 for d in self.pending_defects.values() if d.status == "expired")
        
        return {
            "is_running": self.is_running,
            "roll_id": self.roll_id,
            "buffer_size": len(self.frame_buffer),
            "buffer_capacity": settings.FRAME_BUFFER_SIZE,
            "verification_queue_size": self.verification_queue.qsize(),
            "pending_count": p,
            "confirmed_count": c,
            "rejected_count": r,
            "expired_count": e,
            "total_frames_captured": self._capture_worker.frame_index if self._capture_worker else 0,
            "cascade_id_counter": self._flash_worker._cascade_id_counter if self._flash_worker else 0,
            "video_id": self.video_id
        }
