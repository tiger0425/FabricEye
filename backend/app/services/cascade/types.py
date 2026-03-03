"""
FabricEye 级联检测引擎 - 数据类型定义
"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class PendingDefect:
    """跟踪从Flash到Plus验证的检测过程。"""
    cascade_id: int
    frame_index: int
    flash_confidence: float
    roi_crop: np.ndarray
    timestamp: float
    bbox: tuple
    defect_type: str
    severity: str
    created_at: float
    status: str = "pending"
    plus_confidence: Optional[float] = None
