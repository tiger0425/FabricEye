import cv2
import logging
from typing import Optional, Protocol
import numpy as np
from abc import ABC, abstractmethod
from app.core.config import settings

logger = logging.getLogger(__name__)

class BaseCamera(ABC):
    """
    相机基类，定义统一接口
    """
    @abstractmethod
    def open(self) -> bool:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def get_frame(self) -> Optional[np.ndarray]:
        pass

class OpenCVCamera(BaseCamera):
    """
    OpenCV 相机实现 (普通摄像头/USB摄像头)
    """
    def __init__(self, device_id: int, width: int = 1280, height: int = 720, fps: int = 30):
        self.device_id = device_id
        self.width = width
        self.height = height
        self.fps = fps
        self.cap: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        try:
            self.cap = cv2.VideoCapture(self.device_id)
            if not self.cap.isOpened():
                logger.error(f"Cannot open OpenCV camera {self.device_id}")
                return False
            
            # 设置分辨率和帧率
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # 验证实际设置的值
            actual_w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            logger.info(f"OpenCV Camera {self.device_id} started. Res: {actual_w}x{actual_h}")
            return True
        except Exception as e:
            logger.error(f"Error opening OpenCV camera: {e}")
            return False

    def close(self) -> None:
        if self.cap:
            self.cap.release()
            self.cap = None
            logger.info(f"OpenCV Camera {self.device_id} closed.")

    def get_frame(self) -> Optional[np.ndarray]:
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None

class MockCamera(BaseCamera):
    """
    模拟相机实现 (产生噪点)
    """
    def __init__(self, width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        self.is_opened = False

    def open(self) -> bool:
        self.is_opened = True
        logger.info("Mock Camera started.")
        return True

    def close(self) -> None:
        self.is_opened = False
        logger.info("Mock Camera closed.")

    def get_frame(self) -> Optional[np.ndarray]:
        if not self.is_opened:
            return None
        # 产生噪点
        return np.random.randint(0, 255, (self.height, self.width, 3), dtype=np.uint8)

class CameraFactory:
    """
    相机工厂，根据配置创建相机实例
    """
    @staticmethod
    def create_camera() -> BaseCamera:
        cam_type = settings.CAMERA_TYPE.lower()
        if cam_type == "opencv":
            return OpenCVCamera(
                device_id=settings.CAMERA_ID,
                width=settings.CAMERA_WIDTH,
                height=settings.CAMERA_HEIGHT,
                fps=settings.CAMERA_FPS
            )
        elif cam_type == "mock":
            return MockCamera(
                width=settings.CAMERA_WIDTH,
                height=settings.CAMERA_HEIGHT
            )
        # TODO: 后续增加 MVS 相机支持
        # elif cam_type == "mvs":
        #     return MVSCamera(...)
        else:
            logger.warning(f"Unknown camera type: {cam_type}. Falling back to MockCamera.")
            return MockCamera()

class VideoCaptureService:
    """
    视频采集服务类
    封装相机底层实现，提供高层接口。
    """
    def __init__(self):
        self.camera: BaseCamera = CameraFactory.create_camera()

    def start_capture(self) -> bool:
        return self.camera.open()

    def stop_capture(self) -> None:
        self.camera.close()

    def get_frame(self) -> Optional[np.ndarray]:
        frame = self.camera.get_frame()
        if frame is None:
            # 如果配置不是 mock 却没拿到帧，可以考虑自动回退到 mock 或重试
            return None
        return frame

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
