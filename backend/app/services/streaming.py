import threading
import queue
import time
import logging
from typing import Optional, Callable
from app.services.video_capture import VideoCaptureService
from app.services.ai_analyzer import AIAnalyzerService
from app.routers.websocket import manager
import asyncio

logger = logging.getLogger(__name__)

class StreamingEngine:
    """
    流式处理引擎类
    协调视频采集、录制和 AI 分析。
    """
    def __init__(self, roll_id: int):
        self.roll_id = roll_id
        self.video_service = VideoCaptureService()
        self.analyzer = AIAnalyzerService()
        self.frame_queue = queue.Queue(maxsize=30)
        self.is_running = False
        
        self.recording_thread: Optional[threading.Thread] = None
        self.analysis_thread: Optional[threading.Thread] = None

    def start_engine(self) -> bool:
        if self.is_running:
            return True
            
        if not self.video_service.start_capture():
            return False
            
        self.analyzer.load_model()
        self.is_running = True
        
        self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        
        self.recording_thread.start()
        self.analysis_thread.start()
        
        logger.info(f"Streaming Engine started for roll {self.roll_id}")
        return True

    def stop_engine(self) -> None:
        self.is_running = False
        if self.recording_thread:
            self.recording_thread.join(timeout=2)
        if self.analysis_thread:
            self.analysis_thread.join(timeout=2)
        self.video_service.stop_capture()
        logger.info(f"Streaming Engine stopped for roll {self.roll_id}")

    def _recording_loop(self) -> None:
        while self.is_running:
            frame = self.video_service.get_frame()
            if frame is not None:
                try:
                    # 将帧入队供分析，如果不满则放入
                    if not self.frame_queue.full():
                        self.frame_queue.put(frame)
                except Exception as e:
                    logger.error(f"Error in recording loop: {e}")
            time.sleep(0.01) # 限制采样频率

    def _analysis_loop(self) -> None:
        # 创建新的事件循环以在线程中运行异步 WebSocket 推送
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self.is_running:
            try:
                # 从队列获取帧，超时 1 秒
                frame = self.frame_queue.get(timeout=1)
                defects = self.analyzer.analyze_frame(frame)
                
                if defects:
                    for defect in defects:
                        # 补充 roll_id
                        defect['rollId'] = self.roll_id
                        # 推送到 WebSocket
                        loop.run_until_complete(manager.broadcast(defect))
                        logger.info(f"Defect detected and broadcasted: {defect['type']}")
                
                self.frame_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in analysis loop: {e}")
            
            time.sleep(0.1) # 模拟 AI 处理间隔
