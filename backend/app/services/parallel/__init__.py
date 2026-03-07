"""
FabricEye 并行检测引擎

提供 YOLO + VLM 双路并行检测能力。
支持渐进式数据积累策略：前期以 VLM 为主，后期以 YOLO 为主。

模块结构：
- engine.ParallelEngine: 主控制器
- yolo_worker.YoloWorker: YOLO 检测线程
- vlm_sampler.VlmSampler: VLM 采样线程
- reconciler.Reconciler: 交叉核对引擎
- result_store.ResultStore: 结果缓存
- types: 数据类型定义

使用示例：
```python
from app.services.parallel import ParallelEngine

# 创建引擎
engine = ParallelEngine(roll_id=1)

# 启动并行检测
await engine.start()

# ... 检测进行中 ...

# 停止并执行交叉核对
stats = await engine.stop_and_reconcile()
print(stats)
```
"""

from app.services.parallel.engine import ParallelEngine
from app.services.parallel.yolo_worker import YoloWorker, YoloDetector
from app.services.parallel.vlm_sampler import VlmSampler, AdaptiveVlmSampler
from app.services.parallel.reconciler import Reconciler, ReconciliationConfig
from app.services.parallel.result_store import ResultStore
from app.services.parallel.types import (
    DetectionSource,
    ReconciliationStatus,
    DefectType,
    DefectSeverity,
    DetectionResult,
    ReconciliationResult,
    ParallelDetectionStats,
    SampleForTraining,
    DEFECT_CLASSES,
    DEFECT_CLASSES_CN,
)

__all__ = [
    # 引擎
    "ParallelEngine",
    
    # 组件
    "YoloWorker",
    "YoloDetector",
    "VlmSampler",
    "AdaptiveVlmSampler",
    "Reconciler",
    "ReconciliationConfig",
    "ResultStore",
    
    # 类型
    "DetectionSource",
    "ReconciliationStatus",
    "DefectType",
    "DefectSeverity",
    "DetectionResult",
    "ReconciliationResult",
    "ParallelDetectionStats",
    "SampleForTraining",
    
    # 常量
    "DEFECT_CLASSES",
    "DEFECT_CLASSES_CN",
]
