"""
Embedding服务模块
封装Qwen3-VL多模态Embedding模型的调用
支持本地推理和阿里云 API 服务
"""

import sys
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING
from PIL import Image

from ..config import get_settings

# 延迟导入：只在类型检查时导入，运行时不导入
if TYPE_CHECKING:
    from qwen3_vl_embedding import Qwen3VLEmbedder

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding服务类
    负责管理Qwen3-VL模型实例并提供向量生成接口
    支持本地推理和阿里云 API 服务
    """

    _instance: Optional["EmbeddingService"] = None
    _embedder: Optional[Any] = None  # 使用Any避免类型错误
    _api_client: Optional[Any] = None  # API 客户端

    def __new__(cls):
        """单例模式确保只有一个模型实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._initialized = getattr(self, '_initialized', False)
        self._api_provider = None

    def initialize(
        self,
        model_path: Optional[str] = None,
        device: Optional[str] = None
    ) -> None:
        """
        初始化Embedding服务（本地模型或API客户端）
        Args:
            model_path: 本地模型路径（仅用于本地推理）
            device: 设备名称（仅用于本地推理）
        """
        if self._initialized:
            logger.warning("Embedding服务已初始化，跳过重复初始化")
            return

        settings = get_settings()
        self._api_provider = settings.EMBEDDING_API_PROVIDER.lower()

        # 根据配置选择初始化方式
        if self._api_provider == "aliyun":
            self._initialize_api()
        elif self._api_provider == "local":
            self._initialize_local(model_path, device)
        else:
            raise ValueError(f"不支持的 Embedding API Provider: {self._api_provider}")

        self._initialized = True
        logger.info(f"Embedding服务初始化完成 (Provider: {self._api_provider})")

    def _initialize_api(self):
        """初始化阿里云 API 客户端"""
        try:
            from .aliyun_embedding_client import get_aliyun_client
            self._api_client = get_aliyun_client()
            self._api_client.initialize()
            logger.info(f"阿里云 Embedding API 客户端初始化成功 (Dimension: {self._api_client.get_vector_dimension()})")
        except Exception as e:
            logger.error(f"阿里云 API 客户端初始化失败: {e}")
            raise

    def _initialize_local(
        self,
        model_path: Optional[str] = None,
        device: Optional[str] = None
    ):
        """初始化本地模型"""
        settings = get_settings()

        # 添加模型脚本路径到sys.path
        SCRIPTS_PATH = Path(__file__).parent.parent.parent / "qwen3-vl-embedding-2B" / "scripts"
        sys.path.insert(0, str(SCRIPTS_PATH))

        try:
            from qwen3_vl_embedding import Qwen3VLEmbedder

            model_path = model_path or settings.MODEL_PATH
            device = device or settings.CUDA_DEVICE

            logger.info(f"正在加载Embedding模型: {model_path}")
            logger.info(f"设备: {device}")

            self._embedder = Qwen3VLEmbedder(
                model_path=model_path,
                device=device
            )
            logger.info("Embedding服务初始化成功")
        except Exception as e:
            logger.error(f"Embedding服务初始化失败: {e}", exc_info=True)
            raise

    @property
    def is_initialized(self) -> bool:
        """检查模型是否已初始化"""
        return self._initialized

    @property
    def vector_dimension(self) -> int:
        """获取向量维度"""
        if not self.is_initialized:
            raise RuntimeError("Embedding服务未初始化")
        
        if self._api_provider == "aliyun" and self._api_client:
            return self._api_client.get_vector_dimension()
        elif self._api_provider == "local" and self._embedder:
            return self._embedder.model.config.hidden_size
        else:
            raise RuntimeError("未知的 API Provider 或模型未初始化")

    def generate_embedding(
        self,
        text: Optional[str] = None,
        image: Optional[Union[str, Image.Image]] = None,
        instruction: Optional[str] = None,
        normalize: bool = True
    ) -> List[float]:
        """
        生成单个输入的Embedding向量

        Args:
            text: 文本内容
            image: 图片路径或PIL Image对象
            instruction: 指令提示词
            normalize: 是否归一化向量

        Returns:
            向量列表
        """
        if not self.is_initialized:
            raise RuntimeError("Embedding服务未初始化，请先调用initialize()")

        # 根据 Provider 选择调用方式
        if self._api_provider == "aliyun" and self._api_client:
            # API 调用
            image_path = None
            if image:
                if isinstance(image, Image.Image):
                    # 保存临时图片
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
                        # 处理 RGBA 模式图片，转换为 RGB 模式以兼容 JPEG
                        if image.mode == 'RGBA':
                            # 创建白色背景，将透明部分填充为白色
                            background = Image.new('RGB', image.size, (255, 255, 255))
                            background.paste(image, mask=image.split()[-1])  # 使用 alpha 通道作为掩码
                            image = background
                        elif image.mode != 'RGB':
                            # 其他模式也转换为 RGB
                            image = image.convert('RGB')
                        
                        image.save(f.name, format='JPEG', quality=95)
                        image_path = f.name
                else:
                    image_path = str(image)
            
            return self._api_client.generate_embedding(
                text=text,
                image=image_path,
                instruction=instruction,
                normalize=normalize
            )
        elif self._api_provider == "local" and self._embedder:
            # 本地模型调用
            input_data = {
                "text": text,
                "image": image,
                "instruction": instruction
            }
            embeddings = self._embedder.process([input_data], normalize=normalize)
            return embeddings[0].cpu().tolist()
        else:
            raise RuntimeError("未知的 API Provider 或模型未初始化")

    def generate_embeddings_batch(
        self,
        inputs: List[Dict[str, Any]],
        normalize: bool = True
    ) -> List[List[float]]:
        """
        批量生成Embedding向量

        Args:
            inputs: 输入列表，每个元素包含text、image、instruction等字段
            normalize: 是否归一化向量

        Returns:
            向量列表的列表
        """
        if not self.is_initialized:
            raise RuntimeError("Embedding服务未初始化，请先调用initialize()")

        # 根据 Provider 选择调用方式
        if self._api_provider == "aliyun" and self._api_client:
            return self._api_client.generate_embeddings_batch(inputs, normalize=normalize)
        elif self._api_provider == "local" and self._embedder:
            embeddings = self._embedder.process(inputs, normalize=normalize)
            return embeddings.cpu().tolist()
        else:
            raise RuntimeError("未知的 API Provider 或模型未初始化")

    def generate_text_embedding(
        self,
        text: str,
        instruction: Optional[str] = None,
        normalize: bool = True
    ) -> List[float]:
        """
        生成纯文本的Embedding向量

        Args:
            text: 文本内容
            instruction: 指令提示词
            normalize: 是否归一化向量

        Returns:
            向量列表
        """
        return self.generate_embedding(
            text=text,
            instruction=instruction,
            normalize=normalize
        )

    def generate_image_embedding(
        self,
        image: Union[str, Image.Image],
        instruction: Optional[str] = None,
        normalize: bool = True
    ) -> List[float]:
        """
        生成图片的Embedding向量

        Args:
            image: 图片路径或PIL Image对象
            instruction: 指令提示词
            normalize: 是否归一化向量

        Returns:
            向量列表
        """
        return self.generate_embedding(
            image=image,
            instruction=instruction,
            normalize=normalize
        )

    def generate_multimodal_embedding(
        self,
        text: str,
        image: Union[str, Image.Image],
        instruction: Optional[str] = None,
        normalize: bool = True
    ) -> List[float]:
        """
        生成图文混合的Embedding向量

        Args:
            text: 文本内容
            image: 图片路径或PIL Image对象
            instruction: 指令提示词
            normalize: 是否归一化向量

        Returns:
            向量列表
        """
        return self.generate_embedding(
            text=text,
            image=image,
            instruction=instruction,
            normalize=normalize
        )


# 全局服务实例
embedding_service = EmbeddingService()


def get_embedding_service() -> EmbeddingService:
    """获取Embedding服务实例"""
    return embedding_service
