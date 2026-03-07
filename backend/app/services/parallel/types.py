"""
FabricEye 并行检测引擎 - 数据类型定义
定义 YOLO + VLM 双路检测的数据结构。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import numpy as np


class DetectionSource(str, Enum):
    """检测来源枚举"""
    YOLO = "yolo"
    VLM = "vlm"
    BOTH = "both"  # 交叉核对确认


class ReconciliationStatus(str, Enum):
    """交叉核对状态枚举"""
    PENDING = "pending"       # 待核对
    MATCHED = "matched"       # 双方一致
    YOLO_ONLY = "yolo_only"  # 仅 YOLO 发现
    VLM_ONLY = "vlm_only"     # 仅 VLM 发现（YOLO 漏检）
    REJECTED = "rejected"     # 复核排除


class DefectType(str, Enum):
    """缺陷类型枚举（与 VLM 分类对齐）"""
    HOLE = "hole"                       # 破洞
    STAIN = "stain"                     # 污渍
    COLOR_VARIANCE = "color_variance"   # 色差
    WARP_BREAK = "warp_break"           # 断经
    WEFT_BREAK = "weft_break"           # 断纬
    FOREIGN_MATTER = "foreign_matter"   # 异物
    CREASE = "crease"                   # 折痕
    SNAG = "snag"                       # 抽丝
    UNKNOWN = "unknown"                  # 未知
    MISSED = "missed"                   # 漏检（VLM 发现但 YOLO 未发现）


class DefectSeverity(str, Enum):
    """缺陷严重程度枚举"""
    MINOR = "minor"       # 轻微
    MODERATE = "moderate"  # 中等
    SEVERE = "severe"     # 严重


# YOLO 缺陷类别映射（与 VLM 分类对齐）
DEFECT_CLASSES = {
    0: "hole",
    1: "stain",
    2: "color_variance",
    3: "warp_break",
    4: "weft_break",
    5: "foreign_matter",
    6: "crease",
    7: "snag",
}

DEFECT_CLASSES_CN = {
    "hole": "破洞",
    "stain": "污渍",
    "color_variance": "色差",
    "warp_break": "断经",
    "weft_break": "断纬",
    "foreign_matter": "异物",
    "crease": "折痕",
    "snag": "抽丝",
    "unknown": "未知",
}


@dataclass
class DetectionResult:
    """单次检测结果"""
    source: DetectionSource          # 检测来源
    frame_index: int                # 帧索引
    timestamp: float                # 时间戳（秒）
    defect_type: str                # 缺陷类型
    severity: str                   # 严重程度
    confidence: float               # 置信度 (0-1)
    bbox: tuple                    # 边界框 (x1, y1, x2, y2)
    roi_crop: Optional[np.ndarray]  # ROI 裁剪图像
    location: Optional[List[int]] = None  # 位置 [x1, y1, x2, y2]
    
    def __post_init__(self):
        if self.location is None and self.bbox:
            self.location = list(self.bbox)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source": self.source.value,
            "frame_index": self.frame_index,
            "timestamp": self.timestamp,
            "defect_type": self.defect_type,
            "severity": self.severity,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "location": self.location,
        }


@dataclass
class ReconciliationResult:
    """交叉核对结果"""
    yolo_result: Optional[DetectionResult] = None
    vlm_result: Optional[DetectionResult] = None
    status: ReconciliationStatus = ReconciliationStatus.PENDING
    final_confidence: float = 0.0
    final_defect_type: str = "unknown"
    final_severity: str = "minor"
    final_bbox: tuple = (0, 0, 0, 0)
    
    @property
    def is_matched(self) -> bool:
        """是否匹配成功"""
        return self.status in [
            ReconciliationStatus.MATCHED,
            ReconciliationStatus.YOLO_ONLY,
            ReconciliationStatus.VLM_ONLY,
        ]
    
    @property
    def is_confirmed(self) -> bool:
        """是否确认缺陷（排除误报）"""
        return self.status in [
            ReconciliationStatus.MATCHED,
            ReconciliationStatus.YOLO_ONLY,
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status.value,
            "final_confidence": self.final_confidence,
            "final_defect_type": self.final_defect_type,
            "final_severity": self.final_severity,
            "final_bbox": self.final_bbox,
            "yolo_result": self.yolo_result.to_dict() if self.yolo_result else None,
            "vlm_result": self.vlm_result.to_dict() if self.vlm_result else None,
        }


@dataclass
class ParallelDetectionStats:
    """并行检测统计信息"""
    roll_id: int
    start_time: float = 0.0
    end_time: float = 0.0
    
    # YOLO 统计
    yolo_total_frames: int = 0
    yolo_detections: int = 0
    
    # VLM 统计
    vlm_total_samples: int = 0
    vlm_detections: int = 0
    
    # 核对统计
    matched_count: int = 0
    yolo_only_count: int = 0
    vlm_only_count: int = 0
    rejected_count: int = 0
    
    # 最终结果
    final_defect_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        duration = self.end_time - self.start_time if self.end_time > 0 else 0
        return {
            "roll_id": self.roll_id,
            "duration_seconds": round(duration, 2),
            "yolo": {
                "total_frames": self.yolo_total_frames,
                "detections": self.yolo_detections,
            },
            "vlm": {
                "total_samples": self.vlm_total_samples,
                "detections": self.vlm_detections,
            },
            "reconciliation": {
                "matched": self.matched_count,
                "yolo_only": self.yolo_only_count,
                "vlm_only": self.vlm_only_count,
                "rejected": self.rejected_count,
            },
            "final_defect_count": self.final_defect_count,
        }


@dataclass
class SampleForTraining:
    """训练样本（用于 YOLO 增量训练）"""
    cascade_id: int                 #  cascade ID
    frame_index: int               # 帧索引
    timestamp: float               # 时间戳
    defect_type: str               # 缺陷类型
    severity: str                  # 严重程度
    bbox: tuple                   # 边界框
    roi_image_path: str            # ROI 图像路径
    source: DetectionSource       # 数据来源
    verified_at: datetime = field(default_factory=datetime.utcnow)
    used_for_training: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "cascade_id": self.cascade_id,
            "frame_index": self.frame_index,
            "timestamp": self.timestamp,
            "defect_type": self.defect_type,
            "severity": self.severity,
            "bbox": self.bbox,
            "roi_image_path": self.roi_image_path,
            "source": self.source.value,
            "verified_at": self.verified_at.isoformat(),
            "used_for_training": self.used_for_training,
        }
