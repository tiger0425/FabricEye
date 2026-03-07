"""
FabricEye 并行检测引擎 - 交叉核对引擎
实现 YOLO 和 VLM 检测结果的事后交叉核对。
"""

import time
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from app.services.parallel.types import (
    DetectionResult,
    DetectionSource,
    ReconciliationResult,
    ReconciliationStatus,
)
from app.services.parallel.result_store import ResultStore

logger = logging.getLogger(__name__)


def calculate_iou(box1: Tuple[float, float, float, float], 
                  box2: Tuple[float, float, float, float]) -> float:
    """
    计算两个边界框的 IOU
    
    Args:
        box1: (x1, y1, x2, y2)
        box2: (x1, y1, x2, y2)
        
    Returns:
        IOU 值 (0-1)
    """
    # 计算交集区域
    x1_inter = max(box1[0], box2[0])
    y1_inter = max(box1[1], box2[1])
    x2_inter = min(box1[2], box2[2])
    y2_inter = min(box1[3], box2[3])
    
    if x2_inter <= x1_inter or y2_inter <= y1_inter:
        return 0.0
    
    # 计算交集面积
    inter_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
    
    # 计算各自的面积
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    
    # 计算并集面积
    union_area = area1 + area2 - inter_area
    
    if union_area == 0:
        return 0.0
    
    return inter_area / union_area


def time_difference_seconds(ts1: float, ts2: float) -> float:
    """计算时间差（秒）"""
    return abs(ts1 - ts2)


@dataclass
class ReconciliationConfig:
    """核对配置"""
    iou_threshold: float = 0.3          # IOU 匹配阈值
    time_window_seconds: float = 2.0   # 时间窗口（秒）
    confidence_weight_yolo: float = 0.6  # YOLO 置信度权重
    confidence_weight_vlm: float = 0.4   # VLM 置信度权重
    
    # 确认阈值
    high_confidence_threshold: float = 0.85  # 高置信度直接确认
    low_confidence_threshold: float = 0.3   # 低置信度直接排除


class Reconciler:
    """
    交叉核对引擎
    
    负责将 YOLO 和 VLM 的检测结果进行匹配，
    识别：matched（双方一致）、yolo_only、vlm_only。
    """
    
    def __init__(self, config: Optional[ReconciliationConfig] = None):
        self.config = config or ReconciliationConfig()
        self._matched_pairs: List[Tuple[DetectionResult, DetectionResult]] = []
    
    def reconcile_frame(self, 
                        yolo_results: List[DetectionResult],
                        vlm_results: List[DetectionResult]) -> List[ReconciliationResult]:
        """
        核对单帧的 YOLO 和 VLM 结果
        
        Args:
            yolo_results: YOLO 检测结果列表
            vlm_results: VLM 检测结果列表
            
        Returns:
            核对结果列表
        """
        results = []
        
        # 情况1: 双方都有结果 -> 尝试匹配
        if yolo_results and vlm_results:
            matched_yolo = set()
            matched_vlm = set()
            
            # 按置信度排序
            sorted_yolo = sorted(yolo_results, key=lambda x: x.confidence, reverse=True)
            sorted_vlm = sorted(vlm_results, key=lambda x: x.confidence, reverse=True)
            
            # 贪心匹配
            for yolo_det in sorted_yolo:
                best_match = None
                best_iou = 0
                best_vlm_idx = -1
                
                for i, vlm_det in enumerate(sorted_vlm):
                    if i in matched_vlm:
                        continue
                    
                    # 检查时间窗口
                    time_diff = time_difference_seconds(yolo_det.timestamp, vlm_det.timestamp)
                    if time_diff > self.config.time_window_seconds:
                        continue
                    
                    # 计算 IOU
                    iou = calculate_iou(yolo_det.bbox, vlm_det.bbox)
                    
                    if iou >= self.config.iou_threshold and iou > best_iou:
                        best_iou = iou
                        best_match = vlm_det
                        best_vlm_idx = i
                
                if best_match is not None and best_vlm_idx >= 0:
                    matched_yolo.add(id(yolo_det))
                    matched_vlm.add(best_vlm_idx)
                    
                    # 双方一致 -> 计算融合置信度
                    final_confidence = (
                        self.config.confidence_weight_yolo * yolo_det.confidence +
                        self.config.confidence_weight_vlm * best_match.confidence
                    )
                    
                    # 优先信任 YOLO 的分类（假设 YOLO 更准）
                    final_defect_type = yolo_det.defect_type
                    final_severity = yolo_det.severity
                    final_bbox = yolo_det.bbox
                    
                    result = ReconciliationResult(
                        yolo_result=yolo_det,
                        vlm_result=best_match,
                        status=ReconciliationStatus.MATCHED,
                        final_confidence=final_confidence,
                        final_defect_type=final_defect_type,
                        final_severity=final_severity,
                        final_bbox=final_bbox,
                    )
                    results.append(result)
            
            # 处理未匹配的 YOLO 结果 -> YOLO独有
            for yolo_det in sorted_yolo:
                if id(yolo_det) not in matched_yolo:
                    result = ReconciliationResult(
                        yolo_result=yolo_det,
                        vlm_result=None,
                        status=ReconciliationStatus.YOLO_ONLY,
                        final_confidence=yolo_det.confidence,
                        final_defect_type=yolo_det.defect_type,
                        final_severity=yolo_det.severity,
                        final_bbox=yolo_det.bbox,
                    )
                    results.append(result)
            
            # 处理未匹配的 VLM 结果 -> VLM独有（YOLO漏检）
            for i, vlm_det in enumerate(sorted_vlm):
                if i not in matched_vlm:
                    result = ReconciliationResult(
                        yolo_result=None,
                        vlm_result=vlm_det,
                        status=ReconciliationStatus.VLM_ONLY,
                        final_confidence=vlm_det.confidence,
                        final_defect_type=vlm_det.defect_type,
                        final_severity=vlm_det.severity,
                        final_bbox=vlm_det.bbox,
                    )
                    results.append(result)
        
        # 情况2: 仅 YOLO 有结果
        elif yolo_results and not vlm_results:
            for yolo_det in yolo_results:
                result = ReconciliationResult(
                    yolo_result=yolo_det,
                    vlm_result=None,
                    status=ReconciliationStatus.YOLO_ONLY,
                    final_confidence=yolo_det.confidence,
                    final_defect_type=yolo_det.defect_type,
                    final_severity=yolo_det.severity,
                    final_bbox=yolo_det.bbox,
                )
                results.append(result)
        
        # 情况3: 仅 VLM 有结果
        elif not yolo_results and vlm_results:
            for vlm_det in vlm_results:
                result = ReconciliationResult(
                    yolo_result=None,
                    vlm_result=vlm_det,
                    status=ReconciliationStatus.VLM_ONLY,
                    final_confidence=vlm_det.confidence,
                    final_defect_type=vlm_det.defect_type,
                    final_severity=vlm_det.severity,
                    final_bbox=vlm_det.bbox,
                )
                results.append(result)
        
        # 情况4: 双方都无结果 -> 无需处理
        
        return results
    
    def reconcile_all(self, result_store: ResultStore) -> List[ReconciliationResult]:
        """
        核对所有缓存的结果
        
        Args:
            result_store: 结果存储器
            
        Returns:
            所有核对结果
        """
        all_results = []
        
        # 获取帧索引范围
        frame_range = result_store.get_frame_range()
        start_frame, end_frame = frame_range
        
        logger.info(f"开始交叉核对，帧范围: {start_frame} - {end_frame}")
        
        # 遍历每一帧
        for frame_idx in range(start_frame, end_frame + 1):
            yolo_results = result_store.get_yolo_results(frame_idx)
            vlm_results = result_store.get_vlm_results(frame_idx)
            
            # 核对该帧
            frame_results = self.reconcile_frame(yolo_results, vlm_results)
            
            # 存储核对结果
            for result in frame_results:
                result_store.set_reconciliation_result(frame_idx, result)
                all_results.append(result)
        
        logger.info(f"交叉核对完成，共 {len(all_results)} 个结果")
        
        # 统计各类结果
        matched = sum(1 for r in all_results if r.status == ReconciliationStatus.MATCHED)
        yolo_only = sum(1 for r in all_results if r.status == ReconciliationStatus.YOLO_ONLY)
        vlm_only = sum(1 for r in all_results if r.status == ReconciliationStatus.VLM_ONLY)
        
        logger.info(f"核对结果: 匹配={matched}, YOLO独有={yolo_only}, VLM独有={vlm_only}")
        
        return all_results
    
    def get_vlm_only_for_review(self, result_store: ResultStore) -> List[ReconciliationResult]:
        """
        获取需要 VLM Plus 复检的结果（VLM独有）
        
        Args:
            result_store: 结果存储器
            
        Returns:
            VLM独有结果列表（需要复检）
        """
        reconciliation_results = result_store.get_reconciliation_results()
        
        return [
            r for r in reconciliation_results
            if r.status == ReconciliationStatus.VLM_ONLY
        ]
    
    def get_confirmed_results(self, result_store: ResultStore) -> List[ReconciliationResult]:
        """
        获取确认的缺陷列表（排除 VLM独有待复检的）
        
        Args:
            result_store: 结果存储器
            
        Returns:
            确认的缺陷列表
        """
        return result_store.get_confirmed_defects()
    
    def get_summary(self, result_store: ResultStore) -> dict:
        """
        获取核对摘要
        
        Args:
            result_store: 结果存储器
            
        Returns:
            摘要字典
        """
        all_results = result_store.get_reconciliation_results()
        
        matched = sum(1 for r in all_results if r.status == ReconciliationStatus.MATCHED)
        yolo_only = sum(1 for r in all_results if r.status == ReconciliationStatus.YOLO_ONLY)
        vlm_only = sum(1 for r in all_results if r.status == ReconciliationStatus.VLM_ONLY)
        rejected = sum(1 for r in all_results if r.status == ReconciliationStatus.REJECTED)
        
        return {
            "total": len(all_results),
            "matched": matched,
            "yolo_only": yolo_only,
            "vlm_only": vlm_only,
            "rejected": rejected,
            "confirmed": matched + yolo_only,
            "needs_review": vlm_only,
        }
