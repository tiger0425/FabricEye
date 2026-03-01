"""
FabricEye AI验布系统 - 级联检测引擎
Flash (快速初筛) + Plus (精确确认) 双阶段检测流水线。
管理帧环形缓冲区、空间去重、异步验证队列和 WebSocket 广播。
"""

import threading
import queue
import time
import logging
import collections
import asyncio
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


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PendingDefect:
    """Tracks a detection from Flash through Plus verification."""
    cascade_id: int          # auto-incrementing ID
    frame_index: int         # index in ring buffer
    flash_confidence: float  # confidence from Flash
    roi_crop: np.ndarray     # 512x512 crop for Plus verification
    timestamp: float         # time.time() when detected
    bbox: tuple              # (x1, y1, x2, y2) pixel coordinates
    defect_type: str         # type from Flash
    severity: str            # severity from Flash
    created_at: float        # for TTL expiry
    status: str = "pending"  # pending | confirmed | rejected | expired
    plus_confidence: Optional[float] = None


# ---------------------------------------------------------------------------
# Spatial deduplication
# ---------------------------------------------------------------------------

class DetectionDeduplicator:
    """
    Deduplicates detections using IoU within a sliding time window.
    Prevents the same physical defect from being queued multiple times.
    """

    def __init__(self, iou_threshold: float, time_window: float):
        self.iou_threshold = iou_threshold
        self.time_window = time_window
        self._recent: List[Tuple[tuple, float]] = []  # (bbox, timestamp)

    def is_duplicate(self, bbox: tuple, timestamp: float) -> bool:
        """Check whether *bbox* overlaps any recent detection above the IoU threshold."""
        self._prune(timestamp)
        for prev_bbox, _ in self._recent:
            if self._compute_iou(bbox, prev_bbox) >= self.iou_threshold:
                return True
        return False

    def add_detection(self, bbox: tuple, timestamp: float) -> None:
        """Record a detection so future calls to *is_duplicate* can reference it."""
        self._prune(timestamp)
        self._recent.append((bbox, timestamp))

    def _prune(self, now: float) -> None:
        """Remove entries older than *time_window*."""
        cutoff = now - self.time_window
        self._recent = [(b, t) for b, t in self._recent if t >= cutoff]

    @staticmethod
    def _compute_iou(box1: tuple, box2: tuple) -> float:
        """Standard IoU between two (x1, y1, x2, y2) boxes."""
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

        if union_area <= 0:
            return 0.0
        return inter_area / union_area


# ---------------------------------------------------------------------------
# ROI extraction helper
# ---------------------------------------------------------------------------

def get_vlm_roi(
    image: np.ndarray,
    bbox: tuple,
    margin: float = 0.15,
    target_size: int = 512,
) -> np.ndarray:
    """
    Crop a region of interest from *image* around *bbox* (x1, y1, x2, y2 in pixels),
    expand by *margin* on each side, and letterbox-resize to *target_size* x *target_size*.

    Returns
    -------
    np.ndarray  –  BGR uint8 image of shape (target_size, target_size, 3).
    """
    img_h, img_w = image.shape[:2]
    x1, y1, x2, y2 = bbox

    bw = x2 - x1
    bh = y2 - y1

    # Expand by margin, clamp to image bounds
    mx = bw * margin
    my = bh * margin
    cx1 = max(0, int(x1 - mx))
    cy1 = max(0, int(y1 - my))
    cx2 = min(img_w, int(x2 + mx))
    cy2 = min(img_h, int(y2 + my))

    crop = image[cy1:cy2, cx1:cx2]

    # Letterbox resize: fit into target_size x target_size, pad with black
    ch, cw = crop.shape[:2]
    if ch == 0 or cw == 0:
        return np.zeros((target_size, target_size, 3), dtype=np.uint8)

    scale = min(target_size / cw, target_size / ch)
    new_w = int(cw * scale)
    new_h = int(ch * scale)
    resized = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    canvas = np.zeros((target_size, target_size, 3), dtype=np.uint8)
    pad_x = (target_size - new_w) // 2
    pad_y = (target_size - new_h) // 2
    canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized

    return canvas


# ---------------------------------------------------------------------------
# Cascade Detection Engine
# ---------------------------------------------------------------------------

class CascadeEngine:
    """
    Two-stage cascade detection engine.

    Stage 1 – **Flash**: fast model scans every frame at ANALYSIS_INTERVAL.
    Stage 2 – **Plus**: precise model verifies suspicious crops from Flash.

    Threads
    -------
    1. _capture_thread  – feeds frames into the ring buffer.
    2. _flash_thread    – runs Flash detection, deduplicates, queues ROIs.
    3. _plus_thread     – verifies queued ROIs, broadcasts confirmed defects.
    """

    def __init__(self, roll_id: int):
        self.roll_id = roll_id

        # Services
        self.video_service = VideoCaptureService()
        self.analyzer = AIAnalyzerService()

        # Frame ring buffer
        self.frame_buffer: collections.deque = collections.deque(
            maxlen=settings.FRAME_BUFFER_SIZE,
        )
        self._frame_index: int = 0  # monotonic counter for frame_index

        # Verification queue (Flash → Plus)
        self.verification_queue: queue.Queue = queue.Queue(
            maxsize=settings.VERIFICATION_QUEUE_SIZE,
        )

        # Pending defects tracking
        self._pending_lock = threading.Lock()
        self.pending_defects: Dict[int, PendingDefect] = {}
        self._cascade_id_counter: int = 0

        # Deduplicator
        self.deduplicator = DetectionDeduplicator(
            iou_threshold=settings.DEDUP_IOU_THRESHOLD,
            time_window=settings.DEDUP_TIME_WINDOW,
        )

        # Thread handles
        self.is_running: bool = False
        self._capture_thread: Optional[threading.Thread] = None
        self._flash_thread: Optional[threading.Thread] = None
        self._plus_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """Start the cascade engine (capture + Flash + Plus threads)."""
        if self.is_running:
            logger.warning("CascadeEngine is already running")
            return True

        if not self.video_service.start_capture():
            logger.error("Failed to start video capture")
            return False

        self.analyzer.load_model()
        self.is_running = True

        self._capture_thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="cascade-capture",
        )
        self._flash_thread = threading.Thread(
            target=self._flash_loop, daemon=True, name="cascade-flash",
        )
        self._plus_thread = threading.Thread(
            target=self._plus_loop, daemon=True, name="cascade-plus",
        )

        self._capture_thread.start()
        self._flash_thread.start()
        self._plus_thread.start()

        logger.info(
            f"CascadeEngine started for roll {self.roll_id} "
            f"(buffer={settings.FRAME_BUFFER_SIZE}, "
            f"queue={settings.VERIFICATION_QUEUE_SIZE})"
        )
        return True

    def stop(self) -> None:
        """Stop the engine and join all threads."""
        self.is_running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=2)
        if self._flash_thread:
            self._flash_thread.join(timeout=2)
        if self._plus_thread:
            self._plus_thread.join(timeout=2)
        logger.info(f"CascadeEngine stopped for roll {self.roll_id}")

    # ------------------------------------------------------------------
    # Thread loops
    # ------------------------------------------------------------------

    def _capture_loop(self) -> None:
        """Continuously capture frames into the ring buffer."""
        while self.is_running:
            try:
                frame = self.video_service.get_frame()
                if frame is not None:
                    self.frame_buffer.append((self._frame_index, frame))
                    self._frame_index += 1
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
            time.sleep(0.01)

    def _flash_loop(self) -> None:
        """Run Flash (fast) detection on the latest frame at ANALYSIS_INTERVAL."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self.is_running:
            try:
                # Grab latest frame from buffer
                if not self.frame_buffer:
                    time.sleep(0.1)
                    continue

                frame_index, frame = self.frame_buffer[-1]

                # Run Flash detection (sync wrapper)
                detections = self.analyzer.analyze_with_flash(frame)

                now = time.time()
                img_h, img_w = frame.shape[:2]

                for det in detections:
                    confidence = det.get("confidence", 0.0)
                    if confidence < settings.CASCADE_FLASH_THRESHOLD:
                        continue

                    # Convert location to (x1, y1, x2, y2) pixel bbox
                    bbox = self._location_to_bbox(det.get("location", [0, 0, 0, 0]), img_w, img_h)

                    # Deduplication check
                    if self.deduplicator.is_duplicate(bbox, now):
                        continue

                    # Prepare ROI crop for Plus verification
                    roi_crop = get_vlm_roi(frame, bbox)

                    # Create PendingDefect
                    with self._pending_lock:
                        self._cascade_id_counter += 1
                        cid = self._cascade_id_counter

                    pending = PendingDefect(
                        cascade_id=cid,
                        frame_index=frame_index,
                        flash_confidence=confidence,
                        roi_crop=roi_crop,
                        timestamp=now,
                        bbox=bbox,
                        defect_type=det.get("type", "unknown"),
                        severity=det.get("severity", "minor"),
                        created_at=now,
                    )

                    # Enqueue for Plus verification (non-blocking)
                    try:
                        self.verification_queue.put_nowait(pending)
                    except queue.Full:
                        logger.warning(
                            f"Verification queue full – skipping cascade_id={cid} "
                            f"(type={pending.defect_type}, conf={confidence:.2f})"
                        )
                        continue

                    with self._pending_lock:
                        self.pending_defects[cid] = pending

                    self.deduplicator.add_detection(bbox, now)

                    logger.info(
                        f"Flash detected: cascade_id={cid} type={pending.defect_type} "
                        f"conf={confidence:.2f} bbox={bbox}"
                    )

                # Expire stale PendingDefects
                self._expire_pending(now)

            except Exception as e:
                logger.error(f"Error in flash loop: {e}")

            time.sleep(settings.ANALYSIS_INTERVAL)

        loop.close()

    def _plus_loop(self) -> None:
        """Consume the verification queue and run Plus (precise) confirmation."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self.is_running:
            try:
                pending: PendingDefect = self.verification_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                # Run Plus detection (sync wrapper)
                results = self.analyzer.analyze_with_plus(pending.roi_crop)

                # Find the best matching result
                plus_confidence = 0.0
                if results:
                    plus_confidence = max(r.get("confidence", 0.0) for r in results)

                with self._pending_lock:
                    defect = self.pending_defects.get(pending.cascade_id)
                    if defect is None:
                        continue

                    if plus_confidence >= settings.CASCADE_PLUS_THRESHOLD:
                        defect.status = "confirmed"
                        defect.plus_confidence = plus_confidence

                        defect_dict = {
                            "type": "defect_confirmed",
                            "rollId": self.roll_id,
                            "cascadeId": defect.cascade_id,
                            "defectType": defect.defect_type,
                            "severity": defect.severity,
                            "location": list(defect.bbox),
                            "flashConfidence": round(defect.flash_confidence, 3),
                            "plusConfidence": round(plus_confidence, 3),
                            "timestamp": datetime.utcnow().isoformat(),
                        }

                        # Broadcast via WebSocket
                        loop.run_until_complete(manager.broadcast(defect_dict))

                        # Persist confirmed defect to database
                        loop.run_until_complete(
                            self._save_defect_to_db(defect, plus_confidence)
                        )
                        logger.info(
                            f"CONFIRMED cascade_id={defect.cascade_id} "
                            f"type={defect.defect_type} "
                            f"flash={defect.flash_confidence:.2f} "
                            f"plus={plus_confidence:.2f}"
                        )
                    else:
                        defect.status = "rejected"
                        defect.plus_confidence = plus_confidence
                        logger.info(
                            f"Rejected cascade_id={defect.cascade_id} "
                            f"type={defect.defect_type} "
                            f"plus={plus_confidence:.2f} "
                            f"(threshold={settings.CASCADE_PLUS_THRESHOLD})"
                        )

            except Exception as e:
                logger.error(f"Error in plus loop: {e}")

        loop.close()

    async def _save_defect_to_db(self, defect: PendingDefect, plus_confidence: float) -> None:
        """Persist a confirmed defect to the database via async session."""
        try:
            # Map defect_type string to DefectType enum
            try:
                matched_enum = DefectType(defect.defect_type.lower())
            except ValueError:
                logger.warning(f"Unknown defect type '{defect.defect_type}', falling back to STAIN")
                matched_enum = DefectType.STAIN

            # Map severity string to DefectSeverity enum
            try:
                matched_severity = DefectSeverity(defect.severity.lower())
            except ValueError:
                logger.warning(f"Unknown severity '{defect.severity}', falling back to MINOR")
                matched_severity = DefectSeverity.MINOR

            db_defect = Defect(
                roll_id=self.roll_id,
                defect_type=matched_enum,
                defect_type_cn=DefectTypeCN.get_cn(matched_enum),
                confidence=plus_confidence,
                severity=matched_severity,
                bbox_x1=defect.bbox[0],
                bbox_y1=defect.bbox[1],
                bbox_x2=defect.bbox[2],
                bbox_y2=defect.bbox[3],
                detected_at=datetime.utcnow(),
                reviewed=False,
            )

            async with SessionLocal() as session:
                session.add(db_defect)
                await session.commit()
                logger.info(
                    f"Saved defect to DB: cascade_id={defect.cascade_id} "
                    f"type={matched_enum.value}"
                )
        except Exception as e:
            logger.error(f"Failed to save defect to DB: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _location_to_bbox(
        location: list, img_w: int, img_h: int,
    ) -> Tuple[int, int, int, int]:
        """
        Convert a detection location to (x1, y1, x2, y2) pixel coordinates.

        Handles two formats returned by the AI analyzer:
        - [x, y, w, h] in pixels  (w/h are sizes)
        - [xmin, ymin, xmax, ymax] normalized 0-1000
        """
        if len(location) != 4:
            return (0, 0, 0, 0)

        a, b, c, d = location

        # Heuristic: if all values <= 1000 and c > a and d > b,
        # treat as normalised [xmin, ymin, xmax, ymax] in 0-1000 range.
        if all(0 <= v <= 1000 for v in location) and c > a and d > b:
            # Could be normalised OR small pixel [x, y, w, h].
            # If c and d are clearly "max" style (much larger than typical w/h):
            if c > 100 or d > 100:
                # Normalised 0-1000 → pixel
                x1 = int(a * img_w / 1000)
                y1 = int(b * img_h / 1000)
                x2 = int(c * img_w / 1000)
                y2 = int(d * img_h / 1000)
                return (x1, y1, x2, y2)

        # Default: treat as [x, y, w, h] in pixel coordinates
        x1 = int(a)
        y1 = int(b)
        x2 = int(a + c)
        y2 = int(b + d)
        return (x1, y1, x2, y2)

    def _expire_pending(self, now: float) -> None:
        """Mark PendingDefects older than TTL as expired."""
        with self._pending_lock:
            for cid, defect in self.pending_defects.items():
                if defect.status == "pending" and (now - defect.created_at) > settings.PENDING_DEFECT_TTL:
                    defect.status = "expired"
                    logger.info(f"Expired cascade_id={cid} (age={now - defect.created_at:.1f}s)")

    def get_status(self) -> dict:
        """Return engine statistics."""
        with self._pending_lock:
            pending_count = sum(1 for d in self.pending_defects.values() if d.status == "pending")
            confirmed_count = sum(1 for d in self.pending_defects.values() if d.status == "confirmed")
            rejected_count = sum(1 for d in self.pending_defects.values() if d.status == "rejected")
            expired_count = sum(1 for d in self.pending_defects.values() if d.status == "expired")

        return {
            "is_running": self.is_running,
            "roll_id": self.roll_id,
            "buffer_size": len(self.frame_buffer),
            "buffer_capacity": settings.FRAME_BUFFER_SIZE,
            "verification_queue_size": self.verification_queue.qsize(),
            "pending_count": pending_count,
            "confirmed_count": confirmed_count,
            "rejected_count": rejected_count,
            "expired_count": expired_count,
            "total_frames_captured": self._frame_index,
            "cascade_id_counter": self._cascade_id_counter,
        }
