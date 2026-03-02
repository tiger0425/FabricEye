"""
向后兼容重定向模块
警告: 此模块已弃用，请使用 app.services.cascade
"""

import warnings

warnings.warn(
    "app.services.cascade_engine 已弃用，请使用 app.services.cascade",
    DeprecationWarning,
    stacklevel=2
)

# 重导出所有内容
from app.services.cascade import (
    PendingDefect,
    DetectionDeduplicator,
    AsyncVideoWriter,
    get_vlm_roi,
    CascadeEngine,
)

__all__ = [
    "PendingDefect",
    "DetectionDeduplicator",
    "AsyncVideoWriter",
    "get_vlm_roi",
    "CascadeEngine",
]
