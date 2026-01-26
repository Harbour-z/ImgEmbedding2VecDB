"""
智能图片推荐API路由
提供多模态AI模型集成的图片分析和推荐接口
"""

import logging
import json
from typing import List, Optional, Union
from fastapi import APIRouter, UploadFile, File, Form, Body, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator

from ..services import get_image_recommendation_service, ImageRecommendationService
from ..models import BaseResponse, ResponseStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/image-recommendation", tags=["Image Recommendation"])


class ImageRecommendationRequest(BaseModel):
    """图片推荐请求"""
    images: List[str] = Field(..., description="图片ID列表")
    user_preference: Optional[str] = Field(None, description="用户偏好或分析维度（可选）")
    
    @field_validator('images', mode='before')
    @classmethod
    def parse_images(cls, v):
        """
        解析 images 参数，支持两种格式：
        1. List[str]: 标准数组格式
        2. str: OpenJiuwen 序列化的字符串格式，如 "['id1', 'id2']"
        """
        if isinstance(v, str):
            try:
                return json.loads(v.replace("'", '"'))
            except json.JSONDecodeError:
                raise ValueError(f"无法解析 images 参数: {v}")
        elif isinstance(v, list):
            return v
        else:
            raise ValueError(f"images 参数必须是字符串或数组，当前类型: {type(v)}")


class ImageRecommendationUploadRequest(BaseModel):
    """图片推荐上传请求"""
    user_preference: Optional[str] = Field(None, description="用户偏好或分析维度（可选）")


@router.post(
    "/analyze",
    summary="智能图片推荐",
    description="""
    使用多模态AI模型（qwen3-max + qwen3-vl-plus）进行深度图片分析和推荐
    
    **工作流程**：
    1. 使用qwen3-max生成优化的分析提示词
    2. 使用qwen3-vl-plus对每张图片进行多模态分析
    3. 从艺术维度（构图、色彩、光影、主题、情感、创意、故事性）评估
    4. 综合评分并推荐最佳图片
    
    **评估维度**：
    - 构图美学（25%权重）
    - 色彩搭配（20%权重）
    - 光影运用（15%权重）
    - 主题表达（15%权重）
    - 情感传达（10%权重）
    - 创意独特性（8%权重）
    - 故事性（7%权重）
    
    **严格禁止**：仅基于分辨率、文件大小等技术参数进行评价
    """
)
async def recommend_images_by_ids(
    request: ImageRecommendationRequest,
    rec_svc: ImageRecommendationService = Depends(get_image_recommendation_service)
):
    """
    根据图片ID列表进行智能推荐
    
    Args:
        request: 推荐请求，包含图片ID列表和用户偏好
        rec_svc: 图片推荐服务
        
    Returns:
        推荐结果
    """
    import logging
    import json
    logger = logging.getLogger(__name__)
    
    logger.info(f"[API] 收到图片推荐请求: images={request.images}, user_preference={request.user_preference}")
    
    if not rec_svc.is_initialized:
        raise HTTPException(status_code=503, detail="图片推荐服务未初始化")
    
    images_list = request.images
    
    if not images_list:
        raise HTTPException(status_code=400, detail="图片ID列表不能为空")
    
    if len(images_list) > 10:
        raise HTTPException(status_code=400, detail="最多支持分析10张图片")
        
    if len(request.images) > 10:
        raise HTTPException(status_code=400, detail="最多支持分析10张图片")
        
    logger.info(
        f"接收到图片推荐请求: "
        f"图片数量={len(request.images)}, "
        f"用户偏好={request.user_preference}"
    )
    
    try:
        # 获取图片数据
        from ..services import get_storage_service
        storage_svc = get_storage_service()
        
        images_data = []
        valid_ids = []
        
        for image_id in request.images:
            try:
                image_path = storage_svc.get_image_path(image_id)
                if image_path:
                    with open(image_path, 'rb') as f:
                        images_data.append(f.read())
                        valid_ids.append(image_id)
            except Exception as e:
                logger.warning(f"无法读取图片 {image_id}: {e}")
                
        if not images_data:
            raise HTTPException(status_code=404, detail="未找到有效的图片")
            
        # 调用推荐服务
        result = await rec_svc.recommend_images(
            images=images_data,
            image_ids=valid_ids,
            user_preference=request.user_preference
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"图片推荐失败: {result.get('error')}"
            )
            
        logger.info(
            f"图片推荐成功: "
            f"推荐ID={result.get('recommendation', {}).get('best_image_id')}"
        )
        
        return BaseResponse(
            status=ResponseStatus.SUCCESS,
            message="图片推荐完成",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图片推荐异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"图片推荐失败: {str(e)}"
        )


@router.post(
    "/upload-analyze",
    summary="上传并分析图片",
    description="""
    直接上传图片文件并进行智能分析推荐
    
    支持一次性上传多张图片（最多10张），系统将自动：
    1. 保存图片到存储
    2. 生成图片向量
    3. 调用多模态AI分析
    4. 返回推荐结果
    """
)
async def recommend_uploaded_images(
    files: List[UploadFile] = File(..., description="上传的图片文件"),
    user_preference: Optional[str] = Form(None, description="用户偏好或分析维度（可选）"),
    rec_svc: ImageRecommendationService = Depends(get_image_recommendation_service)
):
    """
    上传图片并进行分析推荐
    
    Args:
        files: 上传的图片文件列表
        user_preference: 用户偏好
        rec_svc: 图片推荐服务
        
    Returns:
        推荐结果
    """
    if not rec_svc.is_initialized:
        raise HTTPException(status_code=503, detail="图片推荐服务未初始化")
        
    if not files:
        raise HTTPException(status_code=400, detail="必须至少上传一张图片")
        
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="最多支持分析10张图片")
        
    logger.info(
        f"接收到上传推荐请求: "
        f"图片数量={len(files)}, "
        f"用户偏好={user_preference}"
    )
    
    try:
        # 读取图片数据
        images_data = []
        
        for file in files:
            content = await file.read()
            images_data.append(content)
            logger.debug(f"读取图片: {file.filename}, 大小: {len(content)} bytes")
        
        # 调用推荐服务（不存储，仅分析）
        result = await rec_svc.recommend_images(
            images=images_data,
            image_ids=None,
            user_preference=user_preference
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"图片推荐失败: {result.get('error')}"
            )
            
        logger.info(
            f"上传图片推荐成功: "
            f"推荐ID={result.get('recommendation', {}).get('best_image_id')}"
        )
        
        return BaseResponse(
            status=ResponseStatus.SUCCESS,
            message="图片推荐完成",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传图片推荐异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"图片推荐失败: {str(e)}"
        )


@router.get(
    "/health",
    summary="健康检查",
    description="检查图片推荐服务是否可用"
)
async def health_check(rec_svc: ImageRecommendationService = Depends(get_image_recommendation_service)):
    """
    健康检查
    """
    return {
        "status": "healthy" if rec_svc.is_initialized else "uninitialized",
        "service": "image_recommendation_service"
    }
