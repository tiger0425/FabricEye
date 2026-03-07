"""
FabricEye 并行检测引擎 - Plus 复检器
对 YOLO 漏检项（VLM独有结果）进行 VLM Plus 精准复核。
"""

import threading
import logging
import time
from typing import List, Optional, Dict, Any, Callable
import numpy as np
import cv2

from app.services.parallel.types import (
    DetectionResult,
    DetectionSource,
    ReconciliationResult,
    ReconciliationStatus,
)
from app.services.parallel.result_store import ResultStore

logger = logging.getLogger(__name__)


class PlusReviewer:
    """
    Plus 复检器
    
    负责对 YOLO 漏检项（VLM独有结果）进行 VLM Plus 精准复核。
    复用现有的 ai_analyzer.py 中的 Plus API 调用逻辑。
    """
    
    def __init__(
        self,
        result_store: ResultStore,
        analyzer=None,  # AIAnalyzerService 实例
        plus_callback: Optional[Callable] = None,  # Plus 调用回调
        # 复检配置
        review_threshold: float = 0.3,  # 低于此阈值才送复检
        batch_size: int = 10,  # 批量复检大小
    ):
        self.result_store = result_store
        self.analyzer = analyzer
        self.plus_callback = plus_callback
        self.review_threshold = review_threshold
        self.batch_size = batch_size
        
        # 线程控制
        self._thread: Optional[threading.Thread] = None
        self._is_running = False
        
        # 统计
        self._total_reviewed = 0
        self._total_confirmed = 0
        self._total_rejected = 0
    
    def start(self) -> bool:
        """启动 Plus 复检线程"""
        if self._is_running:
            return True
        
        self._is_running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        logger.info("Plus Reviewer 启动成功")
        return True
    
    def stop(self) -> None:
        """停止 Plus 复检线程"""
        self._is_running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info(f"Plus Reviewer 已停止，共复检 {self._total_reviewed} 项")
    
    def _run(self) -> None:
        """Plus 复检主循环"""
        while self._is_running:
            try:
                self._process_review()
            except Exception as e:
                logger.error(f"Plus 复检错误: {e}")
            
            time.sleep(0.5)  # 定期检查待复检项
    
    def _process_review(self) -> None:
        """处理待复检项"""
        # 获取 VLM 独有结果（需要复检的）
        vlm_only_results = self._get_pending_review_results()
        
        if not vlm_only_results:
            return
        
        # 批量处理
        batch = vlm_only_results[:self.batch_size]
        
        for reconciliation_result in batch:
            self._review_single(reconciliation_result)
    
    def _get_pending_review_results(self) -> List[ReconciliationResult]:
        """获取需要复检的结果"""
        all_results = self.result_store.get_reconciliation_results()
        
        # 筛选 VLM独有 且置信度低于阈值的
        pending = [
            r for r in all_results
            if r.status == ReconciliationStatus.VLM_ONLY
            and r.final_confidence < self.review_threshold
        ]
        
        return pending
    
    def _review_single(self, reconciliation_result: ReconciliationResult) -> None:
        """复检单个结果"""
        self._total_reviewed += 1
        
        # 获取 VLM 结果
        vlm_result = reconciliation_result.vlm_result
        if not vlm_result or vlm_result.roi_crop is None:
            logger.warning(f"复检项缺少 ROI 图像: frame={vlm_result.frame_index if vlm_result else 'N/A'}")
            return
        
        try:
            # 调用 VLM Plus 进行精准分析
            plus_results = self._call_plus(vlm_result.roi_crop)
            
            if not plus_results:
                # Plus 返回空，排除
                reconciliation_result.status = ReconciliationStatus.REJECTED
                self._total_rejected += 1
                logger.info(f"Plus 复检排除: frame={vlm_result.frame_index}")
                return
            
            # 获取最高置信度的结果
            best_result = max(plus_results, key=lambda x: x.get("confidence", 0))
            plus_confidence = best_result.get("confidence", 0)
            
            # 判断是否确认为缺陷
            if plus_confidence >= self.review_threshold:
                # 确认
                reconciliation_result.status = ReconciliationStatus.MATCHED
                reconciliation_result.final_confidence = plus_confidence
                reconciliation_result.final_defect_type = best_result.get("type", vlm_result.defect_type)
                reconciliation_result.final_severity = best_result.get("severity", vlm_result.severity)
                self._total_confirmed += 1
                logger.info(f"Plus 复检确认: frame={vlm_result.frame_index}, confidence={plus_confidence:.2f}")
            else:
                # 排除
                reconciliation_result.status = ReconciliationStatus.REJECTED
                self._total_rejected += 1
                logger.info(f"Plus 复检排除: frame={vlm_result.frame_index}")
            
            # 更新结果存储
            self.result_store.set_reconciliation_result(
                vlm_result.frame_index,
                reconciliation_result
            )
            
        except Exception as e:
            logger.error(f"Plus 复检失败: {e}")
            # 出错时保留原状态
    
    def _call_plus(self, roi_crop: np.ndarray) -> List[Dict[str, Any]]:
        """调用 VLM Plus API"""
        try:
            # 方式1: 使用回调函数
            if self.plus_callback is not None:
                return self.plus_callback(roi_crop)
            # 方式2: 使用 analyzer 实例
            elif self.analyzer is not None:
                return self.analyzer.analyze_with_plus(roi_crop)
            else:
                logger.warning("Plus Reviewer 未配置 analyzer 或 callback")
                return []
        except Exception as e:
            logger.error(f"VLM Plus API 调用失败: {e}")
            return []
    
    def review_all(self, reconciliation_results: List[ReconciliationResult]) -> None:
        """
        同步复检所有结果（用于事后批量处理）
        
        Args:
            reconciliation_results: 核对结果列表
        """
        # 筛选需要复检的
        to_review = [
            r for r in reconciliation_results
            if r.status == ReconciliationStatus.VLM_ONLY
        ]
        
        logger.info(f"开始 Plus 复检，共 {len(to_review)} 项")
        
        for result in to_review:
            self._review_single(result)
        
        logger.info(f"Plus 复检完成: 确认={self._total_confirmed}, 排除={self._total_rejected}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取复检器状态"""
        return {
            "is_running": self._is_running,
            "total_reviewed": self._total_reviewed,
            "total_confirmed": self._total_confirmed,
            "total_rejected": self._total_rejected,
            "review_threshold": self.review_threshold,
            "batch_size": self.batch_size,
        }


class AdaptivePlusReviewer(PlusReviewer):
    """
    自适应 Plus 复检器
    
    根据 VLM 独有结果的数量动态调整复检策略。
    """
    
    def __init__(
        self,
        result_store: ResultStore,
        analyzer=None,
        plus_callback: Optional[Callable] = None,
        review_threshold: float = 0.3,
        batch_size: int = 10,
        # 自适应参数
        max_review_per_batch: int = 50,  # 每批最大复检数
        min_review_interval: float = 0.1,  # 最小复检间隔
    ):
        super().__init__(result_store, analyzer, plus_callback, review_threshold, batch_size)
        
        self.max_review_per_batch = max_review_per_batch
        self.min_review_interval = min_review_interval
    
    def _process_review(self) -> None:
        """自适应处理复检"""
        # 获取 VLM 独有结果
        vlm_only_results = self._get_pending_review_results()
        
        if not vlm_only_results:
            return
        
        # 动态调整批量大小
        pending_count = len(vlm_only_results)
        
        if pending_count > 100:
            # 待复检项很多，加快处理
            current_batch_size = min(self.max_review_per_batch, pending_count)
            self.batch_size = current_batch_size
        elif pending_count > 20:
            # 正常处理
            self.batch_size = self.batch_size
        else:
            # 待复检项少，放慢处理
            self.batch_size = max(1, pending_count)
        
        # 批量处理
        batch = vlm_only_results[:self.batch_size]
        
        for reconciliation_result in batch:
            self._review_single(reconciliation_result)
            time.sleep(self.min_review_interval)  # 控制复检频率
    
    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status["max_review_per_batch"] = self.max_review_per_batch
        status["min_review_interval"] = self.min_review_interval
        return status
