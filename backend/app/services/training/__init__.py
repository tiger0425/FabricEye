"""
FabricEye 训练数据管理

提供训练样本收集和数据集管理功能。
"""

from app.services.training.sample_collector import SampleCollector, DatasetManager

__all__ = [
    "SampleCollector",
    "DatasetManager",
]
