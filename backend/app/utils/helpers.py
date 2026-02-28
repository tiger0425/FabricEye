"""
FabricEye AI验布系统 - 通用工具函数
提供日期格式化、文件路径处理等辅助功能。
"""

import os
from datetime import datetime


def format_timestamp(dt: datetime) -> str:
    """
    格式化日期时间。
    
    Args:
        dt (datetime): 日期时间对象
        
    Returns:
        str: 格式化后的字符串
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def ensure_dir(path: str) -> None:
    """
    确保目录存在，如果不存在则创建。
    
    Args:
        path (str): 目录路径
    """
    if not os.path.exists(path):
        os.makedirs(path)
