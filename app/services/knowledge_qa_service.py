"""
知识问答服务模块
负责调用多模态大模型进行基于图片的智能问答
"""

import base64
import logging
from typing import Optional, Dict, Any
from openai import OpenAI
from ..config import get_settings
from .storage_service import get_storage_service

logger = logging.getLogger(__name__)


class KnowledgeQAService:
    """
    知识问答服务类
    提供基于图片的智能问答功能
    """

    _instance: Optional["KnowledgeQAService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._initialized = getattr(self, "_initialized", False)
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
        return base64.b64encode(image_content).decode("utf-8")

    def knowledge_qa(
        self,
        image_uuid: str,
        question: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        基于图片的知识问答

        Args:
            image_uuid: 图片UUID
            question: 用户的问题
            context: 额外上下文信息（可选）

        Returns:
            包含问答结果和状态的字典
        """
        try:
            # 1. 获取图片
            if not self.storage_service.is_initialized:
                self.storage_service.initialize(self.settings.STORAGE_PATH)

            if not self.storage_service.image_exists(image_uuid):
                return {
                    "status": "error",
                    "message": f"图片不存在: {image_uuid}",
                    "answer": None
                }

            image_data = self.storage_service.get_image(image_uuid)
            if not image_data:
                return {
                    "status": "error",
                    "message": "无法读取图片内容",
                    "answer": None
                }

            content, media_type = image_data
            base64_image = self._encode_image(content)

            # 2. 构建系统提示词
            system_prompt = (
                "你是一位专业的知识问答助手，擅长分析图片内容并结合用户问题提供准确、有用的回答。\n\n"
                "【核心能力】：\n"
                "1. 植物识别：能够识别多肉植物等植物的品种，并提供养护要点\n"
                "2. 情感分析：能够从照片中分析人物情绪状态，识别开心、温馨等情感\n"
                "3. 物体识别：能够识别图片中的各种物体、食材、物品等\n"
                "4. 场景理解：能够理解照片的场景、环境、活动等\n"
                "5. 创意写作：能够基于图片内容创作祝福文案、菜谱推荐等创意内容\n\n"
                "【输出要求】：\n"
                "1. 回答要准确、实用、有帮助\n"
                "2. 使用清晰的结构化表达（如分点说明）\n"
                "3. 适当使用emoji表情使回答更生动\n"
                "4. 如果图片内容不足以回答问题，请诚实说明\n"
                "5. 不要包含'好的'、'当然'等客套话，直接进入主题"
            )

            # 3. 构建用户提示词
            user_prompt = question
            if context:
                user_prompt = f"{context}\n\n问题：{question}"

            # 4. 调用模型
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.settings.VISION_MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
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

            answer = response.choices[0].message.content

            return {
                "status": "success",
                "message": "问答成功",
                "answer": answer
            }

        except Exception as e:
            logger.error(f"知识问答失败: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"知识问答失败: {str(e)}",
                "answer": None
            }


# 全局实例
knowledge_qa_service = KnowledgeQAService()


def get_knowledge_qa_service() -> KnowledgeQAService:
    """获取知识问答服务实例"""
    return knowledge_qa_service
