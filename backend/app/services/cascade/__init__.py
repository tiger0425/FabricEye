"""
FabricEye 级联检测引擎包
Flash + Plus 双阶段检测流水线

向后兼容: 原有从 cascade_engine 导入的代码仍然可用
"""

# 数据类型
from app.services.cascade.types import PendingDefect

# 核心组件
from app.services.cascade.deduplicator import DetectionDeduplicator
from app.services.cascade.video_writer import AsyncVideoWriter
from app.services.cascade.image_processor import get_vlm_roi

# 工具函数
from app.services.cascade.timestamp import calculate_relative_timestamp, format_timestamp
from app.services.cascade.bbox_utils import location_to_bbox, is_valid_location, format_position

# 工作线程
from app.services.cascade.capture_worker import CaptureWorker
from app.services.cascade.flash_worker import FlashWorker
from app.services.cascade.plus_worker import PlusWorker

# 主引擎
from app.services.cascade.engine import CascadeEngine

__all__ = [
    # 数据类型
    "PendingDefect",
    # 核心组件
    "DetectionDeduplicator",
    "AsyncVideoWriter",
    "get_vlm_roi",
    # 工具函数
    "calculate_relative_timestamp",
    "format_timestamp",
    "location_to_bbox",
    "is_valid_location",
    "format_position",
    # 工作线程
    "CaptureWorker",
    "FlashWorker",
    "PlusWorker",
    # 主引擎
    "CascadeEngine",
]
