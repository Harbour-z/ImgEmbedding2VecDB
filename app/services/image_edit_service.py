"""
图片编辑服务模块
使用 qwen-image-edit-plus 模型进行图片风格转换和编辑
"""

import logging
import base64
import httpx
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from io import BytesIO
from datetime import datetime
import dashscope

from ..config import get_settings

logger = logging.getLogger(__name__)


class ImageEditService:
    """
    图片编辑服务类
    
    职责：
    1. 调用 qwen-image-edit-plus 模型进行图片编辑
    2. 支持动漫风格转换等多种编辑功能
    3. 处理图片上传和结果保存
    4. 管理元数据记录
    """

    _instance: Optional["ImageEditService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._initialized = getattr(self, '_initialized', False)
        self._api_key: Optional[str] = None
        self._base_url: str = "https://dashscope.aliyuncs.com/api/v1"
        self._model_name: str = "qwen-image-edit-plus"

    def initialize(self) -> None:
        """
        初始化图片编辑服务
        """
        if self._initialized:
            logger.info("图片编辑服务已初始化")
            return

        settings = get_settings()
        
        # 从环境变量获取 API Key（复用 OPENAI_API_KEY）
        self._api_key = settings.OPENAI_API_KEY
        
        if not self._api_key:
            logger.warning("未配置 API Key，图片编辑服务将不可用")
            return

        # 设置基础 URL（使用北京地域）
        self._base_url = settings.OPENAI_BASE_URL or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
        logger.info(f"图片编辑服务初始化完成，模型: {self._model_name}")
        self._initialized = True

    @property
    def is_initialized(self) -> bool:
        return self._initialized and self._api_key is not None

    def _encode_image_to_base64(self, image_data: bytes, format: str = "jpeg") -> str:
        """
        将图片数据编码为 Base64 格式
        
        Args:
            image_data: 图片二进制数据
            format: 图片格式（jpeg, png 等）
            
        Returns:
            Base64 编码字符串
        """
        mime_type = f"image/{format}"
        base64_data = base64.b64encode(image_data).decode('utf-8')
        return f"data:{mime_type};base64,{base64_data}"

    def _encode_image_path_to_base64(self, image_path: str) -> str:
        """
        将图片文件路径编码为 Base64 格式
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            Base64 编码字符串
        """
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # 根据文件扩展名确定格式
        ext = Path(image_path).suffix.lower().lstrip('.')
        if ext in ['jpg', 'jpeg']:
            format = 'jpeg'
        elif ext == 'png':
            format = 'png'
        elif ext == 'gif':
            format = 'gif'
        elif ext == 'webp':
            format = 'webp'
        elif ext == 'bmp':
            format = 'bmp'
        else:
            format = 'jpeg'  # 默认
        
        return self._encode_image_to_base64(image_data, format)

    async def edit_image(
        self,
        image_data: bytes,
        prompt: str,
        negative_prompt: str = " ",
        prompt_extend: bool = True,
        n: int = 1,
        size: Optional[str] = None,
        watermark: bool = False,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        调用图片编辑 API
        
        Args:
            image_data: 图片二进制数据
            prompt: 编辑提示词
            negative_prompt: 反向提示词
            prompt_extend: 是否开启智能提示词改写
            n: 生成图片数量
            size: 输出图片分辨率
            watermark: 是否添加水印
            seed: 随机数种子
            
        Returns:
            包含成功状态和图片URL的字典
        """
        if not self.is_initialized:
            return {
                "success": False,
                "error": "图片编辑服务未初始化，请检查配置"
            }
        
        # 将图片数据转换为 Base64，并添加 data URI 前缀
        image_base64 = f"data:image/png;base64,{base64.b64encode(image_data).decode('utf-8')}"
        
        # 构建消息内容 - qwen-image-edit-plus 只支持单图输入
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": image_base64},
                    {"text": prompt}
                ]
            }
        ]
        
        # 构建参数字典
        call_parameters = {
            "n": n,
            "watermark": watermark,
            "negative_prompt": negative_prompt,
            "prompt_extend": prompt_extend
        }
        
        if size:
            call_parameters["size"] = size
        if seed is not None:
            call_parameters["seed"] = seed
        
        logger.info(f"调用图片编辑API: {self._model_name}, prompt: {prompt}")
        logger.debug(f"参数: {call_parameters}")
        
        try:
            # 使用 DashScope SDK 调用 API
            response = dashscope.MultiModalConversation.call(
                api_key=self._api_key,
                model=self._model_name,
                messages=messages,
                stream=False,
                **call_parameters
            )
            
            logger.info(f"图片编辑API调用成功")
            
            # 检查响应状态
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"API 调用失败: {response.code} - {response.message}"
                }
            
            # 解析结果
            if response.output and len(response.output.choices) > 0:
                contents = response.output.choices[0].message.content
                
                # 提取生成的图片 URL
                image_urls = []
                for content in contents:
                    if "image" in content:
                        image_urls.append(content["image"])
                
                return {
                    "success": True,
                    "image_urls": image_urls,
                    "prompt": prompt,
                    "model_used": self._model_name,
                    "parameters": call_parameters
                }
            
            return {
                "success": False,
                "error": "无法解析 API 响应",
                "response": str(response.output)
            }
                
        except Exception as e:
            logger.error(f"图片编辑处理异常: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"处理异常: {str(e)}"
            }

    async def download_generated_image(self, image_url: str) -> Optional[bytes]:
        """
        下载生成的图片
        
        Args:
            image_url: 图片 URL
            
        Returns:
            图片二进制数据
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                return response.content
        except Exception as e:
            logger.error(f"下载图片失败: {e}")
            return None

    async def edit_image_and_save(
        self,
        image_data: bytes,
        prompt: str,
        source_image_id: Optional[str] = None,
        style_tag: Optional[str] = None,
        auto_index: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        编辑图片并保存到存储服务
        
        Args:
            image_data: 原始图片数据
            prompt: 编辑提示词
            source_image_id: 源图片 ID（用于元数据记录）
            style_tag: 风格标签（用于元数据记录）
            auto_index: 是否自动索引到向量数据库
            **kwargs: 其他编辑参数
            
        Returns:
            包含保存结果和元数据的字典
        """
        from . import get_storage_service
        from .search_service import get_search_service
        from ..models import ImageMetadata
        import asyncio
        
        # 调用编辑 API
        edit_result = await self.edit_image(image_data, prompt, **kwargs)
        
        if not edit_result.get("success"):
            return edit_result
        
        # 下载生成的图片
        image_urls = edit_result.get("image_urls", [])
        if not image_urls:
            return {
                "success": False,
                "error": "未生成任何图片"
            }
        
        saved_images = []
        storage_svc = get_storage_service()
        search_svc = get_search_service()
        
        for i, url in enumerate(image_urls):
            image_bytes = await self.download_generated_image(url)
            if not image_bytes:
                logger.warning(f"下载第 {i+1} 张图片失败")
                continue
            
            try:
                # 保存图片到存储服务
                save_result = storage_svc.save_image(
                    image_bytes,
                    f"edited_{i+1}.png"
                )
                
                # 构建完整的元数据（包含存储信息和编辑信息）
                metadata = {
                    "source_image_id": source_image_id,
                    "edit_prompt": prompt,
                    "edit_style": style_tag or "unknown",
                    "edit_model": self._model_name,
                    "edit_parameters": kwargs,
                    "edit_time": datetime.now().isoformat(),
                    "tags": [style_tag or "edited"] if style_tag else ["edited"]
                }
                
                # 构建用于索引的 ImageMetadata
                index_metadata = ImageMetadata(
                    filename=f"edited_{i+1}.png",
                    file_path=save_result["full_path"],
                    file_size=save_result["file_size"],
                    width=save_result["width"],
                    height=save_result["height"],
                    format=save_result["format"],
                    created_at=save_result["created_at"],
                    tags=metadata["tags"],
                    description=f"编辑后的图片: {prompt}"
                )
                
                # 异步索引图片到向量数据库
                if auto_index and search_svc.is_initialized:
                    asyncio.create_task(
                        self._async_index_image(
                            image_id=save_result["id"],
                            image_path=save_result["full_path"],
                            metadata=index_metadata.model_dump(),
                            search_svc=search_svc
                        )
                    )
                    logger.info(f"已触发异步索引: {save_result['id']}")
                    metadata["indexed"] = "processing"
                else:
                    metadata["indexed"] = False
                
                saved_images.append({
                    "image_id": save_result["id"],
                    "url": save_result["url"],
                    "metadata": metadata
                })
                
                logger.info(f"编辑图片保存成功: {save_result['id']}")
                
            except Exception as e:
                logger.error(f"保存编辑图片失败: {e}", exc_info=True)
        
        return {
            "success": len(saved_images) > 0,
            "saved_images": saved_images,
            "total_generated": len(image_urls),
            "total_saved": len(saved_images),
            "edit_result": edit_result
        }
    
    async def _async_index_image(
        self,
        image_id: str,
        image_path: str,
        metadata: Dict[str, Any],
        search_svc: Any
    ):
        """
        异步索引图片到向量数据库
        
        注意：索引失败不会影响图片保存，但会导致该图片无法被搜索到
        """
        try:
            logger.info(f"开始异步索引图片: {image_id}")
            
            success = search_svc.index_image(
                image_id=image_id,
                image_path=image_path,
                metadata=metadata
            )
            
            if success:
                logger.info(f"✅ 异步索引成功: {image_id}")
            else:
                logger.error(f"❌ 异步索引失败: {image_id} - index_image返回False")
                
        except Exception as e:
            logger.error(f"❌ 异步索引异常: {image_id}", exc_info=True)
            logger.error(f"   错误详情: {str(e)}")
            logger.error(f"   图片路径: {image_path}")
            # 注意：异步索引失败不影响图片存储，图片文件已成功保存


# 全局服务实例
_image_edit_service: Optional[ImageEditService] = None


def get_image_edit_service() -> ImageEditService:
    """获取图片编辑服务实例"""
    global _image_edit_service
    if _image_edit_service is None:
        _image_edit_service = ImageEditService()
    return _image_edit_service
