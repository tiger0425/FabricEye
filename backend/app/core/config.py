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
    AI_PROVIDER: str = "cascade"  # 可选: mock, kimi, qwen, cascade
    AI_API_KEY: str = ""
    AI_API_BASE_URL: str = "https://api.moonshot.cn/v1"
    AI_MODEL: str = "moonshot-v1-8k"
    ANALYSIS_INTERVAL: float = 2.0  # 提高检测频率

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
    ANALYSIS_INTERVAL: float = 5.0  # 每5秒分析1帧，降低服务器负载

    # Qwen3.5 级联检测配置 (PRIMARY_MODEL, SECONDARY_MODEL)
    QWEN_API_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_API_KEY: str = ""  # DashScope API Key
    PRIMARY_MODEL: str = "qwen3.5-flash"
    SECONDARY_MODEL: str = "qwen3.5-plus"
    ENABLE_SECONDARY: bool = True

    # 级联检测阈值
    FLASH_THRESHOLD: float = 0.4  # Flash 初筛阈值
    SKIP_VERIFY_THRESHOLD: float = 0.8  # 超过此值则认为初扫已足够准确，跳过复核

    # 去重与缓冲
    DEDUP_IOU_THRESHOLD: float = 0.5  # IoU 空间去重阈值
    DEDUP_TIME_WINDOW: float = 3.0  # 时间窗口（秒）
    FRAME_BUFFER_SIZE: int = 120  # 帧环形缓冲区大小

    # 级联队列
    VERIFICATION_QUEUE_SIZE: int = 50  # Plus 验证队列大小
    PENDING_DEFECT_TTL: float = 30.0  # PendingDefect 超时（秒）
    
    # ==================== Parallel 并行检测配置 ====================
    # YOLO 配置
    YOLO_MODEL_PATH: str = "models/yolov11s_fabric.pt"  # YOLO 模型路径
    YOLO_CONFIDENCE: float = 0.5  # YOLO 检测置信度阈值
    YOLO_SKIP_FRAMES: int = 0  # YOLO 跳帧数，0 表示每帧都检测
    
    # VLM 采样配置
    VLM_SAMPLE_INTERVAL: int = 30  # VLM 采样间隔（帧数）
    USE_ADAPTIVE_SAMPLING: bool = False  # 是否使用自适应采样
    
    # 交叉核对配置
    RECONCILE_IOU_THRESHOLD: float = 0.3  # 核对匹配 IOU 阈值
    RECONCILE_TIME_WINDOW: float = 2.0  # 核对时间窗口（秒）
    
    # 训练配置
    TRAINING_MIN_SAMPLES: int = 50  # 触发训练最少样本数

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
