"""
FabricEye 级联检测引擎 - 时间戳工具
处理时间戳计算和格式化。
"""

import time
from typing import Optional


def calculate_relative_timestamp(
    recording_start_time: Optional[float],
    current_time: Optional[float] = None
) -> float:
    """
    计算相对于录制开始时间的时间戳。
    
    Args:
        recording_start_time: 录制开始时间（秒级时间戳）
        current_time: 当前时间（默认为time.time()）
    
    Returns:
        相对时间戳（秒），如果start_time为None则返回0
    """
    if not recording_start_time:
        return 0.0
    
    current = current_time or time.time()
    return round(current - recording_start_time, 2)


def format_timestamp(seconds: float) -> str:
    """
    将秒数格式化为可读时间字符串 (MM:SS)。
    
    Args:
        seconds: 时间戳（秒）
    
    Returns:
        格式化字符串，如 "01:30"
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"
