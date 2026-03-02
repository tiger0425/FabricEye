"""
FabricEye 级联检测引擎 - 图像处理器
VLM ROI提取和图像预处理工具。
"""

import numpy as np
import cv2


def get_vlm_roi(
    image: np.ndarray, 
    bbox: tuple, 
    margin: float = 0.15, 
    target_size: int = 512
) -> np.ndarray:
    """
    从图像中提取VLM处理的ROI区域。
    
    Args:
        image: 原始图像 (H, W, C)
        bbox: 边界框 (x1, y1, x2, y2)
        margin: 边距比例
        target_size: 目标输出尺寸
    
    Returns:
        处理后的ROI图像 (target_size, target_size, 3)
    """
    img_h, img_w = image.shape[:2]
    x1, y1, x2, y2 = bbox
    
    # 计算带边距的裁剪区域
    mx, my = (x2 - x1) * margin, (y2 - y1) * margin
    cx1, cy1 = max(0, int(x1 - mx)), max(0, int(y1 - my))
    cx2, cy2 = min(img_w, int(x2 + mx)), min(img_h, int(y2 + my))
    
    # 裁剪
    crop = image[cy1:cy2, cx1:cx2]
    if crop.size == 0:
        return np.zeros((target_size, target_size, 3), dtype=np.uint8)
    
    # 等比例缩放
    scale = min(target_size / crop.shape[1], target_size / crop.shape[0])
    resized = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    
    # 居中填充到目标尺寸
    canvas = np.zeros((target_size, target_size, 3), dtype=np.uint8)
    pad_x = (target_size - resized.shape[1]) // 2
    pad_y = (target_size - resized.shape[0]) // 2
    canvas[pad_y:pad_y + resized.shape[0], pad_x:pad_x + resized.shape[1]] = resized
    
    return canvas
