"""
FabricEye 级联检测引擎 - Flash检测工作线程
快速初筛检测流程。
"""

import threading
import time
import asyncio
import queue
from typing import Dict

import numpy as np
import cv2

from app.core.config import settings
from app.services.cascade.types import PendingDefect
from app.services.cascade.deduplicator import DetectionDeduplicator
from app.services.cascade.image_processor import get_vlm_roi
from app.services.cascade.bbox_utils import location_to_bbox, is_valid_location


class FlashWorker:
    """Flash检测工作线程（快速初筛）。"""
    
    def __init__(
        self,
        frame_buffer,
        verification_queue: queue.Queue,
        pending_defects: Dict[int, PendingDefect],
        pending_lock: threading.Lock,
        deduplicator: DetectionDeduplicator
    ):
        self.frame_buffer = frame_buffer
        self.verification_queue = verification_queue
        self.pending_defects = pending_defects
        self.pending_lock = pending_lock
        self.deduplicator = deduplicator
        self.analyzer = None  # 由engine设置
        self._cascade_id_counter = 0
        self._thread: threading.Thread = None
        self._is_running = False
    
    def start(self, analyzer) -> None:
        """启动Flash检测线程。"""
        self.analyzer = analyzer
        self._is_running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("--- THREAD START: Flash Loop ---", flush=True)
    
    def stop(self) -> None:
        """停止Flash检测线程。"""
        self._is_running = False
    
    def get_next_cascade_id(self) -> int:
        """获取下一个级联ID。"""
        with self.pending_lock:
            self._cascade_id_counter += 1
            return self._cascade_id_counter
    
    def _run(self) -> None:
        """Flash检测循环。"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self._is_running:
            try:
                self._process_frame()
            except Exception as e:
                print(f"Flash error: {e}", flush=True)
            time.sleep(settings.ANALYSIS_INTERVAL)
        
        loop.close()
    
    def _process_frame(self) -> None:
        """处理单帧检测。"""
        if not self.frame_buffer:
            time.sleep(0.1)
            return
        
        _, frame = self.frame_buffer[-1]
        detections = self.analyzer.analyze_with_flash(frame)
        now = time.time()
        
        for det in detections:
            self._process_detection(det, frame, now)
    
    def _process_detection(self, det: dict, frame: np.ndarray, now: float) -> None:
        """处理单个检测结果。"""
        confidence = det.get("confidence", 0.0)
        if confidence < settings.CASCADE_FLASH_THRESHOLD:
            return
        
        location = det.get("location", [0, 0, 0, 0])
        
        if is_valid_location(location):
            bbox = location_to_bbox(location, frame.shape[1], frame.shape[0])
            if self.deduplicator.is_duplicate(bbox, now):
                return
            roi_crop = get_vlm_roi(frame, bbox)
        else:
            bbox = (0, 0, frame.shape[1], frame.shape[0])
            roi_crop = self._create_full_frame_roi(frame)
        
        self._create_pending_defect(det, bbox, roi_crop, now, confidence)
    
    def _create_full_frame_roi(self, frame: np.ndarray) -> np.ndarray:
        """创建全帧ROI。"""
        scale = 512 / max(frame.shape[0], frame.shape[1])
        resized = cv2.resize(frame, None, fx=scale, fy=scale)
        canvas = np.zeros((512, 512, 3), dtype=np.uint8)
        y_offset = (512 - resized.shape[0]) // 2
        x_offset = (512 - resized.shape[1]) // 2
        canvas[y_offset:y_offset+resized.shape[0], x_offset:x_offset+resized.shape[1]] = resized
        return canvas
    
    def _create_pending_defect(
        self, det: dict, bbox: tuple, roi_crop: np.ndarray,
        now: float, confidence: float
    ) -> None:
        """创建待确认缺陷。"""
        cid = self.get_next_cascade_id()
        
        pending = PendingDefect(
            cascade_id=cid,
            frame_index=0,  # 由engine更新
            flash_confidence=confidence,
            roi_crop=roi_crop,
            timestamp=now,
            bbox=bbox,
            defect_type=det.get("type", "unknown"),
            severity=det.get("severity", "minor"),
            created_at=now
        )
        
        try:
            self.verification_queue.put_nowait(pending)
            with self.pending_lock:
                self.pending_defects[cid] = pending
            self.deduplicator.add_detection(bbox, now)
            print(f"--- FLASH DETECTED: cid={cid} ---", flush=True)
        except queue.Full:
            pass
