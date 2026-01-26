"""
智能图像检索API路由
提供基于语义的图像搜索接口
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form

from ..models import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchType,
    ResponseStatus,
    ImageMetadata,
)
from ..services import get_search_service, SearchService

router = APIRouter(prefix="/search", tags=["Search"])


def get_service():
    """获取搜索服务依赖"""
    search_svc = get_search_service()

    if not search_svc.is_initialized:
        raise HTTPException(status_code=503, detail="搜索服务未初始化")

    return search_svc


@router.post(
    "/",
    response_model=SearchResponse,
    summary="统一搜索接口",
    description="""
    智能图像搜索，支持多种查询方式：
    - **纯文本搜索**: 使用自然语言描述查找匹配的图片
    - **图片搜索**: 以图搜图，查找相似图片
    - **图文混合搜索**: 结合文本描述和参考图片进行搜索
    
    系统会自动识别查询类型并执行相应的检索策略。
    """
)
async def search(
    request: SearchRequest,
    search_svc: SearchService = Depends(get_service)
):
    """
    执行智能图像搜索

    - **query_text**: 文本查询（可选）
    - **query_image_id**: 查询图片的ID（可选）
    - **query_image_url**: 查询图片的URL或路径（可选）
    - **instruction**: 自定义查询指令（可选）
    - **top_k**: 返回结果数量，默认10
    - **score_threshold**: 相似度阈值（可选）
    - **filter_tags**: 标签过滤（可选）
    """
    result = search_svc.search(
        query_text=request.query_text,
        query_image_id=request.query_image_id,
        query_image_url=request.query_image_url,
        instruction=request.instruction,
        top_k=request.top_k,
        score_threshold=request.score_threshold,
        filter_tags=request.filter_tags
    )

    # 转换结果
    search_results = [
        SearchResult(
            id=r["id"],
            score=r["score"],
            metadata=ImageMetadata(
                **r["metadata"]) if r.get("metadata") else None,
            preview_url=r.get("preview_url")
        )
        for r in result["results"]
    ]

    return SearchResponse(
        status=ResponseStatus.SUCCESS,
        message="搜索完成",
        data=search_results,
        query_type=SearchType(result["query_type"]),
        total=result["total"]
    )


@router.get(
    "/text",
    response_model=SearchResponse,
    summary="文本语义搜索",
    description="使用自然语言描述搜索图片，如「日落时的海滩」「穿红色衣服的人」"
)
async def search_by_text(
    query: str = Query(..., description="搜索文本"),
    instruction: Optional[str] = Query(None, description="自定义指令"),
    top_k: int = Query(10, ge=1, le=100, description="返回数量"),
    score_threshold: Optional[float] = Query(
        None, ge=0, le=1, description="相似度阈值"),
    tags: Optional[List[str]] = Query(None, description="标签过滤"),
    search_svc: SearchService = Depends(get_service)
):
    """文本语义搜索"""
    results = search_svc.search_by_text(
        query_text=query,
        instruction=instruction,
        top_k=top_k,
        score_threshold=score_threshold,
        filter_tags=tags
    )

    search_results = [
        SearchResult(
            id=r["id"],
            score=r["score"],
            metadata=ImageMetadata(
                **r["metadata"]) if r.get("metadata") else None,
            preview_url=r.get("preview_url")
        )
        for r in results
    ]

    return SearchResponse(
        status=ResponseStatus.SUCCESS,
        message="文本搜索完成",
        data=search_results,
        query_type=SearchType.TEXT,
        total=len(search_results)
    )


@router.get(
    "/image/{image_id}",
    response_model=SearchResponse,
    summary="以图搜图",
    description="根据指定图片ID搜索相似图片"
)
async def search_by_image_id(
    image_id: str,
    instruction: Optional[str] = Query(None, description="自定义指令"),
    top_k: int = Query(10, ge=1, le=100, description="返回数量"),
    score_threshold: Optional[float] = Query(
        None, ge=0, le=1, description="相似度阈值"),
    tags: Optional[List[str]] = Query(None, description="标签过滤"),
    search_svc: SearchService = Depends(get_service)
):
    """根据图片ID搜索相似图片"""
    results = search_svc.search_by_image_id(
        image_id=image_id,
        instruction=instruction,
        top_k=top_k,
        score_threshold=score_threshold,
        filter_tags=tags
    )

    search_results = [
        SearchResult(
            id=r["id"],
            score=r["score"],
            metadata=ImageMetadata(
                **r["metadata"]) if r.get("metadata") else None,
            preview_url=r.get("preview_url")
        )
        for r in results
    ]

    return SearchResponse(
        status=ResponseStatus.SUCCESS,
        message="图片搜索完成",
        data=search_results,
        query_type=SearchType.IMAGE,
        total=len(search_results)
    )


@router.post(
    "/image",
    response_model=SearchResponse,
    summary="上传图片搜索",
    description="上传图片进行以图搜图"
)
async def search_by_uploaded_image(
    file: UploadFile = File(..., description="上传的查询图片"),
    instruction: Optional[str] = Form(None, description="自定义指令"),
    top_k: int = Form(10, ge=1, le=100, description="返回数量"),
    score_threshold: Optional[float] = Form(
        None, ge=0, le=1, description="相似度阈值"),
    tags: Optional[List[str]] = Form(None, description="标签过滤"),
    search_svc: SearchService = Depends(get_service)
):
    """上传图片进行搜索"""
    import logging
    from PIL import Image
    import io

    logger = logging.getLogger(__name__)

    logger.info(
        f"接收到以图搜图请求: filename={file.filename}, "
        f"top_k={top_k}, score_threshold={score_threshold}, tags={tags}"
    )

    # 读取上传的图片
    content = await file.read()
    image = Image.open(io.BytesIO(content))

    logger.info(f"图片读取成功: size={image.size}, mode={image.mode}")

    results = search_svc.search_by_image(
        image=image,
        instruction=instruction,
        top_k=top_k,
        score_threshold=score_threshold,
        filter_tags=tags
    )

    logger.info(f"搜索服务返回 {len(results)} 条结果")

    search_results = [
        SearchResult(
            id=r["id"],
            score=r["score"],
            metadata=ImageMetadata(
                **r["metadata"]) if r.get("metadata") else None,
            preview_url=r.get("preview_url")
        )
        for r in results
    ]

    # 记录返回结果的相似度范围
    if search_results:
        scores = [r.score for r in search_results if r.score is not None]
        if scores:
            logger.info(
                f"返回结果统计: count={len(search_results)}, "
                f"min_score={min(scores):.4f}, max_score={max(scores):.4f}, "
                f"avg_score={sum(scores)/len(scores):.4f}"
            )

    return SearchResponse(
        status=ResponseStatus.SUCCESS,
        message="图片搜索完成",
        data=search_results,
        query_type=SearchType.IMAGE,
        total=len(search_results)
    )


@router.post(
    "/hybrid",
    response_model=SearchResponse,
    summary="图文混合搜索",
    description="同时使用文本描述和图片进行搜索，获得更精确的结果"
)
async def search_hybrid(
    query_text: str = Query(..., description="文本描述"),
    image_id: Optional[str] = Query(None, description="参考图片ID"),
    image_url: Optional[str] = Query(None, description="参考图片URL"),
    instruction: Optional[str] = Query(None, description="自定义指令"),
    top_k: int = Query(10, ge=1, le=100, description="返回数量"),
    score_threshold: Optional[float] = Query(
        None, ge=0, le=1, description="相似度阈值"),
    tags: Optional[List[str]] = Query(None, description="标签过滤"),
    search_svc: SearchService = Depends(get_service)
):
    """图文混合搜索"""
    # 确定图片
    from ..services import get_storage_service
    storage_svc = get_storage_service()

    image_path = None
    if image_id:
        path = storage_svc.get_image_path(image_id)
        if path:
            image_path = str(path)
        else:
            raise HTTPException(status_code=404, detail=f"图片不存在: {image_id}")
    elif image_url:
        image_path = image_url
    else:
        raise HTTPException(status_code=400, detail="必须提供image_id或image_url")

    results = search_svc.search_hybrid(
        query_text=query_text,
        image=image_path,
        instruction=instruction,
        top_k=top_k,
        score_threshold=score_threshold,
        filter_tags=tags
    )

    search_results = [
        SearchResult(
            id=r["id"],
            score=r["score"],
            metadata=ImageMetadata(
                **r["metadata"]) if r.get("metadata") else None,
            preview_url=r.get("preview_url")
        )
        for r in results
    ]

    return SearchResponse(
        status=ResponseStatus.SUCCESS,
        message="混合搜索完成",
        data=search_results,
        query_type=SearchType.HYBRID,
        total=len(search_results)
    )


@router.get(
    "/meta",
    summary="元数据搜索",
    description="按元数据检索图片，支持日期、标签等元数据过滤"
)
async def search_by_meta(
    date_text: Optional[str] = Query(None, description="日期文本，支持格式：1.18 / 1月18日 / 2026-01-18"),
    tags: Optional[str] = Query(None, description="标签过滤，逗号分隔的字符串，例如 'cat,outdoor'"),
    top_k: int = Query(10, ge=1, le=100, description="返回数量"),
    search_svc: SearchService = Depends(get_service)
):
    """按元数据搜索图片"""
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    
    results = search_svc.search_by_meta(
        date_text=date_text,
        tags=tags_list,
        top_k=top_k
    )

    search_results = [
        SearchResult(
            id=r["id"],
            score=r.get("score"),
            metadata=ImageMetadata(
                **r["metadata"]) if r.get("metadata") else None,
            preview_url=r.get("preview_url")
        )
        for r in results
    ]

    return SearchResponse(
        status=ResponseStatus.SUCCESS,
        message="元数据搜索完成",
        data=search_results,
        query_type=SearchType.TEXT,
        total=len(search_results)
    )


@router.get(
    "/meta/hybrid",
    summary="元数据+语义组合搜索",
    description="结合元数据过滤和语义相似度进行组合检索"
)
async def search_by_meta_with_text(
    query: str = Query(..., description="语义查询描述"),
    date_text: Optional[str] = Query(None, description="日期文本，支持格式：1.18 / 1月18日 / 2026-01-18"),
    tags: Optional[str] = Query(None, description="标签过滤，逗号分隔的字符串，例如 'cat,outdoor'"),
    top_k: int = Query(10, ge=1, le=100, description="返回数量"),
    score_threshold: Optional[float] = Query(
        None, ge=0, le=1, description="相似度阈值"),
    instruction: Optional[str] = Query(None, description="自定义指令"),
    search_svc: SearchService = Depends(get_service)
):
    """元数据+语义组合搜索"""
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    
    results = search_svc.search_by_text_with_meta(
        query_text=query,
        date_text=date_text,
        tags=tags_list,
        top_k=top_k,
        score_threshold=score_threshold,
        instruction=instruction
    )

    search_results = [
        SearchResult(
            id=r["id"],
            score=r.get("score"),
            metadata=ImageMetadata(
                **r["metadata"]) if r.get("metadata") else None,
            preview_url=r.get("preview_url")
        )
        for r in results
    ]

    return SearchResponse(
        status=ResponseStatus.SUCCESS,
        message="组合搜索完成",
        data=search_results,
        query_type=SearchType.HYBRID,
        total=len(search_results)
    )
