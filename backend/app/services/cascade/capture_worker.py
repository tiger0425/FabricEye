"""
FabricEye 级联检测引擎 - 采集工作线程
视频帧采集和录制。
"""

import threading
import time
from typing import Optional

import cv2

from app.services.cascade.video_writer import AsyncVideoWriter


class CaptureWorker:
    """视频采集工作线程。"""
    
    def __init__(self, video_service, frame_buffer):
        self.video_service = video_service
        self.frame_buffer = frame_buffer
        self.video_writer: Optional[AsyncVideoWriter] = None
        self.video_path: Optional[str] = None
        self._frame_index = 0
        self._thread: Optional[threading.Thread] = None
        self._is_running = False
    
    def start(self, video_path: str) -> None:
        """启动采集线程。"""
        self.video_path = video_path
        self._is_running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"--- THREAD START: Capture Loop ---", flush=True)
    
    def stop(self) -> None:
        """停止采集线程。"""
        self._is_running = False
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
    
    def _run(self) -> None:
        """采集循环。"""
        while self._is_running:
            try:
                frame = self.video_service.get_frame()
                if frame is not None:
                    self._process_frame(frame)
            except Exception as e:
                print(f"Capture error: {e}", flush=True)
            time.sleep(0.01)
    
    def _process_frame(self, frame) -> None:
        """处理单帧。"""
        # 初始化VideoWriter
        if self.video_writer is None and self.video_path:
            self._init_video_writer(frame)
        
        # 写入视频
        if self.video_writer:
            self.video_writer.write(frame)
        
        # 添加到缓冲区
        self.frame_buffer.append((self._frame_index, frame))
        self._frame_index += 1
    
    def _init_video_writer(self, frame) -> None:
        """初始化视频写入器。"""
        h, w = frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        self.video_writer = AsyncVideoWriter(self.video_path, fourcc, 25.0, (w, h))
        
        if not self.video_writer.writer.isOpened():
            self.video_writer.release()
            self.video_writer = AsyncVideoWriter(
                self.video_path,
                cv2.VideoWriter_fourcc(*'mp4v'),
                25.0, (w, h)
            )
    
    @property
    def frame_index(self) -> int:
        return self._frame_index
