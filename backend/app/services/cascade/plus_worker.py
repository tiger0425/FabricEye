"""
FabricEye 级联检测引擎 - Plus检测工作线程
精确确认检测流程。
"""

import os
import asyncio
import threading
import queue
from typing import Dict

import cv2

from app.core.config import settings
from app.routers.websocket import manager
from app.services.cascade.types import PendingDefect
from app.services.cascade.timestamp import calculate_relative_timestamp
from app.services.cascade.bbox_utils import format_position
from app.services.cascade.db_operations import save_defect_to_db


class PlusWorker:
    """Plus检测工作线程（精确确认）。"""
    
    def __init__(
        self,
        verification_queue: queue.Queue,
        pending_defects: Dict[int, PendingDefect],
        pending_lock: threading.Lock,
        roll_id: int
    ):
        self.verification_queue = verification_queue
        self.pending_defects = pending_defects
        self.pending_lock = pending_lock
        self.roll_id = roll_id
        self.analyzer = None
        self.video_id = None
        self.recording_start_time = None
        self._thread: threading.Thread = None
        self._is_running = False
        self._debug_dir = "storage/debug_crops"
    
    def start(self, analyzer, video_id: int, recording_start_time: float) -> None:
        """启动Plus检测线程。"""
        self.analyzer = analyzer
        self.video_id = video_id
        self.recording_start_time = recording_start_time
        self._is_running = True
        os.makedirs(self._debug_dir, exist_ok=True)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("--- THREAD START: Plus Loop ---", flush=True)
    
    def stop(self) -> None:
        """停止Plus检测线程。"""
        self._is_running = False
    
    def _run(self) -> None:
        """Plus检测循环。"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self._is_running:
            try:
                pending = self.verification_queue.get(timeout=1)
                self._process_pending(pending, loop)
            except queue.Empty:
                continue
        
        loop.close()
    
    def _process_pending(self, pending: PendingDefect, loop) -> None:
        """处理待确认缺陷。"""
        snapshot_path = f"{self._debug_dir}/cid_{pending.cascade_id}.jpg"
        cv2.imwrite(snapshot_path, pending.roi_crop)
        
        results = self.analyzer.analyze_with_plus(pending.roi_crop)
        plus_confidence = max((r.get("confidence", 0.0) for r in results), default=0.0)
        
        with self.pending_lock:
            defect = self.pending_defects.get(pending.cascade_id)
            if not defect:
                return
            
            if plus_confidence >= settings.CASCADE_PLUS_THRESHOLD:
                defect.status = "confirmed"
                self._confirm_defect(defect, plus_confidence, snapshot_path, loop)
            else:
                defect.status = "rejected"
    
    def _confirm_defect(self, defect: PendingDefect, plus_confidence: float, 
                        snapshot_path: str, loop) -> None:
        """确认缺陷并广播。"""
        raw_type = defect.defect_type.lower()
        if raw_type == "color_variation":
            raw_type = "color_variance"
        
        relative_ts = calculate_relative_timestamp(self.recording_start_time)
        
        defect_dict = {
            "type": "defect_confirmed",
            "id": defect.cascade_id,
            "defectType": raw_type,
            "severity": defect.severity,
            "confidence": round(plus_confidence, 3),
            "position": format_position(defect.bbox),
            "timestamp": relative_ts,
            "imageUrl": f"/api/defects/image/cid_{defect.cascade_id}",
            "rollId": self.roll_id,
            "cascadeId": defect.cascade_id,
            "flashConfidence": round(defect.flash_confidence, 3),
            "plusConfidence": round(plus_confidence, 3),
            "location": list(defect.bbox)
        }
        
        loop.run_until_complete(manager.broadcast(defect_dict))
        loop.run_until_complete(
            save_defect_to_db(defect, plus_confidence, snapshot_path,
                           self.roll_id, self.video_id, relative_ts)
        )
        print(f"--- PLUS CONFIRMED: cid={defect.cascade_id} ---", flush=True)
