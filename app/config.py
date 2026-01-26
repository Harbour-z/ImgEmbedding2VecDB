"""
配置管理模块
支持环境变量和默认配置的灵活切换
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""

    # 基础配置
    APP_NAME: str = "Smart Album API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # API配置
    API_PREFIX: str = "/api/v1"

    # Embedding模型配置
    MODEL_PATH: str = str(Path(__file__).parent.parent / "qwen3-vl-embedding-2B")
    CUDA_DEVICE: str = "0"

    MAX_LENGTH: int = 8192
    MIN_PIXELS: int = 4 * 32 * 32  # 4 * IMAGE_FACTOR^2
    MAX_PIXELS: int = 1800 * 32 * 32  # 1800 * IMAGE_FACTOR^2
    DEFAULT_INSTRUCTION: str = "Represent the user's input."

    # Embedding Service Configuration (API-based)
    EMBEDDING_API_PROVIDER: str = "local"  # Options: local, aliyun
    ALIYUN_EMBEDDING_API_KEY: Optional[str] = None
    ALIYUN_EMBEDDING_BASE_URL: Optional[str] = None  # DashScope SDK 不需要
    ALIYUN_EMBEDDING_MODEL_NAME: str = "qwen3-vl-embedding"
    ALIYUN_EMBEDDING_DIMENSION: int = 2560  # 支持 2560, 2048, 1536, 1024, 768, 512, 256

    # Qdrant向量数据库配置
    QDRANT_MODE: str = "local"  # local | docker | cloud
    QDRANT_PATH: str = str(Path(__file__).parent.parent / "qdrant_data")
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "smart_album"
    VECTOR_DIMENSION: int = 2560  # Qwen3-VL embedding维度 (2560 for qwen3-vl-embedding)

    # 图片存储配置
    STORAGE_PATH: str = str(
        Path(__file__).parent.parent / "storage" / "images")
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: set = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}

    # Agent集成配置
    AGENT_ENABLED: bool = True
    AGENT_PROVIDER: str = "openai"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL_NAME: str = "gpt-4o"

    LLM_SSL_VERIFY: bool = False
    LLM_SSL_CERT: Optional[str] = None

    # Multi-modal Visual Understanding Model Configuration
    # Supports numeric suffixes for multiple instances (e.g. VISION_MODEL_1_*)
    VISION_MODEL_NAME: str = "qwen3-vl-plus"
    VISION_MODEL_API_KEY: Optional[str] = None
    VISION_MODEL_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # Image Generation Model Configuration (Reserved)
    IMAGE_GENERATION_MODEL_NAME: Optional[str] = None
    IMAGE_GENERATION_MODEL_API_KEY: Optional[str] = None
    IMAGE_GENERATION_MODEL_BASE_URL: Optional[str] = None

    # Image Editing Model Configuration (Reserved)
    IMAGE_EDITING_MODEL_NAME: Optional[str] = None
    IMAGE_EDITING_MODEL_API_KEY: Optional[str] = None
    IMAGE_EDITING_MODEL_BASE_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore" # 允许.env中存在未在Settings中定义的字段


@lru_cache()
def get_settings() -> Settings:
    """获取缓存的配置实例"""
    return Settings()


# 确保必要目录存在
def ensure_directories():
    """确保所有必要的目录存在"""
    settings = get_settings()

    # 创建存储目录
    storage_path = Path(settings.STORAGE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)

    # 创建Qdrant本地存储目录
    if settings.QDRANT_MODE == "local":
        qdrant_path = Path(settings.QDRANT_PATH)
        qdrant_path.mkdir(parents=True, exist_ok=True)
