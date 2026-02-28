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

    class Config:
        case_sensitive = True


settings = Settings()
