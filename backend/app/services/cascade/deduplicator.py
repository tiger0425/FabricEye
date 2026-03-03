"""
FabricEye 级联检测引擎 - 去重器
基于IOU（交并比）的检测结果去重算法。
"""

from typing import List, Tuple


class DetectionDeduplicator:
    """基于IOU和时序窗口的检测去重器。"""
    
    def __init__(self, iou_threshold: float, time_window: float):
        self.iou_threshold = iou_threshold
        self.time_window = time_window
        self._recent: List[Tuple[tuple, float]] = []

    def is_duplicate(self, bbox: tuple, timestamp: float) -> bool:
        """检查是否为重复检测。"""
        self._prune(timestamp)
        for prev_bbox, _ in self._recent:
            if self._compute_iou(bbox, prev_bbox) >= self.iou_threshold:
                return True
        return False

    def add_detection(self, bbox: tuple, timestamp: float) -> None:
        """添加新的检测结果。"""
        self._prune(timestamp)
        self._recent.append((bbox, timestamp))

    def _prune(self, now: float) -> None:
        """清理过期的历史记录。"""
        cutoff = now - self.time_window
        self._recent = [(b, t) for b, t in self._recent if t >= cutoff]

    @staticmethod
    def _compute_iou(box1: tuple, box2: tuple) -> float:
        """计算两个边界框的IOU。"""
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
