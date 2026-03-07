"""
FabricEye YOLO 模型管理

提供 YOLO 模型管理和训练任务接口。
"""

from app.services.yolo.model_manager import ModelManager, TrainingAPI

__all__ = [
    "ModelManager",
    "TrainingAPI",
]
