"""
FabricEye 并行检测引擎 - 主控制器
协调 YOLO 和 VLM 双路并行检测，以及事后交叉核对。
"""

import os
import asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import deque

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.video_capture import VideoCaptureService
from app.services.ai_analyzer import AIAnalyzerService
from app.models.video import Video, VideoStatus
from app.models.defect import Defect, DefectType, DefectSeverity

from app.services.parallel.types import (
    DetectionSource,
    ReconciliationStatus,
    ReconciliationResult,
    SampleForTraining,
    ParallelDetectionStats,
)
from app.services.parallel.result_store import ResultStore
from app.services.parallel.reconciler import Reconciler, ReconciliationConfig
from app.services.parallel.yolo_worker import YoloWorker
from app.services.parallel.vlm_sampler import VlmSampler, AdaptiveVlmSampler

logger = logging.getLogger(__name__)


class ParallelEngine:
    """
    并行检测引擎主控制器
    
    协调 YOLO 和 VLM 双路并行检测：
    - 检测阶段：YOLO 逐帧 + VLM 采样
    - 核对阶段：事后交叉核对
    - 复检阶段：VLM Plus 复检漏检
    """
    
    def __init__(self, roll_id: int):
        self.roll_id = roll_id
        
        # 视频服务
        self.video_service = VideoCaptureService()
        
        # AI 分析服务
        self.analyzer = AIAnalyzerService()
        
        # 共享帧缓冲区
        self.frame_buffer: deque = deque(maxlen=settings.FRAME_BUFFER_SIZE)
        
        # 结果存储
        self.result_store = ResultStore(roll_id=roll_id)
        
        # 核对配置
        self.reconciler_config = ReconciliationConfig(
            iou_threshold=settings.RECONCILE_IOU_THRESHOLD,
            time_window_seconds=settings.RECONCILE_TIME_WINDOW,
        )
        self.reconciler = Reconciler(self.reconciler_config)
        
        # 工作线程
        self._yolo_worker: Optional[YoloWorker] = None
        self._vlm_sampler: Optional[VlmSampler] = None
        self._capture_worker: Optional[threading.Thread] = None
        
        # 状态
        self.is_running = False
        self.video_path: Optional[str] = None
        self.video_id: Optional[int] = None
        self.recording_start_time: Optional[float] = None
        
        # 配置
        self._load_config()
    
    def _load_config(self) -> None:
        """从配置加载参数"""
        # YOLO 配置
        self.yolo_model_path = getattr(settings, 'YOLO_MODEL_PATH', 'models/yolov11s_fabric.pt')
        self.yolo_confidence = getattr(settings, 'YOLO_CONFIDENCE', 0.5)
        self.yolo_skip_frames = getattr(settings, 'YOLO_SKIP_FRAMES', 0)
        
        # VLM 配置
        self.vlm_sample_interval = getattr(settings, 'VLM_SAMPLE_INTERVAL', 30)
        self.use_adaptive_sampling = getattr(settings, 'USE_ADAPTIVE_SAMPLING', False)
        
        # 核对配置
        self.reconciler_config.iou_threshold = getattr(settings, 'RECONCILE_IOU_THRESHOLD', 0.3)
        self.reconciler_config.time_window_seconds = getattr(settings, 'RECONCILE_TIME_WINDOW', 2.0)
        
        logger.info(f"ParallelEngine 配置加载完成: YOLO={self.yolo_model_path}, VLM间隔={self.vlm_sample_interval}")
    
    async def start(self) -> bool:
        """
        启动并行检测引擎
        
        Returns:
            是否启动成功
        """
        if self.is_running:
            logger.warning("ParallelEngine 已在运行")
            return True
        
        # 初始化视频采集
        if not self.video_service.start_capture():
            logger.error("视频采集启动失败")
            return False
        
        # 初始化 AI 分析服务
        self.analyzer.load_model()
        
        # 初始化视频录制
        await self._init_video_recording()
        
        # 启动帧采集线程
        self._start_capture_worker()
        
        # 启动 YOLO 检测线程
        self._yolo_worker = YoloWorker(
            frame_buffer=self.frame_buffer,
            result_store=self.result_store,
            model_path=self.yolo_model_path,
            confidence_threshold=self.yolo_confidence,
            skip_frames=self.yolo_skip_frames,
        )
        self._yolo_worker.start(self.roll_id)
        
        # 启动 VLM 采样线程
        if self.use_adaptive_sampling:
            self._vlm_sampler = AdaptiveVlmSampler(
                frame_buffer=self.frame_buffer,
                result_store=self.result_store,
                sample_interval=self.vlm_sample_interval,
                analyzer=self.analyzer,
            )
        else:
            self._vlm_sampler = VlmSampler(
                frame_buffer=self.frame_buffer,
                result_store=self.result_store,
                sample_interval=self.vlm_sample_interval,
                analyzer=self.analyzer,
            )
        self._vlm_sampler.start(self.roll_id)
        
        self.is_running = True
        logger.info(f"ParallelEngine 启动成功 (roll_id={self.roll_id})")
        return True
    
    def stop(self) -> None:
        """停止并行检测引擎"""
        if not self.is_running:
            return
        
        logger.info("正在停止 ParallelEngine...")
        self.is_running = False
        
        # 停止工作线程
        if self._yolo_worker:
            self._yolo_worker.stop()
        
        if self._vlm_sampler:
            self._vlm_sampler.stop()
        
        # 停止帧采集
        self._stop_capture_worker()
        
        # 保存视频信息
        if self.video_id:
            try:
                loop = asyncio.get_event_loop()
                asyncio.run_coroutine_threadsafe(self._save_video_info(), loop)
            except Exception as e:
                logger.error(f"保存视频信息失败: {e}")
        
        logger.info("ParallelEngine 已停止")
    
    async def stop_and_reconcile(self) -> Dict[str, Any]:
        """
        停止引擎并执行交叉核对
        
        Returns:
            核对结果统计
        """
        # 停止双路检测
        self.stop()
        
        # 执行交叉核对
        logger.info("开始执行交叉核对...")
        reconciliation_results = self.reconciler.reconcile_all(self.result_store)
        
        # 获取统计信息
        stats = self.result_store.get_stats_dict()
        
        # 保存确认的缺陷到数据库
        await self._save_confirmed_defects(reconciliation_results)
        
        # 收集训练样本
        await self._collect_training_samples(reconciliation_results)
        
        logger.info(f"交叉核对完成: {stats}")
        
        return stats
    
    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        yolo_status = self._yolo_worker.get_status() if self._yolo_worker else {}
        vlm_status = self._vlm_sampler.get_status() if self._vlm_sampler else {}
        store_summary = self.result_store.get_summary()
        recon_summary = self.reconciler.get_summary(self.result_store)
        
        return {
            "is_running": self.is_running,
            "roll_id": self.roll_id,
            "video_id": self.video_id,
            "yolo": yolo_status,
            "vlm": vlm_status,
            "store": store_summary,
            "reconciliation": recon_summary,
        }
    
    # ==================== 私有方法 ====================
    
    async def _init_video_recording(self) -> None:
        """初始化视频录制"""
        timestamp = int(time.time())
        video_dir = "storage/videos"
        os.makedirs(video_dir, exist_ok=True)
        self.video_path = os.path.join(video_dir, f"roll_{self.roll_id}_{timestamp}.mp4")
        self.recording_start_time = time.time()
        
        async with SessionLocal() as session:
            v = Video(
                roll_id=self.roll_id,
                file_path=self.video_path,
                status=VideoStatus.RECORDING,
                started_at=datetime.utcnow()
            )
            session.add(v)
            await session.commit()
            await session.refresh(v)
            self.video_id = v.id
            logger.info(f"视频录制初始化成功: video_id={self.video_id}")
    
    async def _save_video_info(self) -> None:
        """保存视频元数据"""
        if not self.video_id:
            return
        
        duration = time.time() - self.recording_start_time if self.recording_start_time else 0
        file_size = os.path.getsize(self.video_path) if self.video_path and os.path.exists(self.video_path) else 0
        
        async with SessionLocal() as session:
            from sqlalchemy import select
            res = await session.execute(select(Video).where(Video.id == self.video_id))
            v = res.scalar_one_or_none()
            if v:
                v.status = VideoStatus.COMPLETED
                v.duration_seconds = duration
                v.file_size = file_size
                v.completed_at = datetime.utcnow()
                await session.commit()
                logger.info(f"视频信息已保存: duration={duration:.2f}s, size={file_size}")
    
    def _start_capture_worker(self) -> None:
        """启动帧采集工作线程"""
        def capture_loop():
            while self.is_running:
                try:
                    frame = self.video_service.get_frame()
                    if frame is not None:
                        timestamp = time.time()
                        self.frame_buffer.append((0, frame, timestamp))
                except Exception as e:
                    logger.error(f"帧采集错误: {e}")
                time.sleep(1 / 60)  # 60 FPS
        
        self._capture_worker = threading.Thread(target=capture_loop, daemon=True)
        self._capture_worker.start()
    
    def _stop_capture_worker(self) -> None:
        """停止帧采集工作线程"""
        self.video_service.stop_capture()
        if self._capture_worker:
            self._capture_worker.join(timeout=2)
    
    async def _save_confirmed_defects(self, results: List[ReconciliationResult]) -> None:
        """将确认的缺陷保存到数据库"""
        confirmed = [r for r in results if r.is_confirmed]
        
        async with SessionLocal() as session:
            for result in confirmed:
                try:
                    # 获取缺陷类型枚举
                    defect_type = self._get_defect_type(result.final_defect_type)
                    severity = self._get_severity(result.final_severity)
                    
                    defect = Defect(
                        roll_id=self.roll_id,
                        video_id=self.video_id,
                        defect_type=defect_type,
                        defect_type_cn=self._get_defect_cn(result.final_defect_type),
                        confidence=result.final_confidence,
                        severity=severity,
                        timestamp=result.vlm_result.timestamp if result.vlm_result else (
                            result.yolo_result.timestamp if result.yolo_result else 0
                        ),
                        bbox_x1=result.final_bbox[0],
                        bbox_y1=result.final_bbox[1],
                        bbox_x2=result.final_bbox[2],
                        bbox_y2=result.final_bbox[3],
                    )
                    session.add(defect)
                except Exception as e:
                    logger.error(f"保存缺陷失败: {e}")
            
            await session.commit()
            logger.info(f"已保存 {len(confirmed)} 个缺陷到数据库")
    
    async def _collect_training_samples(self, results: List[ReconciliationResult]) -> None:
        """收集训练样本"""
        confirmed = [r for r in results if r.is_confirmed]
        
        for i, result in enumerate(confirmed):
            # 确定数据来源
            source = DetectionSource.BOTH if result.yolo_result and result.vlm_result else (
                DetectionSource.YOLO if result.yolo_result else DetectionSource.VLM
            )
            
            # 创建训练样本
            timestamp = result.vlm_result.timestamp if result.vlm_result else (
                result.yolo_result.timestamp if result.yolo_result else 0
            )
            frame_index = result.vlm_result.frame_index if result.vlm_result else (
                result.yolo_result.frame_index if result.yolo_result else 0
            )
            
            sample = SampleForTraining(
                cascade_id=i + 1,
                frame_index=frame_index,
                timestamp=timestamp,
                defect_type=result.final_defect_type,
                severity=result.final_severity,
                bbox=result.final_bbox,
                roi_image_path=f"storage/training_samples/roll_{self.roll_id}_sample_{i}.jpg",
                source=source,
            )
            
            self.result_store.add_training_sample(sample)
        
        logger.info(f"已收集 {len(confirmed)} 个训练样本")
    
    def _get_defect_type(self, defect_type: str) -> DefectType:
        """获取缺陷类型枚举"""
        try:
            return DefectType(defect_type)
        except ValueError:
            # 使用 fallback 方式获取 UNKNOWN
            return DefectType("unknown")
    
    def _get_severity(self, severity: str) -> DefectSeverity:
        """获取严重程度枚举"""
        try:
            return DefectSeverity(severity)
        except ValueError:
            return DefectSeverity.MINOR
    
    def _get_defect_cn(self, defect_type: str) -> str:
        """获取缺陷中文名称"""
        from app.services.parallel.types import DEFECT_CLASSES_CN
        return DEFECT_CLASSES_CN.get(defect_type, "未知")
