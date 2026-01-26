"""
社交媒体文案生成服务模块
负责调用多模态大模型生成朋友圈/小红书文案
"""

import base64
import logging
from typing import Optional, Dict, Any
from openai import OpenAI
from ..config import get_settings
from .storage_service import get_storage_service

logger = logging.getLogger(__name__)

class SocialMediaService:
    """
    社交媒体服务类
    提供基于图片的文案生成功能
    """
    
    _instance: Optional["SocialMediaService"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
        
    def __init__(self):
        self._initialized = getattr(self, '_initialized', False)
        if not self._initialized:
            self.settings = get_settings()
            self.storage_service = get_storage_service()
            self._client = None
            self._initialized = True
    
    def _get_client(self) -> OpenAI:
        """获取或初始化OpenAI客户端"""
        if self._client is None:
            api_key = self.settings.VISION_MODEL_API_KEY
            base_url = self.settings.VISION_MODEL_BASE_URL
            
            if not api_key:
                raise ValueError("未配置 VISION_MODEL_API_KEY，无法调用模型")
                
            self._client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
        return self._client

    def _encode_image(self, image_content: bytes) -> str:
        """将图片内容编码为base64字符串"""
        return base64.b64encode(image_content).decode('utf-8')

    def generate_caption(
        self, 
        image_uuid: str, 
        style: str = "简洁", 
        purpose: str = "生活分享"
    ) -> Dict[str, Any]:
        """
        生成社交媒体文案
        
        Args:
            image_uuid: 图片UUID
            style: 文案风格
            purpose: 发帖用途
            
        Returns:
            包含生成的文案和状态的字典
        """
        try:
            # 1. 获取图片
            if not self.storage_service.is_initialized:
                # 尝试初始化（使用默认配置，实际应在应用启动时初始化）
                self.storage_service.initialize(self.settings.STORAGE_PATH)
            
            if not self.storage_service.image_exists(image_uuid):
                return {
                    "status": "error",
                    "message": f"图片不存在: {image_uuid}",
                    "caption": None
                }
                
            image_data = self.storage_service.get_image(image_uuid)
            if not image_data:
                return {
                    "status": "error", 
                    "message": "无法读取图片内容",
                    "caption": None
                }
                
            content, media_type = image_data
            base64_image = self._encode_image(content)
            
            # 2. 构建提示词
            prompt = (
                f"请你作为一位社交媒体运营专家，为这张图片写一段文案。\n"
                f"【风格要求】：{style}\n"
                f"【发布用途】：{purpose}\n"
                f"请直接输出文案内容，不要包含'好的'、'当然'等客套话。文案应适当包含emoji表情，使其更生动。"
            )
            
            # 3. 调用模型
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.settings.VISION_MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
            )
            
            caption = response.choices[0].message.content
            
            return {
                "status": "success",
                "message": "文案生成成功",
                "caption": caption
            }
            
        except Exception as e:
            logger.error(f"生成文案失败: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"生成文案失败: {str(e)}",
                "caption": None
            }

# 全局实例
social_service = SocialMediaService()
