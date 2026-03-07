"""
FabricEye 并行检测引擎 - 双路结果缓存
线程安全的结果存储，支持 YOLO 和 VLM 双路检测结果的写入和读取。
"""

import threading
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np

from app.services.parallel.types import (
    DetectionResult,
    DetectionSource,
    ReconciliationResult,
    ReconciliationStatus,
    ParallelDetectionStats,
    SampleForTraining,
)


def _default_dict():
    """创建默认字典"""
    return defaultdict(list)


def _default_stats():
    """创建默认统计信息"""
    return ParallelDetectionStats(roll_id=0)


@dataclass
class ResultStore:
    """
    双路检测结果存储器
    
    线程安全地存储 YOLO 和 VLM 的检测结果，
    支持事后交叉核对。
    """
    roll_id: int
    start_time: float = field(default_factory=time.time)
    
    # YOLO 结果缓存 (frame_index -> List[DetectionResult])
    _yolo_results: Dict[int, List[DetectionResult]] = field(default_factory=_default_dict)
    
    # VLM 结果缓存 (frame_index -> List[DetectionResult])
    _vlm_results: Dict[int, List[DetectionResult]] = field(default_factory=_default_dict)
    
    # 核对结果缓存 (frame_index -> ReconciliationResult)
    _reconciliation_results: Dict[int, ReconciliationResult] = field(default_factory=dict)
    
    # 训练样本收集
    _training_samples: List[SampleForTraining] = field(default_factory=list)
    
    # 统计信息
    _stats: ParallelDetectionStats = field(default_factory=_default_stats)
    
    # 锁
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def __post_init__(self):
        self._stats.roll_id = self.roll_id
        self._stats.start_time = self.start_time
    
    # ==================== YOLO 结果写入 ====================
    
    def add_yolo_result(self, result: DetectionResult) -> None:
        """添加 YOLO 检测结果（线程安全）"""
        with self._lock:
            frame_idx = result.frame_index
            self._yolo_results[frame_idx].append(result)
            self._stats.yolo_detections += 1
            
            # 如果该帧已有 VLM 结果，触发核对
            if frame_idx in self._vlm_results and self._vlm_results[frame_idx]:
                # 标记需要核对
                pass
    
    def get_yolo_results(self, frame_index: Optional[int] = None) -> List[DetectionResult]:
        """
        获取 YOLO 检测结果
        
        Args:
            frame_index: 指定帧索引，None 表示获取所有
            
        Returns:
            检测结果列表
        """
        with self._lock:
            if frame_index is not None:
                return list(self._yolo_results.get(frame_index, []))
            else:
                # 返回所有结果
                all_results = []
                for results in self._yolo_results.values():
                    all_results.extend(results)
                return all_results
    
    def get_all_yolo_results_by_time(self, start_time: float = 0, end_time: float = float('inf')) -> List[DetectionResult]:
        """按时间范围获取 YOLO 结果"""
        with self._lock:
            results = []
            for frame_results in self._yolo_results.values():
                for r in frame_results:
                    if start_time <= r.timestamp <= end_time:
                        results.append(r)
            return results
    
    # ==================== VLM 结果写入 ====================
    
    def add_vlm_result(self, result: DetectionResult) -> None:
        """添加 VLM 检测结果（线程安全）"""
        with self._lock:
            frame_idx = result.frame_index
            self._vlm_results[frame_idx].append(result)
            self._stats.vlm_detections += 1
            
            # 如果该帧已有 YOLO 结果，触发核对
            if frame_idx in self._yolo_results and self._yolo_results[frame_idx]:
                # 标记需要核对
                pass
    
    def get_vlm_results(self, frame_index: Optional[int] = None) -> List[DetectionResult]:
        """获取 VLM 检测结果"""
        with self._lock:
            if frame_index is not None:
                return list(self._vlm_results.get(frame_index, []))
            else:
                all_results = []
                for results in self._vlm_results.values():
                    all_results.extend(results)
                return all_results
    
    def get_all_vlm_results_by_time(self, start_time: float = 0, end_time: float = float('inf')) -> List[DetectionResult]:
        """按时间范围获取 VLM 结果"""
        with self._lock:
            results = []
            for frame_results in self._vlm_results.values():
                for r in frame_results:
                    if start_time <= r.timestamp <= end_time:
                        results.append(r)
            return results
    
    # ==================== 核对结果管理 ====================
    
    def set_reconciliation_result(self, frame_index: int, result: ReconciliationResult) -> None:
        """设置核对结果"""
        with self._lock:
            self._reconciliation_results[frame_index] = result
            
            # 更新统计
            if result.status == ReconciliationStatus.MATCHED:
                self._stats.matched_count += 1
            elif result.status == ReconciliationStatus.YOLO_ONLY:
                self._stats.yolo_only_count += 1
            elif result.status == ReconciliationStatus.VLM_ONLY:
                self._stats.vlm_only_count += 1
            elif result.status == ReconciliationStatus.REJECTED:
                self._stats.rejected_count += 1
    
    def get_reconciliation_results(self) -> List[ReconciliationResult]:
        """获取所有核对结果"""
        with self._lock:
            return list(self._reconciliation_results.values())
    
    def get_confirmed_defects(self) -> List[ReconciliationResult]:
        """获取确认的缺陷列表"""
        with self._lock:
            return [
                r for r in self._reconciliation_results.values()
                if r.is_confirmed
            ]
    
    # ==================== 训练样本管理 ====================
    
    def add_training_sample(self, sample: SampleForTraining) -> None:
        """添加训练样本"""
        with self._lock:
            self._training_samples.append(sample)
    
    def get_training_samples(self, min_samples: int = 0) -> List[SampleForTraining]:
        """获取训练样本"""
        with self._lock:
            if min_samples > 0 and len(self._training_samples) < min_samples:
                return []
            return list(self._training_samples)
    
    # ==================== 统计信息 ====================
    
    def increment_yolo_frames(self, count: int = 1) -> None:
        """增加 YOLO 处理帧数"""
        with self._lock:
            self._stats.yolo_total_frames += count
    
    def increment_vlm_samples(self, count: int = 1) -> None:
        """增加 VLM 采样次数"""
        with self._lock:
            self._stats.vlm_total_samples += count
    
    def get_stats(self) -> ParallelDetectionStats:
        """获取统计信息"""
        with self._lock:
            self._stats.end_time = time.time()
            self._stats.final_defect_count = (
                self._stats.matched_count +
                self._stats.yolo_only_count +
                self._stats.vlm_only_count
            )
            return self._stats
    
    def get_stats_dict(self) -> dict:
        """获取统计信息（字典格式）"""
        return self.get_stats().to_dict()
    
    # ==================== 帧索引范围 ====================
    
    def get_frame_range(self) -> tuple:
        """获取处理的帧索引范围"""
        with self._lock:
            yolo_frames = list(self._yolo_results.keys())
            vlm_frames = list(self._vlm_results.keys())
            
            if not yolo_frames and not vlm_frames:
                return (0, 0)
            
            all_frames = yolo_frames + vlm_frames
            return (min(all_frames), max(all_frames))
    
    def get_total_frames(self) -> int:
        """获取处理的帧总数"""
        with self._lock:
            yolo_frames = set(self._yolo_results.keys())
            vlm_frames = set(self._vlm_results.keys())
            return max(len(yolo_frames), len(vlm_frames))
    
    # ==================== 清理 ====================
    
    def clear(self) -> None:
        """清空所有结果"""
        with self._lock:
            self._yolo_results.clear()
            self._vlm_results.clear()
            self._reconciliation_results.clear()
            self._training_samples.clear()
            self._stats = ParallelDetectionStats(roll_id=self.roll_id, start_time=time.time())
    
    def get_summary(self) -> dict:
        """获取结果摘要"""
        with self._lock:
            # 直接计算确认的缺陷数量，避免死锁
            confirmed_count = sum(
                1 for r in self._reconciliation_results.values()
                if r.is_confirmed
            )
            return {
                "roll_id": self.roll_id,
                "yolo_frames": len(self._yolo_results),
                "yolo_detections": self._stats.yolo_detections,
                "vlm_samples": len(self._vlm_results),
                "vlm_detections": self._stats.vlm_detections,
                "reconciled": len(self._reconciliation_results),
                "confirmed_defects": confirmed_count,
                "training_samples": len(self._training_samples),
            }
