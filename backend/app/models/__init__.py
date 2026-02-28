"""
FabricEye AI验布系统 - 模型模块
导出所有 ORM 模型。
"""
from app.core.database import Base
from app.models.roll import Roll, RollStatus
from app.models.video import Video, VideoStatus
from app.models.defect import (
    Defect,
    DefectType,
    DefectSeverity,
    ReviewResult,
    DefectTypeCN,
)

# 导出所有模型和 Base
__all__ = [
    "Base",
    "Roll",
    "RollStatus",
    "Video",
    "VideoStatus",
    "Defect",
    "DefectType",
    "DefectSeverity",
    "ReviewResult",
    "DefectTypeCN",
]
