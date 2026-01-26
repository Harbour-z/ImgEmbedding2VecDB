"""
智能图片推荐服务
集成qwen3-max和qwen3-vl-plus模型，提供专业的图片分析和推荐功能
"""

import logging
import base64
import io
from typing import List, Dict, Any, Optional
from PIL import Image
from httpx import AsyncClient, TimeoutException, HTTPStatusError
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class ImageRecommendationService:
    """智能图片推荐服务"""
    
    def __init__(self):
        self._initialized = False
        self._llm_client: Optional[AsyncClient] = None
        self._vl_client: Optional[AsyncClient] = None
        self._settings = None
        
    def initialize(self, settings):
        """
        初始化服务
        
        Args:
            settings: 应用配置对象
        """
        if self._initialized:
            logger.info("图片推荐服务已初始化")
            return
            
        self._settings = settings
        
        # 初始化HTTP客户端
        timeout = 120  # 2分钟超时
        
        # LLM客户端（qwen3-max用于生成提示词）
        self._llm_client = AsyncClient(
            base_url=settings.OPENAI_BASE_URL,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
        )
        
        # VL客户端（qwen3-vl-plus用于图片分析）
        self._vl_client = AsyncClient(
            base_url=settings.OPENAI_BASE_URL,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
        )
        
        logger.info(
            f"图片推荐服务初始化完成 "
            f"(LLM: {settings.OPENAI_MODEL_NAME}, VL: {settings.VISION_MODEL_NAME})"
        )
        self._initialized = True
        
    def is_initialized(self) -> bool:
        """检查服务是否已初始化"""
        return self._initialized
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutException, HTTPStatusError)),
        reraise=True
    )
    async def _generate_analysis_prompt(self, image_count: int, user_preference: Optional[str] = None) -> str:
        """
        使用qwen3-max生成针对qwen3-vl-plus的优化提示词
        
        Args:
            image_count: 待分析图片数量
            user_preference: 用户偏好或分析维度（可选）
            
        Returns:
            优化后的提示词
        """
        if not self._initialized:
            raise RuntimeError("图片推荐服务未初始化")
            
        base_prompt = f"""你是一位专业的摄影师和艺术评论家，精通摄影美学、视觉艺术和图像分析。你的任务是对{image_count}张照片进行深度多模态分析，并推荐出最佳的一张。

【严格禁止的评价维度】
- 严禁仅基于分辨率（像素数量）、文件大小、压缩质量、EXIF参数等纯技术规格进行评价
- 不得因为某张图片分辨率更高或文件更大就直接判定为更好

【强制要求的评价维度】
你必须从以下艺术与内容维度进行深度分析：

1. 构图美学
   - 构图是否遵循黄金分割、三分法、引导线等经典法则
   - 主体位置是否恰当，画面是否平衡
   - 视觉焦点是否清晰，层次感如何
   - 前景、中景、背景的协调性

2. 色彩搭配
   - 色调是否和谐统一，是否有色彩冲突
   - 色彩饱和度、明度是否适中
   - 主色调与辅助色的配合是否恰当
   - 是否有有效的色彩对比或渐变效果

3. 光影运用
   - 光线方向、质量（顺光、逆光、侧光、漫射光）
   - 光影层次感和立体感表现
   - 高光和阴影的处理是否自然
   - 是否有光斑、曝光问题

4. 主题表达清晰度
   - 主题是否明确突出
   - 画面是否传达了明确的意图
   - 主体与背景的关系是否恰当
   - 是否有视觉干扰元素

5. 情感传达强度
   - 图片是否能引发观看者的情感共鸣
   - 情绪氛围营造是否成功
   - 画面故事感和代入感如何
   - 是否有独特的情感表达

6. 创意独特性
   - 视角是否新颖（鸟瞰、低角度、微距等）
   - 拍摄手法是否有创新
   - 是否有独特的视觉元素或构图
   - 是否避免了常见俗套

7. 故事性
   - 图片是否讲述了一个完整或引人遐想的故事
   - 视觉叙事是否连贯
   - 是否有引人深思的细节
   - 画面元素的组合是否具有叙事性

【输出格式要求】
请按照以下JSON格式输出分析结果，不要添加任何额外的解释性文字：

```json
{{
  "analysis": {{
    "image_1": {{
      "id": "图片1的ID或标识",
      "composition_score": 8.5,
      "composition_analysis": "构图分析详细描述...",
      "color_score": 9.0,
      "color_analysis": "色彩分析详细描述...",
      "lighting_score": 8.0,
      "lighting_analysis": "光影分析详细描述...",
      "theme_score": 8.5,
      "theme_analysis": "主题表达分析详细描述...",
      "emotion_score": 9.0,
      "emotion_analysis": "情感传达分析详细描述...",
      "creativity_score": 7.5,
      "creativity_analysis": "创意独特性分析详细描述...",
      "story_score": 8.0,
      "story_analysis": "故事性分析详细描述...",
      "overall_score": 8.35,
      "overall_analysis": "综合评价总结..."
    }},
    "image_2": {{...}},
    "image_3": {{...}}
  }},
  "recommendation": {{
    "best_image_id": "最佳图片的ID或标识",
    "recommendation_reason": "推荐理由详细说明...",
    "alternative_image_ids": ["其他图片ID列表"],
    "key_strengths": ["主要优势点1", "主要优势点2"],
    "potential_improvements": ["可改进点1", "可改进点2"]
  }}
}}
```

【重要提示】
- 本分析任务必须由qwen3-vl-plus模型执行，以确保多模态理解能力被正确应用
- 每个维度的评分为0-10分，保留1位小数
- 综合分数（overall_score）是7个维度的加权平均，权重如下：构图25%、色彩20%、光影15%、主题15%、情感10%、创意8%、故事7%
- 分析描述要具体、专业，避免空泛的评价
- 推荐理由要突出最佳图片的核心优势"""

        # 如果有用户偏好，添加到提示词
        if user_preference:
            base_prompt += f"\n\n【用户偏好】\n{user_preference}\n\n在分析时，请特别关注用户提到的这些方面。"
            
        return base_prompt
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutException, HTTPStatusError)),
        reraise=True
    )
    async def _analyze_images_with_vl(
        self, 
        images_data: List[bytes], 
        prompt: str,
        image_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        使用qwen3-vl-plus进行多模态图片分析
        
        Args:
            images_data: 图片字节数据列表
            prompt: 分析提示词
            image_ids: 图片ID列表（可选）
            
        Returns:
            分析结果字典
        """
        if not self._initialized:
            raise RuntimeError("图片推荐服务未初始化")
            
        if not images_data:
            raise ValueError("图片列表不能为空")
            
        # 构建消息内容
        content = [
            {
                "type": "text",
                "text": prompt
            }
        ]
        
        # 添加图片
        for idx, img_data in enumerate(images_data):
            img_id = image_ids[idx] if image_ids and idx < len(image_ids) else f"image_{idx + 1}"
            
            # 编码图片为base64
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # 检测图片格式
            img = Image.open(io.BytesIO(img_data))
            img_format = img.format.lower() if img.format else 'jpeg'
            
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{img_format};base64,{img_base64}"
                }
            })
        
        # 构建请求
        payload = {
            "model": self._settings.VISION_MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        logger.info(
            f"开始调用qwen3-vl-plus分析{len(images_data)}张图片，"
            f"模型: {self._settings.VISION_MODEL_NAME}"
        )
        
        try:
            response = await self._vl_client.post(
                "/chat/completions",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 提取回复内容
            content_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            logger.info(
                f"qwen3-vl-plus分析完成，返回{len(content_text)}字符"
            )
            
            return {
                "success": True,
                "content": content_text,
                "model": self._settings.VISION_MODEL_NAME
            }
            
        except Exception as e:
            logger.error(f"qwen3-vl-plus分析失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "content": None
            }
            
    async def recommend_images(
        self,
        images: List[bytes],
        image_ids: Optional[List[str]] = None,
        user_preference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        智能图片推荐主流程
        
        Args:
            images: 图片字节数据列表
            image_ids: 图片ID列表（可选）
            user_preference: 用户偏好（可选）
            
        Returns:
            推荐结果字典
        """
        if not self._initialized:
            raise RuntimeError("图片推荐服务未初始化")
            
        if not images:
            raise ValueError("图片列表不能为空")
            
        if len(images) > 10:
            raise ValueError("最多支持分析10张图片")
            
        logger.info(
            f"开始智能图片推荐: 图片数量={len(images)}, "
            f"用户偏好={user_preference}"
        )
        
        try:
            # 步骤1: 使用qwen3-max生成优化提示词
            logger.info("步骤1: 使用qwen3-max生成分析提示词...")
            analysis_prompt = await self._generate_analysis_prompt(
                image_count=len(images),
                user_preference=user_preference
            )
            logger.info(f"提示词生成完成，长度: {len(analysis_prompt)} 字符")
            
            # 步骤2: 使用qwen3-vl-plus分析图片
            logger.info("步骤2: 使用qwen3-vl-plus进行多模态分析...")
            analysis_result = await self._analyze_images_with_vl(
                images_data=images,
                prompt=analysis_prompt,
                image_ids=image_ids
            )
            
            if not analysis_result.get("success"):
                return {
                    "success": False,
                    "error": "图片分析失败",
                    "details": analysis_result.get("error")
                }
                
            # 步骤3: 解析分析结果
            logger.info("步骤3: 解析分析结果...")
            import json
            import re
            
            try:
                content = analysis_result.get("content", "")
                
                # 尝试提取JSON
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = content
                    
                analysis_data = json.loads(json_str)
                
                logger.info(
                    f"分析结果解析成功: "
                    f"推荐图片={analysis_data.get('recommendation', {}).get('best_image_id')}"
                )
                
                return {
                    "success": True,
                    "analysis": analysis_data.get("analysis", {}),
                    "recommendation": analysis_data.get("recommendation", {}),
                    "model_used": self._settings.VISION_MODEL_NAME,
                    "total_images": len(images)
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                return {
                    "success": False,
                    "error": "分析结果解析失败",
                    "details": str(e),
                    "raw_content": content
                }
                
        except Exception as e:
            logger.error(f"图片推荐失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "details": None
            }


# 单例模式
_image_recommendation_service_instance: Optional[ImageRecommendationService] = None


def get_image_recommendation_service() -> ImageRecommendationService:
    """获取图片推荐服务实例"""
    global _image_recommendation_service_instance
    if _image_recommendation_service_instance is None:
        _image_recommendation_service_instance = ImageRecommendationService()
    return _image_recommendation_service_instance
