from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ..services import get_knowledge_qa_service

router = APIRouter(
    prefix="/knowledge-qa",
    tags=["Knowledge QA"]
)


class KnowledgeQARequest(BaseModel):
    image_uuid: str
    question: str
    context: Optional[str] = None


@router.post("/qa")
async def knowledge_qa(request: KnowledgeQARequest) -> Dict[str, Any]:
    """基于图片的知识问答"""
    knowledge_qa_service = get_knowledge_qa_service()
    result = knowledge_qa_service.knowledge_qa(
        image_uuid=request.image_uuid,
        question=request.question,
        context=request.context
    )

    if result["status"] == "error":
        if "不存在" in result["message"]:
            raise HTTPException(status_code=404, detail=result["message"])
        raise HTTPException(status_code=500, detail=result["message"])

    return result
