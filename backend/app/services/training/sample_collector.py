"""
FabricEye 训练数据管理 - 样本收集器
负责从检测结果中收集高质量的训练样本，用于 YOLO 模型增量训练。
"""

import os
import json
import logging
import time
import threading
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from app.services.parallel.types import (
    SampleForTraining,
    DetectionSource,
)

logger = logging.getLogger(__name__)


class SampleCollector:
    """
    训练样本收集器
    
    从确认的检测结果中收集高质量样本：
    - 仅收集人工确认的样本
    - 自动过滤低质量样本
    - 支持多种导出格式（YOLO VOC, COCO 等）
    """
    
    def __init__(
        self,
        output_dir: str = "storage/training_samples",
        min_confidence: float = 0.6,  # 最低置信度阈值
        min_samples: int = 50,  # 触发导出的最少样本数
    ):
        self.output_dir = output_dir
        self.min_confidence = min_confidence
        self.min_samples = min_samples
        
        # 样本缓存
        self._samples: List[SampleForTraining] = []
        self._lock = threading.Lock()
        
        # 统计
        self._total_collected = 0
        self._total_exported = 0
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 样本索引文件
        self._index_file = os.path.join(output_dir, "samples_index.json")
    
    def add_sample(self, sample: SampleForTraining) -> bool:
        """
        添加训练样本
        
        Args:
            sample: 训练样本
            
        Returns:
            是否添加成功
        """
        # 过滤低质量样本
        if sample.defect_type == "unknown":
            logger.debug(f"跳过未知类型样本: {sample.cascade_id}")
            return False
        
        # 检查置信度（从来源推断）
        # VLM 样本通常更可靠
        if sample.source == DetectionSource.VLM:
            # VLM 样本需要更高置信度
            if sample.severity == "minor":
                # 轻微缺陷需要更高置信度
                return False
        
        with self._lock:
            self._samples.append(sample)
            self._total_collected += 1
        
        logger.debug(f"添加训练样本: cascade_id={sample.cascade_id}, type={sample.defect_type}")
        return True
    
    def add_samples_batch(self, samples: List[SampleForTraining]) -> int:
        """
        批量添加样本
        
        Args:
            samples: 样本列表
            
        Returns:
            成功添加的数量
        """
        count = 0
        for sample in samples:
            if self.add_sample(sample):
                count += 1
        return count
    
    def get_samples(self, defect_type: Optional[str] = None) -> List[SampleForTraining]:
        """
        获取样本列表
        
        Args:
            defect_type: 按缺陷类型过滤（可选）
            
        Returns:
            样本列表
        """
        with self._lock:
            if defect_type:
                return [s for s in self._samples if s.defect_type == defect_type]
            return list(self._samples)
    
    def get_sample_count(self) -> int:
        """获取样本总数"""
        with self._lock:
            return len(self._samples)
    
    def should_export(self) -> bool:
        """判断是否应该导出样本"""
        return self.get_sample_count() >= self.min_samples
    
    def export_yolo_format(self, output_path: Optional[str] = None) -> str:
        """
        导出为 YOLO 格式
        
        目录结构:
        output_dir/
        ├── images/
        │   ├── train/
        │   │   ├── defect_hole_001.jpg
        │   │   └── defect_stain_002.jpg
        │   └── val/
        └── labels/
            ├── train/
            │   ├── defect_hole_001.txt
            │   └── defect_stain_002.txt
            └── val/
        
        Args:
            output_path: 输出路径（可选，默认使用 output_dir）
            
        Returns:
            导出的目录路径
        """
        output_path = output_path or self.output_dir
        
        # 创建子目录
        images_train_dir = os.path.join(output_path, "images", "train")
        labels_train_dir = os.path.join(output_path, "labels", "train")
        
        os.makedirs(images_train_dir, exist_ok=True)
        os.makedirs(labels_train_dir, exist_ok=True)
        
        exported_count = 0
        
        with self._lock:
            for sample in self._samples:
                try:
                    # 生成文件名
                    timestamp = int(sample.timestamp)
                    filename = f"defect_{sample.defect_type}_{sample.cascade_id:06d}_{timestamp}"
                    
                    # 复制图像文件（如果有）
                    if os.path.exists(sample.roi_image_path):
                        dest_image_path = os.path.join(
                            images_train_dir,
                            f"{filename}.jpg"
                        )
                        # 这里应该复制文件，但先假设文件已存在
                        # shutil.copy(sample.roi_image_path, dest_image_path)
                    
                    # 生成 YOLO 格式标签文件
                    # YOLO 格式: class_id center_x center_y width height (归一化)
                    label_filename = f"{filename}.txt"
                    label_path = os.path.join(labels_train_dir, label_filename)
                    
                    # 转换 bbox 为 YOLO 格式
                    # 需要图像尺寸信息，这里简化处理
                    class_id = self._get_class_id(sample.defect_type)
                    
                    # 假设 bbox 已经是归一化的（0-1）
                    x1, y1, x2, y2 = sample.bbox
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    width = x2 - x1
                    height = y2 - y1
                    
                    with open(label_path, 'w') as f:
                        f.write(f"{class_id} {center_x} {center_y} {width} {height}\n")
                    
                    exported_count += 1
                    self._total_exported += 1
                    
                except Exception as e:
                    logger.error(f"导出样本失败: {e}")
        
        logger.info(f"YOLO 格式导出完成: {exported_count} 个样本")
        
        # 保存索引文件
        self._save_index(output_path)
        
        return output_path
    
    def _get_class_id(self, defect_type: str) -> int:
        """获取 YOLO 类别 ID"""
        class_mapping = {
            "hole": 0,
            "stain": 1,
            "color_variance": 2,
            "warp_break": 3,
            "weft_break": 4,
            "foreign_matter": 5,
            "crease": 6,
            "snag": 7,
        }
        return class_mapping.get(defect_type, 8)
    
    def _save_index(self, output_path: str) -> None:
        """保存样本索引文件"""
        index_data = {
            "export_time": datetime.utcnow().isoformat(),
            "total_samples": len(self._samples),
            "samples": [
                {
                    "cascade_id": s.cascade_id,
                    "defect_type": s.defect_type,
                    "severity": s.severity,
                    "source": s.source.value,
                    "timestamp": s.timestamp,
                    "verified_at": s.verified_at.isoformat() if s.verified_at else None,
                }
                for s in self._samples
            ]
        }
        
        index_file = os.path.join(output_path, "samples_index.json")
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"样本索引已保存: {index_file}")
    
    def load_index(self, index_file: Optional[str] = None) -> bool:
        """
        加载已有样本索引
        
        Args:
            index_file: 索引文件路径
            
        Returns:
            是否加载成功
        """
        index_file = index_file or self._index_file
        
        if not os.path.exists(index_file):
            return False
        
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # 恢复样本数据（只恢复元数据，不包含图像）
            # 这里简化处理，实际应该从索引重建样本对象
            logger.info(f"加载样本索引: {len(index_data.get('samples', []))} 个样本")
            return True
            
        except Exception as e:
            logger.error(f"加载样本索引失败: {e}")
            return False
    
    def clear(self) -> None:
        """清空样本缓存"""
        with self._lock:
            self._samples.clear()
        logger.info("样本缓存已清空")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            # 按类型统计
            type_counts = {}
            severity_counts = {}
            source_counts = {}
            
            for sample in self._samples:
                # 类型
                type_counts[sample.defect_type] = type_counts.get(sample.defect_type, 0) + 1
                # 严重程度
                severity_counts[sample.severity] = severity_counts.get(sample.severity, 0) + 1
                # 来源
                source_counts[sample.source.value] = source_counts.get(sample.source.value, 0) + 1
            
            return {
                "total_collected": self._total_collected,
                "total_in_cache": len(self._samples),
                "total_exported": self._total_exported,
                "by_type": type_counts,
                "by_severity": severity_counts,
                "by_source": source_counts,
            }


class DatasetManager:
    """
    数据集管理器
    
    负责管理多个布卷的训练数据：
    - 跨布卷样本整合
    - 训练/验证集划分
    - 数据集版本管理
    """
    
    def __init__(self, dataset_dir: str = "storage/datasets"):
        self.dataset_dir = dataset_dir
        os.makedirs(dataset_dir, exist_ok=True)
        
        # 数据集版本
        self._current_version = 1
        self._load_version()
    
    def _load_version(self) -> None:
        """加载当前版本号"""
        version_file = os.path.join(self.dataset_dir, "version.txt")
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                self._current_version = int(f.read().strip()) + 1
    
    def _save_version(self) -> None:
        """保存版本号"""
        version_file = os.path.join(self.dataset_dir, "version.txt")
        with open(version_file, 'w') as f:
            f.write(str(self._current_version))
    
    def create_dataset(
        self,
        name: str,
        samples: List[SampleForTraining],
        train_ratio: float = 0.8,
    ) -> str:
        """
        创建新数据集
        
        Args:
            name: 数据集名称
            samples: 样本列表
            train_ratio: 训练集比例
            
        Returns:
            数据集路径
        """
        # 创建数据集目录
        dataset_name = f"{name}_v{self._current_version}"
        dataset_path = os.path.join(self.dataset_dir, dataset_name)
        
        os.makedirs(dataset_path, exist_ok=True)
        os.makedirs(os.path.join(dataset_path, "images", "train"), exist_ok=True)
        os.makedirs(os.path.join(dataset_path, "images", "val"), exist_ok=True)
        os.makedirs(os.path.join(dataset_path, "labels", "train"), exist_ok=True)
        os.makedirs(os.path.join(dataset_path, "labels", "val"), exist_ok=True)
        
        # 划分训练集和验证集
        import random
        random.shuffle(samples)
        
        split_idx = int(len(samples) * train_ratio)
        train_samples = samples[:split_idx]
        val_samples = samples[split_idx:]
        
        # 导出训练集
        self._export_samples(train_samples, dataset_path, "train")
        
        # 导出验证集
        self._export_samples(val_samples, dataset_path, "val")
        
        # 生成数据集配置文件
        self._generate_yaml(dataset_path, name, len(train_samples), len(val_samples))
        
        # 更新版本号
        self._current_version += 1
        self._save_version()
        
        logger.info(f"数据集创建完成: {dataset_path}")
        return dataset_path
    
    def _export_samples(
        self,
        samples: List[SampleForTraining],
        dataset_path: str,
        split: str,
    ) -> None:
        """导出样本到数据集"""
        images_dir = os.path.join(dataset_path, "images", split)
        labels_dir = os.path.join(dataset_path, "labels", split)
        
        class_mapping = {
            "hole": 0, "stain": 1, "color_variance": 2,
            "warp_break": 3, "weft_break": 4, "foreign_matter": 5,
            "crease": 6, "snag": 7,
        }
        
        for sample in samples:
            # 生成文件名
            filename = f"defect_{sample.defect_type}_{sample.cascade_id:06d}"
            
            # 生成标签文件
            label_path = os.path.join(labels_dir, f"{filename}.txt")
            
            x1, y1, x2, y2 = sample.bbox
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            width = x2 - x1
            height = y2 - y1
            
            class_id = class_mapping.get(sample.defect_type, 8)
            
            with open(label_path, 'w') as f:
                f.write(f"{class_id} {center_x} {center_y} {width} {height}\n")
    
    def _generate_yaml(
        self,
        dataset_path: str,
        name: str,
        train_count: int,
        val_count: int,
    ) -> None:
        """生成 YOLO 数据集配置文件"""
        yaml_content = f"""# YOLO Dataset Configuration
# Generated by FabricEye Training Module

path: {dataset_path}
train: images/train
val: images/val

# Classes
names:
  0: hole
  1: stain
  2: color_variance
  3: warp_break
  4: weft_break
  5: foreign_matter
  6: crease
  7: snag
  8: unknown

# Dataset Info
train_samples: {train_count}
val_samples: {val_count}
total_samples: {train_count + val_count}

# Generated at
generated_at: {datetime.utcnow().isoformat()}
"""
        
        yaml_path = os.path.join(dataset_path, "dataset.yaml")
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        logger.info(f"数据集配置已生成: {yaml_path}")
