"""
阿里云 DashScope Embedding API 客户端
支持 qwen3-vl-embedding 模型的 API 调用
"""

import logging
from typing import Optional, List, Dict, Any
from http import HTTPStatus
import dashscope

from ..config import get_settings

logger = logging.getLogger(__name__)


class AliyunEmbeddingClient:
    """
    阿里云 DashScope Embedding API 客户端
    
    使用 DashScope SDK 调用 qwen3-vl-embedding 模型生成多模态融合向量
    """
    
    _instance: Optional["AliyunEmbeddingClient"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self._api_key: Optional[str] = None
        self._model_name: Optional[str] = None
        self._dimension: int = 2560  # 默认 2560，初始化时会从配置读取
        
    def initialize(self) -> None:
        """初始化 API 客户端"""
        settings = get_settings()
        
        if settings.EMBEDDING_API_PROVIDER != "aliyun":
            logger.warning(f"Embedding provider is '{settings.EMBEDDING_API_PROVIDER}', not 'aliyun', skipping API client init")
            return
            
        self._api_key = settings.ALIYUN_EMBEDDING_API_KEY
        self._model_name = settings.ALIYUN_EMBEDDING_MODEL_NAME
        self._dimension = settings.ALIYUN_EMBEDDING_DIMENSION
        
        if not self._api_key:
            raise ValueError("未配置 ALIYUN_EMBEDDING_API_KEY，无法初始化 API 客户端")
        
        logger.info(f"阿里云 Embedding API 客户端初始化完成 (Model: {self._model_name}, Dimension: {self._dimension})")
    
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._api_key is not None
    
    def generate_embedding(
        self,
        text: Optional[str] = None,
        image: Optional[str] = None,
        instruction: Optional[str] = None,
        normalize: bool = True
    ) -> List[float]:
        """
        通过 API 生成 Embedding 向量（多模态融合向量）
        
        Args:
            text: 文本内容
            image: 图片路径或 URL
            instruction: 指令提示词（暂未使用，保留接口兼容性）
            normalize: 是否归一化（API 默认归一化）
            
        Returns:
            向量列表（与本地模型格式一致）
        """
        if not self.is_initialized:
            raise RuntimeError("API 客户端未初始化")
            
        if not text and not image:
            raise ValueError("必须提供 text 或 image 参数")
        
        # 构建输入数据（多模态融合向量）
        input_data = {}
        
        if text:
            input_data["text"] = text
        
        if image:
            # 如果是本地路径，转换为文件路径（DashScope SDK 会自动处理）
            # 如果是 URL，直接使用
            input_data["image"] = image
        
        # 封装成列表格式
        input_list = [input_data]
        
        try:
            # 调用 DashScope 多模态 Embedding API
            # 指定向量维度参数
            resp = dashscope.MultiModalEmbedding.call(
                api_key=self._api_key,
                model=self._model_name,
                input=input_list,
                parameters={"dimension": self._dimension}
            )
            
            # 检查响应状态
            if resp.status_code != HTTPStatus.OK:
                raise RuntimeError(f"API 调用失败: {resp.code} - {resp.message}")
            
            # 提取向量
            if resp.output:
                # resp.output 可能是字典或对象
                output = resp.output if isinstance(resp.output, dict) else resp.output.__dict__
                embeddings = output.get('embeddings', [])
                if len(embeddings) > 0:
                    embedding = embeddings[0].get('embedding', embeddings[0])
                    # 转换为列表格式
                    if hasattr(embedding, '__iter__'):
                        return list(embedding)
                    else:
                        return list(embedding) if isinstance(embedding, (list, tuple)) else [embedding]
                else:
                    raise RuntimeError(f"API 响应格式异常: {output}")
            else:
                raise RuntimeError(f"API 响应格式异常: {resp.output}")
            
        except Exception as e:
            logger.error(f"API 调用失败: {e}", exc_info=True)
            raise RuntimeError(f"API 调用失败: {str(e)}")
    
    def generate_embeddings_batch(
        self,
        inputs: List[Dict[str, Any]],
        normalize: bool = True
    ) -> List[List[float]]:
        """
        批量生成 Embedding 向量
        
        Args:
            inputs: 输入列表，每个元素包含 text、image、instruction 等字段
            normalize: 是否归一化
            
        Returns:
            向量列表
        """
        if not self.is_initialized:
            raise RuntimeError("API 客户端未初始化")
        
        # 注意：qwen2.5-vl-embedding 不支持批量调用（每个输入对象只能包含一种类型）
        # 因此这里改为逐个调用
        embeddings = []
        for inp in inputs:
            embedding = self.generate_embedding(
                text=inp.get("text"),
                image=inp.get("image"),
                instruction=inp.get("instruction"),
                normalize=normalize
            )
            embeddings.append(embedding)
        
        return embeddings
    
    def set_dimension(self, dimension: int) -> None:
        """设置向量维度（支持 2560, 2048, 1536, 1024, 768, 512, 256）"""
        valid_dimensions = [2560, 2048, 1536, 1024, 768, 512, 256]
        if dimension not in valid_dimensions:
            raise ValueError(f"不支持的向量维度: {dimension}，支持的维度: {valid_dimensions}")
        self._dimension = dimension
        logger.info(f"向量维度已设置为: {dimension}")
    
    def get_vector_dimension(self) -> int:
        """获取当前向量维度"""
        return self._dimension


# 全局实例
_aliyun_client: Optional[AliyunEmbeddingClient] = None


def get_aliyun_client() -> AliyunEmbeddingClient:
    """获取阿里云 Embedding API 客户端实例"""
    global _aliyun_client
    if _aliyun_client is None:
        _aliyun_client = AliyunEmbeddingClient()
    return _aliyun_client
