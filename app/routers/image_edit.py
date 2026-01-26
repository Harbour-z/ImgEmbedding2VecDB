"""
图片编辑API路由
提供基于 qwen-image-edit-plus 模型的图片风格转换和编辑功能
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel

from ..models import (
    BaseResponse,
    ResponseStatus,
    ImageEditRequest,
    ImageEditResponse,
    ImageEditResult,
)
from ..services import (
    get_storage_service,
    StorageService,
    get_image_edit_service,
    ImageEditService,
)

router = APIRouter(prefix="/image-edit", tags=["Image Editing"])


class ConfirmEditRequest(BaseModel):
    """确认编辑请求"""
    confirmed: bool = False
    image_id: str
    prompt: str
    negative_prompt: str = " "
    prompt_extend: bool = True
    n: int = 1
    size: Optional[str] = None
    watermark: bool = False
    seed: Optional[int] = None
    style_tag: Optional[str] = None


@router.post(
    "/edit",
    response_model=ImageEditResponse,
    summary="编辑图片",
    description="""
    使用 qwen-image-edit-plus 模型编辑图片，支持多种风格转换和编辑操作。
    
    **主要功能：**
    - 动漫风格转换
    - 图片风格迁移
    - 文字编辑
    - 物体增删改
    - 背景替换
    - 老照片处理
    
    **重要特性：**
    - 自动开启智能提示词改写（prompt_extend=true），优化简单描述的生成效果
    - 支持生成 1-6 张图片
    - 可自定义输出分辨率
    - 自动保存到图片画廊并记录元数据
    
    **使用示例：**
    ```json
    {
      "image_id": "img-uuid-1234",
      "prompt": "将图片转换为动漫风格",
      "style_tag": "anime",
      "n": 2
    }
    ```
    """
)
async def edit_image(
    request: ImageEditRequest,
    storage_svc: StorageService = Depends(get_storage_service),
    edit_svc: ImageEditService = Depends(get_image_edit_service)
):
    """
    编辑图片接口
    
    处理流程：
    1. 验证图片是否存在
    2. 调用 qwen-image-edit-plus 模型进行编辑
    3. 下载生成的图片
    4. 保存到存储服务
    5. 记录元数据（来源、风格、时间等）
    6. 返回编辑结果
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 验证图片编辑服务是否已初始化
    if not edit_svc.is_initialized:
        raise HTTPException(
            status_code=503,
            detail="图片编辑服务未初始化，请检查配置"
        )
    
    # 验证源图片是否存在
    if not storage_svc.image_exists(request.image_id):
        raise HTTPException(
            status_code=404,
            detail=f"图片不存在: {request.image_id}"
        )
    
    # 读取源图片数据
    image_path = storage_svc.get_image_path(request.image_id)
    if not image_path:
        raise HTTPException(
            status_code=404,
            detail=f"无法找到图片文件: {request.image_id}"
        )
    
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
    except Exception as e:
        logger.error(f"读取图片失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"读取图片失败: {str(e)}"
        )
    
    logger.info(
        f"开始编辑图片: {request.image_id}, "
        f"prompt: {request.prompt}, "
        f"style: {request.style_tag}"
    )
    
    # 调用编辑服务
    try:
        result = await edit_svc.edit_image_and_save(
            image_data=image_data,
            prompt=request.prompt,
            source_image_id=request.image_id,
            style_tag=request.style_tag,
            negative_prompt=request.negative_prompt,
            prompt_extend=request.prompt_extend,
            n=request.n,
            size=request.size,
            watermark=request.watermark,
            seed=request.seed
        )
        
        if result.get("success"):
            logger.info(
                f"图片编辑成功: {request.image_id}, "
                f"生成 {result.get('total_generated', 0)} 张, "
                f"保存 {result.get('total_saved', 0)} 张"
            )
            
            # 构建编辑结果
            edit_result = ImageEditResult(
                success=True,
                saved_images=result.get("saved_images", []),
                total_generated=result.get("total_generated", 0),
                total_saved=result.get("total_saved", 0),
                edit_result=result.get("edit_result", {})
            )
            
            return ImageEditResponse(
                status=ResponseStatus.SUCCESS,
                message=f"图片编辑成功，生成 {result.get('total_generated', 0)} 张图片，已保存 {result.get('total_saved', 0)} 张",
                data=edit_result.dict()
            )
        else:
            error_msg = result.get("error", "未知错误")
            logger.error(f"图片编辑失败: {error_msg}")
            return ImageEditResponse(
                status=ResponseStatus.ERROR,
                message=f"图片编辑失败: {error_msg}",
                data=result
            )
            
    except Exception as e:
        logger.error(f"图片编辑异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"图片编辑处理异常: {str(e)}"
        )


@router.post(
    "/confirm",
    summary="确认编辑并执行",
    description="""
    二次确认接口，用于在Agent对话中确认用户意图后再执行编辑操作。
    
    使用场景：
    1. Agent识别到用户想要编辑图片
    2. Agent先返回确认信息
    3. 用户确认后调用此接口执行编辑
    """
)
async def confirm_and_edit(
    request: ConfirmEditRequest,
    storage_svc: StorageService = Depends(get_storage_service),
    edit_svc: ImageEditService = Depends(get_image_edit_service)
):
    """
    确认并执行编辑
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not request.confirmed:
        return BaseResponse(
            status=ResponseStatus.SUCCESS,
            message="已取消编辑操作"
        )
    
    # 构建编辑请求
    edit_request = ImageEditRequest(
        image_id=request.image_id,
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        prompt_extend=request.prompt_extend,
        n=request.n,
        size=request.size,
        watermark=request.watermark,
        seed=request.seed,
        style_tag=request.style_tag
    )
    
    # 调用编辑接口
    return await edit_image(edit_request, storage_svc, edit_svc)


@router.get(
    "/styles",
    summary="获取支持的编辑风格列表",
    description="""
    返回系统支持的图片编辑风格列表，供用户选择
    """
)
async def get_supported_styles():
    """
    获取支持的编辑风格列表
    """
    styles = [
        {
            "id": "anime",
            "name": "动漫风格",
            "description": "将图片转换为日式动漫风格",
            "prompt_template": "将图片转换为动漫风格",
            "example": "将图片转换为动漫风格"
        },
        {
            "id": "cartoon",
            "name": "卡通风格",
            "description": "将图片转换为卡通插画风格",
            "prompt_template": "将图片转换为卡通风格",
            "example": "将图片转换为卡通风格"
        },
        {
            "id": "oil_painting",
            "name": "油画风格",
            "description": "将图片转换为油画艺术风格",
            "prompt_template": "将图片转换为油画风格",
            "example": "将图片转换为油画风格"
        },
        {
            "id": "watercolor",
            "name": "水彩风格",
            "description": "将图片转换为水彩画风格",
            "prompt_template": "将图片转换为水彩画风格",
            "example": "将图片转换为水彩画风格"
        },
        {
            "id": "sketch",
            "name": "素描风格",
            "description": "将图片转换为铅笔素描风格",
            "prompt_template": "将图片转换为素描风格",
            "example": "将图片转换为素描风格"
        },
        {
            "id": "cyberpunk",
            "name": "赛博朋克风格",
            "description": "将图片转换为赛博朋克科幻风格",
            "prompt_template": "将图片转换为赛博朋克风格",
            "example": "将图片转换为赛博朋克风格"
        },
        {
            "id": "retro",
            "name": "复古风格",
            "description": "将图片转换为复古胶片风格",
            "prompt_template": "将图片转换为复古风格",
            "example": "将图片转换为复古风格"
        },
        {
            "id": "cinematic",
            "name": "电影风格",
            "description": "将图片转换为电影画面风格",
            "prompt_template": "将图片转换为电影风格",
            "example": "将图片转换为电影风格"
        }
    ]
    
    return BaseResponse(
        status=ResponseStatus.SUCCESS,
        message="获取风格列表成功",
        data={"styles": styles}
    )


@router.get(
    "/status",
    summary="获取图片编辑服务状态",
    description="""
    返回图片编辑服务的状态信息
    """
)
async def get_service_status(
    edit_svc: ImageEditService = Depends(get_image_edit_service)
):
    """
    获取图片编辑服务状态
    """
    return BaseResponse(
        status=ResponseStatus.SUCCESS,
        data={
            "initialized": edit_svc.is_initialized,
            "model_name": edit_svc._model_name,
            "base_url": edit_svc._base_url,
            "api_key_configured": edit_svc._api_key is not None
        }
    )
