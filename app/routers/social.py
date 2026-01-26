from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from ..services.social_service import social_service

router = APIRouter(
    prefix="/social",
    tags=["Social Media"]
)

class CaptionRequest(BaseModel):
    image_uuid: str
    style: str = "简洁"
    purpose: str = "生活分享"

@router.post("/caption")
async def generate_caption(request: CaptionRequest) -> Dict[str, Any]:
    """生成社交媒体文案"""
    result = social_service.generate_caption(
        image_uuid=request.image_uuid,
        style=request.style,
        purpose=request.purpose
    )
    
    if result["status"] == "error":
        # 如果是图片不存在等错误，可能返回404或400更合适，这里简单起见统一处理
        # 实际生产中可以根据message内容细分
        if "不存在" in result["message"]:
             raise HTTPException(status_code=404, detail=result["message"])
        raise HTTPException(status_code=500, detail=result["message"])
        
    return result
