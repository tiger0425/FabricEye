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
    AI_PROVIDER: str = "mock"  # 可选: mock, kimi, qwen, cascade
    AI_API_KEY: str = ""
    AI_API_BASE_URL: str = "https://api.moonshot.cn/v1"
    AI_MODEL: str = "moonshot-v1-8k"
    ANALYSIS_INTERVAL: float = 1.0  # 每秒分析1帧

    # Qwen3-VL 级联检测配置
    QWEN_API_BASE_URL: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    QWEN_API_KEY: str = ""  # DashScope API Key
    QWEN_FLASH_MODEL: str = "qwen-vl-max-latest"
    QWEN_PLUS_MODEL: str = "qwen-vl-plus-latest"

    # 级联检测阈值
    CASCADE_FLASH_THRESHOLD: float = 0.4  # Flash 初筛阈值
    CASCADE_PLUS_THRESHOLD: float = 0.85  # Plus 确认阈值

    # 去重与缓冲
    DEDUP_IOU_THRESHOLD: float = 0.5  # IoU 空间去重阈值
    DEDUP_TIME_WINDOW: float = 3.0  # 时间窗口（秒）
    FRAME_BUFFER_SIZE: int = 120  # 帧环形缓冲区大小

    # 级联队列
    VERIFICATION_QUEUE_SIZE: int = 50  # Plus 验证队列大小
    PENDING_DEFECT_TTL: float = 30.0  # PendingDefect 超时（秒）

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
