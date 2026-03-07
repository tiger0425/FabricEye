"""
FabricEye 并行检测引擎 - VLM 采样工作线程
负责定时采样帧并调用 VLM Flash API 进行检测。
"""

import threading
import time
import os
import logging
from typing import Optional, Dict, Any, Callable
from collections import deque
import numpy as np
import cv2

from app.services.parallel.types import (
    DetectionResult,
    DetectionSource,
)
from app.services.parallel.result_store import ResultStore

logger = logging.getLogger(__name__)


class VlmSampler:
    """
    VLM 采样器
    
    负责按一定间隔采样帧并调用 VLM Flash API 进行检测。
    复用现有的 ai_analyzer.py 中的 VLM 调用逻辑。
    """
    
    def __init__(
        self,
        frame_buffer: deque,
        result_store: ResultStore,
        sample_interval: int = 30,  # 每多少帧采样一次
        analyzer = None,  # AIAnalyzerService 实例
        vlm_callback: Optional[Callable] = None,  # VLM 调用回调
    ):
        self.frame_buffer = frame_buffer
        self.result_store = result_store
        self.sample_interval = sample_interval
        self.analyzer = analyzer
        self.vlm_callback = vlm_callback
        
        # 线程控制
        self._thread: Optional[threading.Thread] = None
        self._is_running = False
        self._roll_id = 0
        
        # 帧计数
        self._frame_counter = 0
        self._last_sample_time = time.time()
        self._total_samples = 0
    
    def start(self, roll_id: int = 0) -> bool:
        """
        启动 VLM 采样线程
        
        Args:
            roll_id: 布卷 ID
            
        Returns:
            是否启动成功
        """
        if self._is_running:
            return True
        
        self._roll_id = roll_id
        self._is_running = True
        self._frame_counter = 0
        self._total_samples = 0
        
        # 启动线程
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        logger.info(f"VLM Sampler 启动成功 (roll_id={roll_id}, interval={self.sample_interval})")
        return True
    
    def stop(self) -> None:
        """停止 VLM 采样线程"""
        self._is_running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info(f"VLM Sampler 已停止，共采样 {self._total_samples} 次")
    
    def set_sample_interval(self, interval: int) -> None:
        """动态调整采样间隔"""
        self.sample_interval = max(1, interval)
        logger.info(f"VLM 采样间隔调整为: {self.sample_interval}")
    
    def _run(self) -> None:
        """VLM 采样主循环"""
        while self._is_running:
            try:
                self._process_frame()
            except Exception as e:
                logger.error(f"VLM 采样错误: {e}")
                time.sleep(0.1)
            
            # 帧间隔控制
            time.sleep(0.01)
    
    def _process_frame(self) -> None:
        """处理帧采样"""
        # 检查是否需要采样
        if self._frame_counter % self.sample_interval != 0:
            self._frame_counter += 1
            return
        
        # 检查帧缓冲区是否有新帧
        if not self.frame_buffer:
            self._frame_counter += 1
            return
        
        # 获取最新帧
        try:
            frame_info = self.frame_buffer[-1]
            if frame_info is None:
                self._frame_counter += 1
                return
            
            # 解析帧信息
            if isinstance(frame_info, tuple):
                frame_index, frame, timestamp = frame_info
            else:
                frame = frame_info
                frame_index = self._frame_counter
                timestamp = time.time()
            
            # 更新统计
            self.result_store.increment_vlm_samples()
            self._total_samples += 1
            self._last_sample_time = time.time()
            
            # 调用 VLM 进行检测
            self._call_vlm(frame, frame_index, timestamp)
            
        except IndexError:
            pass
        except Exception as e:
            logger.error(f"VLM 采样处理失败: {e}")
        
        finally:
            self._frame_counter += 1
    
    def _call_vlm(self, frame: np.ndarray, frame_index: int, timestamp: float) -> None:
        """调用 VLM Flash API 进行检测"""
        try:
            # 方式1: 使用回调函数
            if self.vlm_callback is not None:
                detections = self.vlm_callback(frame)
            # 方式2: 使用 analyzer 实例
            elif self.analyzer is not None:
                detections = self.analyzer.analyze_with_flash(frame)
            else:
                logger.warning("VLM Sampler 未配置 analyzer 或 callback")
                detections = []
            
            # 保存检测结果
            for det in detections:
                confidence = det.get("confidence", 0.0)
                location = det.get("location", [0, 0, 0, 0])
                
                # 转换为 bbox 格式
                if len(location) == 4:
                    bbox = tuple(location)
                else:
                    bbox = (0, 0, frame.shape[1], frame.shape[0])
                
                # 根据置信度判断严重程度
                if confidence >= 0.8:
                    severity = "severe"
                elif confidence >= 0.6:
                    severity = "moderate"
                else:
                    severity = "minor"
                
                # 获取缺陷类型
                defect_type = det.get("type", "unknown")
                
                # 创建检测结果
                result = DetectionResult(
                    source=DetectionSource.VLM,
                    frame_index=frame_index,
                    timestamp=timestamp,
                    defect_type=defect_type,
                    severity=severity,
                    confidence=confidence,
                    bbox=bbox,
                    roi_crop=None,
                )
                
                # 写入结果存储
                self.result_store.add_vlm_result(result)
            
            if detections:
                logger.debug(f"VLM 采样检测到 {len(detections)} 个缺陷 (frame={frame_index})")
            
        except Exception as e:
            logger.error(f"VLM API 调用失败: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取采样线程状态"""
        return {
            "is_running": self._is_running,
            "frame_counter": self._frame_counter,
            "sample_interval": self.sample_interval,
            "total_samples": self._total_samples,
            "last_sample_time": self._last_sample_time,
        }


class AdaptiveVlmSampler(VlmSampler):
    """
    自适应 VLM 采样器
    
    根据 YOLO 的检测结果动态调整采样间隔。
    当 YOLO 置信度低时，增加采样频率。
    """
    
    def __init__(
        self,
        frame_buffer: deque,
        result_store: ResultStore,
        sample_interval: int = 30,
        analyzer=None,
        vlm_callback: Optional[Callable] = None,
        # 自适应参数
        low_confidence_threshold: float = 0.5,
        high_confidence_threshold: float = 0.8,
    ):
        super().__init__(frame_buffer, result_store, sample_interval, analyzer, vlm_callback)
        
        self.low_confidence_threshold = low_confidence_threshold
        self.high_confidence_threshold = high_confidence_threshold
        
        # 自适应采样间隔
        self._base_interval = sample_interval
        self._current_interval = sample_interval
    
    def _adjust_interval(self, avg_confidence: float) -> None:
        """根据平均置信度动态调整采样间隔"""
        if avg_confidence < self.low_confidence_threshold:
            # YOLO 置信度低，增加 VLM 采样频率
            self._current_interval = max(5, self._base_interval // 3)
        elif avg_confidence < self.high_confidence_threshold:
            # YOLO 置信度中等，保持正常采样
            self._current_interval = self._base_interval
        else:
            # YOLO 置信度高，降低 VLM 采样频率
            self._current_interval = min(120, self._base_interval * 2)
        
        # 同步到父类
        self.sample_interval = self._current_interval
    
    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status["current_interval"] = self._current_interval
        status["base_interval"] = self._base_interval
        return status
