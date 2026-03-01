"""
FabricEye AI验布系统 - 级联检测引擎
Flash (快速初筛) + Plus (精确确认) 双阶段检测流水线。
"""

import threading
import queue
import time
import logging
import collections
import asyncio
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import numpy as np
import cv2

from app.core.config import settings
from app.services.video_capture import VideoCaptureService
from app.services.ai_analyzer import AIAnalyzerService
from app.routers.websocket import manager
from app.core.database import SessionLocal
from app.models.defect import Defect, DefectType, DefectTypeCN, DefectSeverity

logger = logging.getLogger(__name__)

@dataclass
class PendingDefect:
    """Tracks a detection from Flash through Plus verification."""
    cascade_id: int
    frame_index: int
    flash_confidence: float
    roi_crop: np.ndarray
    timestamp: float
    bbox: tuple
    defect_type: str
    severity: str
    created_at: float
    status: str = "pending"
    plus_confidence: Optional[float] = None

class DetectionDeduplicator:
    def __init__(self, iou_threshold: float, time_window: float):
        self.iou_threshold = iou_threshold
        self.time_window = time_window
        self._recent: List[Tuple[tuple, float]] = []

    def is_duplicate(self, bbox: tuple, timestamp: float) -> bool:
        self._prune(timestamp)
        for prev_bbox, _ in self._recent:
            if self._compute_iou(bbox, prev_bbox) >= self.iou_threshold:
                return True
        return False

    def add_detection(self, bbox: tuple, timestamp: float) -> None:
        self._prune(timestamp)
        self._recent.append((bbox, timestamp))

    def _prune(self, now: float) -> None:
        cutoff = now - self.time_window
        self._recent = [(b, t) for b, t in self._recent if t >= cutoff]

    @staticmethod
    def _compute_iou(box1: tuple, box2: tuple) -> float:
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        inter_w = max(0, x2 - x1)
        inter_h = max(0, y2 - y1)
        inter_area = inter_w * inter_h
        area1 = max(0, box1[2] - box1[0]) * max(0, box1[3] - box1[1])
        area2 = max(0, box2[2] - box2[0]) * max(0, box2[3] - box2[1])
        union_area = area1 + area2 - inter_area
        return inter_area / union_area if union_area > 0 else 0.0

def get_vlm_roi(image: np.ndarray, bbox: tuple, margin: float = 0.15, target_size: int = 512) -> np.ndarray:
    img_h, img_w = image.shape[:2]
    x1, y1, x2, y2 = bbox
    mx, my = (x2 - x1) * margin, (y2 - y1) * margin
    cx1, cy1 = max(0, int(x1 - mx)), max(0, int(y1 - my))
    cx2, cy2 = min(img_w, int(x2 + mx)), min(img_h, int(y2 + my))
    crop = image[cy1:cy2, cx1:cx2]
    if crop.size == 0: return np.zeros((target_size, target_size, 3), dtype=np.uint8)
    scale = min(target_size / crop.shape[1], target_size / crop.shape[0])
    resized = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    canvas = np.zeros((target_size, target_size, 3), dtype=np.uint8)
    pad_x, pad_y = (target_size - resized.shape[1]) // 2, (target_size - resized.shape[0]) // 2
    canvas[pad_y:pad_y + resized.shape[0], pad_x:pad_x + resized.shape[1]] = resized
    return canvas

class CascadeEngine:
    def __init__(self, roll_id: int):
        self.roll_id = roll_id
        self.video_service = VideoCaptureService()
        self.analyzer = AIAnalyzerService()
        self.frame_buffer = collections.deque(maxlen=settings.FRAME_BUFFER_SIZE)
        self._frame_index = 0
        self.verification_queue = queue.Queue(maxsize=settings.VERIFICATION_QUEUE_SIZE)
        self._pending_lock = threading.Lock()
        self.pending_defects: Dict[int, PendingDefect] = {}
        self._cascade_id_counter = 0
        self.deduplicator = DetectionDeduplicator(settings.DEDUP_IOU_THRESHOLD, settings.DEDUP_TIME_WINDOW)
        self.is_running = False
        self._capture_thread = None
        self._flash_thread = None
        self._plus_thread = None

    def start(self) -> bool:
        if self.is_running: return True
        if not self.video_service.start_capture(): return False
        self.analyzer.load_model()
        self.is_running = True
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._flash_thread = threading.Thread(target=self._flash_loop, daemon=True)
        self._plus_thread = threading.Thread(target=self._plus_loop, daemon=True)
        self._capture_thread.start()
        self._flash_thread.start()
        self._plus_thread.start()
        print(f"--- CascadeEngine started for roll {self.roll_id} ---", flush=True)
        return True

    def stop(self) -> None:
        self.is_running = False
        print(f"--- CascadeEngine stopping for roll {self.roll_id} ---", flush=True)

    def _capture_loop(self) -> None:
        print(f"--- THREAD START: Capture Loop ---", flush=True)
        while self.is_running:
            try:
                frame = self.video_service.get_frame()
                if frame is not None:
                    self.frame_buffer.append((self._frame_index, frame))
                    self._frame_index += 1
            except: pass
            time.sleep(0.01)

    def _flash_loop(self) -> None:
        print(f"--- THREAD START: Flash Loop ---", flush=True)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while self.is_running:
            try:
                if not self.frame_buffer:
                    time.sleep(0.1)
                    continue
                _, frame = self.frame_buffer[-1]
                detections = self.analyzer.analyze_with_flash(frame)
                now = time.time()
                for det in detections:
                    confidence = det.get("confidence", 0.0)
                    if confidence < settings.CASCADE_FLASH_THRESHOLD: continue
                    location = det.get("location", [0, 0, 0, 0])
                    print(f"--- FLASH RAW LOCATION: {location} ---", flush=True)
                    
                    is_valid_location = (
                        len(location) == 4 and
                        not all(v == 0 for v in location) and
                        location[2] > location[0] and
                        location[3] > location[1]
                    )
                    
                    if is_valid_location:
                        bbox = self._location_to_bbox(location, frame.shape[1], frame.shape[0])
                        print(f"--- FLASH CONVERTED BBOX: {bbox} (img: {frame.shape[1]}x{frame.shape[0]}) ---", flush=True)
                        if self.deduplicator.is_duplicate(bbox, now): continue
                        roi_crop = get_vlm_roi(frame, bbox)
                    else:
                        print(f"--- INVALID LOCATION, using full frame for Plus verification ---", flush=True)
                        bbox = (0, 0, frame.shape[1], frame.shape[0])
                        scale = 512 / max(frame.shape[0], frame.shape[1])
                        roi_crop = cv2.resize(frame, None, fx=scale, fy=scale)
                        canvas = np.zeros((512, 512, 3), dtype=np.uint8)
                        y_offset = (512 - roi_crop.shape[0]) // 2
                        x_offset = (512 - roi_crop.shape[1]) // 2
                        canvas[y_offset:y_offset+roi_crop.shape[0], x_offset:x_offset+roi_crop.shape[1]] = roi_crop
                        roi_crop = canvas
                    
                    print(f"--- ROI CROP: shape={roi_crop.shape}, mean={roi_crop.mean():.2f}, min={roi_crop.min()}, max={roi_crop.max()} ---", flush=True)
                    with self._pending_lock:
                        self._cascade_id_counter += 1
                        cid = self._cascade_id_counter
                    pending = PendingDefect(
                        cascade_id=cid, frame_index=self._frame_index, flash_confidence=confidence,
                        roi_crop=roi_crop, timestamp=now, bbox=bbox,
                        defect_type=det.get("type", "unknown"), severity=det.get("severity", "minor"),
                        created_at=now
                    )
                    try:
                        self.verification_queue.put_nowait(pending)
                        with self._pending_lock: self.pending_defects[cid] = pending
                        self.deduplicator.add_detection(bbox, now)
                        print(f"--- FLASH DETECTED: cid={cid} ---", flush=True)
                    except: pass
                self._expire_pending(now)
            except: pass
            time.sleep(settings.ANALYSIS_INTERVAL)
        loop.close()

    def _plus_loop(self) -> None:
        debug_dir = "storage/debug_crops"
        os.makedirs(debug_dir, exist_ok=True)
        print(f"--- THREAD START: Plus Loop ---", flush=True)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while self.is_running:
            try: pending = self.verification_queue.get(timeout=1)
            except: continue
            try:
                cv2.imwrite(f"{debug_dir}/cid_{pending.cascade_id}.jpg", pending.roi_crop)
                snapshot_path = f"storage/debug_crops/cid_{pending.cascade_id}.jpg"
                results = self.analyzer.analyze_with_plus(pending.roi_crop)
                plus_confidence = max((r.get("confidence", 0.0) for r in results), default=0.0)
                with self._pending_lock:
                    defect = self.pending_defects.get(pending.cascade_id)
                    if not defect: continue
                    if plus_confidence >= settings.CASCADE_PLUS_THRESHOLD:
                        defect.status = "confirmed"
                        
                        # 映射缺陷类型，确保前端能识别
                        raw_type = defect.defect_type.lower()
                        if raw_type == "color_variation":
                            raw_type = "color_variance"
                        
                        defect_dict = {
                            "type": "defect_confirmed",
                            "id": defect.cascade_id,
                            "defectType": raw_type,
                            "severity": defect.severity,
                            "confidence": round(plus_confidence, 3),
                            "position": f"({defect.bbox[0]}, {defect.bbox[1]})",
                            "timestamp": datetime.now().isoformat(), # 使用本地时间
                            "imageUrl": f"/api/defects/image/cid_{pending.cascade_id}",
                            "rollId": self.roll_id,
                            "cascadeId": defect.cascade_id,
                            "flashConfidence": round(defect.flash_confidence, 3),
                            "plusConfidence": round(plus_confidence, 3),
                            "location": list(defect.bbox)
                        }
                        loop.run_until_complete(manager.broadcast(defect_dict))
                        loop.run_until_complete(self._save_defect_to_db(defect, plus_confidence, snapshot_path))
                        print(f"--- PLUS CONFIRMED: cid={defect.cascade_id} ---", flush=True)
                    else:
                        defect.status = "rejected"
                        print(f"--- PLUS REJECTED: cid={defect.cascade_id} (conf={plus_confidence:.2f}) ---", flush=True)
            except: pass
        loop.close()

    async def _save_defect_to_db(self, defect, plus_confidence, snapshot_path=None) -> None:
        try:
            matched_enum, matched_severity = DefectType.STAIN, DefectSeverity.MINOR
            try: matched_enum = DefectType(defect.defect_type.lower())
            except: pass
            try: matched_severity = DefectSeverity(defect.severity.lower())
            except: pass
            db_defect = Defect(
                roll_id=self.roll_id, defect_type=matched_enum, defect_type_cn=DefectTypeCN.get_cn(matched_enum),
                confidence=plus_confidence, severity=matched_severity,
                bbox_x1=defect.bbox[0], bbox_y1=defect.bbox[1], bbox_x2=defect.bbox[2], bbox_y2=defect.bbox[3],
                snapshot_path=snapshot_path,
                detected_at=datetime.utcnow(), reviewed=False
            )
            async with SessionLocal() as session:
                session.add(db_defect)
                await session.commit()
        except: pass

    def _location_to_bbox(self, location: list, img_w: int, img_h: int) -> Tuple[int, int, int, int]:
        if len(location) != 4: return (0, 0, 0, 0)
        a, b, c, d = location
        max_val = max(a, b, c, d)
        if max_val > max(img_w, img_h):
            return (int(a * img_w / 1000), int(b * img_h / 1000), int(c * img_w / 1000), int(d * img_h / 1000))
        else:
            return (int(a), int(b), int(c), int(d))

    def _expire_pending(self, now: float) -> None:
        with self._pending_lock:
            for cid, defect in self.pending_defects.items():
                if defect.status == "pending" and (now - defect.created_at) > settings.PENDING_DEFECT_TTL:
                    defect.status = "expired"

    def get_status(self) -> dict:
        with self._pending_lock:
            p = sum(1 for d in self.pending_defects.values() if d.status == "pending")
            c = sum(1 for d in self.pending_defects.values() if d.status == "confirmed")
            r = sum(1 for d in self.pending_defects.values() if d.status == "rejected")
            e = sum(1 for d in self.pending_defects.values() if d.status == "expired")
        return {
            "is_running": self.is_running, "roll_id": self.roll_id, "buffer_size": len(self.frame_buffer),
            "buffer_capacity": settings.FRAME_BUFFER_SIZE, "verification_queue_size": self.verification_queue.qsize(),
            "pending_count": p, "confirmed_count": c, "rejected_count": r, "expired_count": e,
            "total_frames_captured": self._frame_index, "cascade_id_counter": self._cascade_id_counter
        }
