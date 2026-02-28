import cv2
import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

class VideoCaptureService:
    """
    视频采集服务类
    封装 OpenCV 的视频捕获功能。
    """
    def __init__(self, device_id: int = 0):
        self.device_id = device_id
        self.cap: Optional[cv2.VideoCapture] = None

    def start_capture(self) -> bool:
        try:
            self.cap = cv2.VideoCapture(self.device_id)
            if not self.cap.isOpened():
                logger.warning(f"Cannot open camera {self.device_id}. Entering Mock mode.")
                return True
            logger.info(f"Camera {self.device_id} started.")
            return True
        except Exception as e:
            logger.error(f"Error starting capture: {e}")
            return False

    def stop_capture(self) -> None:
        if self.cap:
            self.cap.release()
            self.cap = None
            logger.info("Camera stopped.")

    def get_frame(self) -> Optional[np.ndarray]:
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return frame
        # Mock mode: return random noise
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
