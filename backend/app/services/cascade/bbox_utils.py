"""
FabricEye 级联检测引擎 - 边界框工具
边界框转换和验证工具。
"""

from typing import Tuple, List


def location_to_bbox(location: List[float], img_w: int, img_h: int) -> Tuple[int, int, int, int]:
    """
    将location列表转换为bbox元组。
    
    Args:
        location: [x1, y1, x2, y2] 坐标列表
        img_w: 图像宽度
        img_h: 图像高度
    
    Returns:
        (x1, y1, x2, y2) 元组
    """
    if len(location) != 4:
        return (0, 0, 0, 0)
    
    a, b, c, d = location
    max_coord = max(a, b, c, d)
    max_img = max(img_w, img_h)
    
    if max_coord > max_img:
        # 相对坐标 (0-1000) 转换为绝对像素坐标
        return (
            int(a * img_w / 1000),
            int(b * img_h / 1000),
            int(c * img_w / 1000),
            int(d * img_h / 1000)
        )
    
    # 已经是绝对坐标
    return (int(a), int(b), int(c), int(d))


def is_valid_location(location: List[float]) -> bool:
    """
    验证location是否为有效的边界框坐标。
    
    Args:
        location: [x1, y1, x2, y2] 坐标列表
    
    Returns:
        是否有效
    """
    if len(location) != 4:
        return False
    
    if all(v == 0 for v in location):
        return False
    
    x1, y1, x2, y2 = location
    return x2 > x1 and y2 > y1


def format_position(bbox: Tuple[int, int, int, int]) -> str:
    """
    格式化位置字符串。
    
    Args:
        bbox: (x1, y1, x2, y2) 边界框
    
    Returns:
        格式化字符串，如 "(100, 200)"
    """
    return f"({int(bbox[0])}, {int(bbox[1])})"
