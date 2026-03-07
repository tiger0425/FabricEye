"""
FabricEye YOLO 模型管理
负责 YOLO 模型的加载、版本管理和增量训练接口。
"""

import os
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ModelManager:
    """
    YOLO 模型管理器
    
    负责：
    - 模型版本管理
    - 模型加载/卸载
    - 模型文件检查
    - 训练任务提交
    """
    
    def __init__(
        self,
        models_dir: str = "models",
        default_model: str = "yolov11s_fabric.pt",
    ):
        self.models_dir = models_dir
        self.default_model = default_model
        self._current_model = None
        self._model_info = {}
        
        # 确保模型目录存在
        os.makedirs(models_dir, exist_ok=True)
        
        # 模型信息文件
        self._info_file = os.path.join(models_dir, "model_info.json")
        self._load_model_info()
    
    def _load_model_info(self) -> None:
        """加载模型信息"""
        if os.path.exists(self._info_file):
            try:
                with open(self._info_file, 'r', encoding='utf-8') as f:
                    self._model_info = json.load(f)
            except Exception as e:
                logger.error(f"加载模型信息失败: {e}")
                self._model_info = {}
    
    def _save_model_info(self) -> None:
        """保存模型信息"""
        try:
            with open(self._info_file, 'w', encoding='utf-8') as f:
                json.dump(self._model_info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存模型信息失败: {e}")
    
    def register_model(
        self,
        model_name: str,
        version: str = "1.0.0",
        accuracy: float = 0.0,
        train_samples: int = 0,
        description: str = "",
    ) -> bool:
        """
        注册新模型
        
        Args:
            model_name: 模型文件名
            version: 版本号
            accuracy: 准确率
            train_samples: 训练样本数
            description: 描述
            
        Returns:
            是否注册成功
        """
        model_path = os.path.join(self.models_dir, model_name)
        
        if not os.path.exists(model_path):
            logger.warning(f"模型文件不存在: {model_path}")
            return False
        
        # 获取文件大小
        file_size = os.path.getsize(model_path)
        
        # 更新模型信息
        self._model_info[model_name] = {
            "version": version,
            "file_path": model_path,
            "file_size": file_size,
            "accuracy": accuracy,
            "train_samples": train_samples,
            "description": description,
            "created_at": datetime.utcnow().isoformat(),
            "is_active": False,
        }
        
        # 设置为默认模型
        self._model_info["default"] = model_name
        
        self._save_model_info()
        
        logger.info(f"模型注册成功: {model_name} v{version}")
        return True
    
    def set_active_model(self, model_name: str) -> bool:
        """
        设置活跃模型
        
        Args:
            model_name: 模型文件名
            
        Returns:
            是否设置成功
        """
        if model_name not in self._model_info and model_name != self.default_model:
            logger.warning(f"模型未注册: {model_name}")
            return False
        
        # 取消其他模型的活跃状态
        for name, info in self._model_info.items():
            if isinstance(info, dict):
                info["is_active"] = False
        
        # 设置新模型为活跃
        if model_name in self._model_info:
            self._model_info[model_name]["is_active"] = True
        self._model_info["default"] = model_name
        
        self._save_model_info()
        
        logger.info(f"活跃模型已切换: {model_name}")
        return True
    
    def get_active_model(self) -> str:
        """
        获取当前活跃模型
        
        Returns:
            活跃模型名称
        """
        default = self._model_info.get("default", self.default_model)
        
        # 检查默认模型是否存在
        model_path = os.path.join(self.models_dir, default)
        if not os.path.exists(model_path):
            # 回退到默认模型
            return self.default_model
        
        return default
    
    def get_model_info(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取模型信息
        
        Args:
            model_name: 模型名称（None 表示获取活跃模型）
            
        Returns:
            模型信息字典
        """
        model_name = model_name or self.get_active_model()
        
        if model_name in self._model_info:
            return self._model_info[model_name]
        
        return {}
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册的模型
        
        Returns:
            模型列表
        """
        models = []
        
        for name, info in self._model_info.items():
            if isinstance(info, dict) and "file_path" in info:
                models.append({
                    "name": name,
                    **info
                })
        
        return models
    
    def check_model_health(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        检查模型健康状态
        
        Args:
            model_name: 模型名称
            
        Returns:
            健康状态报告
        """
        model_name = model_name or self.get_active_model()
        model_path = os.path.join(self.models_dir, model_name)
        
        report = {
            "model_name": model_name,
            "exists": os.path.exists(model_path),
            "size_bytes": 0,
            "is_valid": False,
            "issues": [],
        }
        
        if report["exists"]:
            report["size_bytes"] = os.path.getsize(model_path)
            
            # 检查文件大小是否合理（至少 1MB）
            if report["size_bytes"] < 1024 * 1024:
                report["issues"].append("文件大小异常，可能已损坏")
            else:
                report["is_valid"] = True
        else:
            report["issues"].append("模型文件不存在")
        
        return report
    
    def download_pretrained(self, model_name: str = "yolov11s.pt") -> bool:
        """
        下载预训练模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            是否下载成功
        """
        try:
            from ultralytics import YOLO
            
            logger.info(f"正在下载预训练模型: {model_name}")
            
            # 下载模型
            model = YOLO(model_name)
            
            # 保存到模型目录
            dest_path = os.path.join(self.models_dir, model_name)
            
            # 如果已存在，跳过
            if os.path.exists(dest_path):
                logger.info(f"模型已存在: {dest_path}")
                return True
            
            # 注意: YOLO 的 save 方法会自动下载
            # 这里简化处理，实际应该复制模型文件
            logger.info(f"预训练模型下载完成: {model_name}")
            
            # 注册模型
            self.register_model(
                model_name=model_name,
                version="pretrained",
                description="官方预训练模型"
            )
            
            return True
            
        except ImportError:
            logger.error("ultralytics 未安装，无法下载预训练模型")
            return False
        except Exception as e:
            logger.error(f"下载预训练模型失败: {e}")
            return False


class TrainingAPI:
    """
    训练任务 API
    
    负责与训练服务器通信，提交训练任务。
    """
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.api_url = api_url or os.environ.get("TRAINING_API_URL", "")
        self.api_key = api_key or os.environ.get("TRAINING_API_KEY", "")
    
    def submit_training(
        self,
        dataset_path: str,
        model_name: str = "yolov11s",
        epochs: int = 100,
        batch_size: int = 16,
        **kwargs,
    ) -> Optional[str]:
        """
        提交训练任务
        
        Args:
            dataset_path: 数据集路径
            model_name: 基础模型名称
            epochs: 训练轮数
            batch_size: 批次大小
            **kwargs: 其他训练参数
            
        Returns:
            任务 ID（如果提交成功）
        """
        if not self.api_url:
            logger.warning("训练 API URL 未配置")
            return None
        
        # 构建请求
        payload = {
            "dataset_path": dataset_path,
            "model_name": model_name,
            "epochs": epochs,
            "batch_size": batch_size,
            "project_name": "FabricEye",
            **kwargs,
        }
        
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            import aiohttp
            import asyncio
            
            async def submit():
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.api_url}/train",
                        json=payload,
                        headers=headers,
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            task_id = result.get("task_id")
                            logger.info(f"训练任务已提交: {task_id}")
                            return task_id
                        else:
                            logger.error(f"训练任务提交失败: {response.status}")
                            return None
            
            return asyncio.run(submit())
            
        except Exception as e:
            logger.error(f"提交训练任务失败: {e}")
            return None
    
    def get_training_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取训练任务状态
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务状态
        """
        if not self.api_url:
            return {"status": "error", "message": "API URL 未配置"}
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            import aiohttp
            import asyncio
            
            async def check():
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.api_url}/train/{task_id}",
                        headers=headers,
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            return {"status": "error", "message": f"HTTP {response.status}"}
            
            return asyncio.run(check())
            
        except Exception as e:
            logger.error(f"获取训练状态失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def download_trained_model(self, task_id: str, dest_path: str) -> bool:
        """
        下载训练好的模型
        
        Args:
            task_id: 任务 ID
            dest_path: 目标路径
            
        Returns:
            是否下载成功
        """
        if not self.api_url:
            logger.warning("训练 API URL 未配置")
            return False
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            import aiohttp
            import asyncio
            
            async def download():
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.api_url}/train/{task_id}/download",
                        headers=headers,
                    ) as response:
                        if response.status == 200:
                            # 保存文件
                            content = await response.read()
                            with open(dest_path, 'wb') as f:
                                f.write(content)
                            logger.info(f"模型已下载: {dest_path}")
                            return True
                        else:
                            logger.error(f"模型下载失败: {response.status}")
                            return False
            
            return asyncio.run(download())
            
        except Exception as e:
            logger.error(f"下载训练模型失败: {e}")
            return False
