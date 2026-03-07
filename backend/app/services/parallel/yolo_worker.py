"""
FabricEye 并行检测引擎 - YOLO 检测工作线程
负责实时逐帧 YOLO 目标检测。
"""

import threading
import time
import os
import logging
from typing import Optional, Dict, Any
from collections import deque
import numpy as np
import cv2

from app.services.parallel.types import (
    DetectionResult,
    DetectionSource,
    DEFECT_CLASSES,
)
from app.services.parallel.result_store import ResultStore

logger = logging.getLogger(__name__)


class YoloDetector:
    """
    YOLO 检测器封装
    
    负责加载 YOLO 模型并进行推理。
    """
    
    def __init__(self, model_path: str, confidence_threshold: float = 0.5):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self._is_loaded = False
    
    def load(self) -> bool:
        """加载 YOLO 模型"""
        if self._is_loaded:
            return True
        
        try:
            # 尝试导入 ultralytics
            import ultralytics
            from ultralytics import YOLO
            
            # 检查模型文件是否存在
            if not os.path.exists(self.model_path):
                logger.warning(f"YOLO 模型文件不存在: {self.model_path}，将使用 mock 模式")
                self.model = None
                self._is_loaded = True
                return True
            
            # 加载模型
            self.model = YOLO(self.model_path)
            logger.info(f"YOLO 模型加载成功: {self.model_path}")
            self._is_loaded = True
            return True
            
        except ImportError:
            logger.warning("ultralytics 未安装，将使用 mock 模式")
            self.model = None
            self._is_loaded = True
            return True
        except Exception as e:
            logger.error(f"YOLO 模型加载失败: {e}")
            self.model = None
            self._is_loaded = True
            return True
    
    def predict(self, frame: np.ndarray) -> list:
        """
        对单帧图像进行 YOLO 推理
        
        Args:
            frame: BGR 格式的图像
            
        Returns:
            检测结果列表 [{'class': ..., 'confidence': ..., 'bbox': ...}]
        """
        if self.model is None:
            # Mock 模式，返回空结果
            return []
        
        try:
            # 运行推理
            results = self.model(frame, conf=self.confidence_threshold, verbose=False)
            
            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                
                for box in boxes:
                    # 获取类别
                    class_id = int(box.cls[0])
                    class_name = DEFECT_CLASSES.get(class_id, "unknown")
                    
                    # 获取置信度
                    confidence = float(box.conf[0])
                    
                    # 获取边界框 (x1, y1, x2, y2)
                    xyxy = box.xyxy[0].cpu().numpy()
                    bbox = (float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3]))
                    
                    detections.append({
                        "class": class_name,
                        "confidence": confidence,
                        "bbox": bbox,
                    })
            
            return detections
            
        except Exception as e:
            logger.error(f"YOLO 推理失败: {e}")
            return []
    
    @property
    def is_loaded(self) -> bool:
        return self._is_loaded


class YoloWorker:
    """
    YOLO 检测工作线程
    
    从帧缓冲区逐帧读取，运行 YOLO 推理，
    将结果写入 ResultStore。
    """
    
    def __init__(
        self,
        frame_buffer: deque,
        result_store: ResultStore,
        model_path: str = "models/yolov11s_fabric.pt",
        confidence_threshold: float = 0.5,
        skip_frames: int = 0,  # 跳帧数，0 表示每帧都检测
    ):
        self.frame_buffer = frame_buffer
        self.result_store = result_store
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.skip_frames = skip_frames
        
        # 检测器
        self.detector = YoloDetector(model_path, confidence_threshold)
        
        # 线程控制
        self._thread: Optional[threading.Thread] = None
        self._is_running = False
        self._roll_id = 0
        
        # 帧计数
        self._frame_counter = 0
        self._last_result_time = time.time()
    
    def start(self, roll_id: int = 0) -> bool:
        """
        启动 YOLO 检测线程
        
        Args:
            roll_id: 布卷 ID
            
        Returns:
            是否启动成功
        """
        if self._is_running:
            return True
        
        # 加载模型
        if not self.detector.load():
            logger.error("YOLO 模型加载失败")
            return False
        
        self._roll_id = roll_id
        self._is_running = True
        self._frame_counter = 0
        
        # 启动线程
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        logger.info(f"YOLO Worker 启动成功 (roll_id={roll_id})")
        return True
    
    def stop(self) -> None:
        """停止 YOLO 检测线程"""
        self._is_running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("YOLO Worker 已停止")
    
    def _run(self) -> None:
        """YOLO 检测主循环"""
        while self._is_running:
            try:
                self._process_frame()
            except Exception as e:
                logger.error(f"YOLO 检测错误: {e}")
                time.sleep(0.1)
    
    def _process_frame(self) -> None:
        """处理单帧"""
        # 检查帧缓冲区是否有新帧
        if not self.frame_buffer:
            time.sleep(0.01)
            return
        
        # 获取最新帧
        try:
            frame_info = self.frame_buffer[-1]
            if frame_info is None:
                time.sleep(0.01)
                return
            
            # 解析帧信息
            if isinstance(frame_info, tuple):
                frame_index, frame, timestamp = frame_info
            else:
                frame = frame_info
                frame_index = self._frame_counter
                timestamp = time.time()
            
            # 跳帧处理
            if self.skip_frames > 0 and self._frame_counter % (self.skip_frames + 1) != 0:
                self._frame_counter += 1
                self.result_store.increment_yolo_frames()
                return
            
            # 运行 YOLO 推理
            detections = self.detector.predict(frame)
            
            # 更新统计
            self.result_store.increment_yolo_frames()
            
            # 保存检测结果
            for det in detections:
                confidence = det["confidence"]
                bbox = det["bbox"]
                
                # 根据置信度判断严重程度
                if confidence >= 0.8:
                    severity = "severe"
                elif confidence >= 0.6:
                    severity = "moderate"
                else:
                    severity = "minor"
                
                # 创建检测结果
                result = DetectionResult(
                    source=DetectionSource.YOLO,
                    frame_index=frame_index,
                    timestamp=timestamp,
                    defect_type=det["class"],
                    severity=severity,
                    confidence=confidence,
                    bbox=bbox,
                    roi_crop=None,  # 可以在后续裁剪
                )
                
                # 写入结果存储
                self.result_store.add_yolo_result(result)
            
            self._frame_counter += 1
            self._last_result_time = time.time()
            
        except IndexError:
            time.sleep(0.01)
        except Exception as e:
            logger.error(f"YOLO 处理帧失败: {e}")
            time.sleep(0.1)
    
    def get_status(self) -> Dict[str, Any]:
        """获取工作线程状态"""
        return {
            "is_running": self._is_running,
            "frame_counter": self._frame_counter,
            "model_loaded": self.detector.is_loaded,
            "model_path": self.model_path,
            "confidence_threshold": self.confidence_threshold,
            "last_result_time": self._last_result_time,
        }
