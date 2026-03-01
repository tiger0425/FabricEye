"""
FabricEye AI验布系统 - 配置管理模块
该模块负责加载和管理应用程序的所有配置项。
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """
    应用程序配置类
    使用 pydantic-settings 从环境变量或默认值加载配置。
    """
    # 项目基本信息
    PROJECT_NAME: str = "FabricEye AI验布系统"
    API_V1_STR: str = "/api"
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./fabriceye.db"
    
    # CORS配置
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    # 视频采集配置
    CAMERA_TYPE: str = "opencv"  # 可选: opencv, mvs, mock
    CAMERA_ID: int = 0
    CAMERA_WIDTH: int = 1280
    CAMERA_HEIGHT: int = 720
    CAMERA_FPS: int = 30
    
    # AI分析配置
    ANALYSIS_INTERVAL: float = 1.0  # 每秒分析1帧
    AI_API_KEY: str = ""
    AI_MODEL_PATH: str = "deepseek-ai/deepseek-vl-1.3b-chat"


    class Config:
        case_sensitive = True


settings = Settings()
