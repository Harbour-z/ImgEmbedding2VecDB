"""
Pydantic数据模型定义
"""

from datetime import datetime
from typing import Optional, List, Any, Dict, Union
from pydantic import BaseModel, Field
from enum import Enum


# ==================== 通用响应模型 ====================

class ResponseStatus(str, Enum):
    """响应状态枚举"""
    SUCCESS = "success"
    ERROR = "error"


class BaseResponse(BaseModel):
    """基础响应模型"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    message: str = "操作成功"
    data: Optional[Any] = None


# ==================== Embedding相关模型 ====================

class EmbeddingInput(BaseModel):
    """单个Embedding输入"""
    text: Optional[str] = Field(None, description="文本内容")
    image_id: Optional[str] = Field(None, description="图片ID（存储系统中的ID）")
    image_url: Optional[str] = Field(None, description="图片URL或本地路径")
    instruction: Optional[str] = Field(None, description="指令提示词")

    class Config:
        json_schema_extra = {
            "examples": [
                {"text": "一只可爱的猫咪"},
                {"image_id": "img_001"},
                {"text": "描述这张图片", "image_id": "img_001"}
            ]
        }


class EmbeddingRequest(BaseModel):
    """Embedding请求模型"""
    inputs: List[EmbeddingInput] = Field(..., description="输入列表，支持批量处理")
    normalize: bool = Field(True, description="是否对向量进行L2归一化")


class EmbeddingResult(BaseModel):
    """单个Embedding结果"""
    index: int = Field(..., description="输入索引")
    embedding: List[float] = Field(..., description="向量表示")
    dimension: int = Field(..., description="向量维度")


class EmbeddingResponse(BaseResponse):
    """Embedding响应模型"""
    data: Optional[List[EmbeddingResult]] = None


# ==================== 向量数据库相关模型 ====================

class ImageMetadata(BaseModel):
    """图片元数据"""
    filename: str = Field(..., description="文件名")
    file_path: str = Field(..., description="存储路径")
    file_size: Optional[int] = Field(None, description="文件大小(bytes)")
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")
    format: Optional[str] = Field(None, description="图片格式")
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    description: Optional[str] = Field(None, description="图片描述")
    extra: Dict[str, Any] = Field(default_factory=dict, description="扩展字段")


class VectorRecord(BaseModel):
    """向量记录模型"""
    id: str = Field(..., description="唯一标识符")
    vector: List[float] = Field(..., description="向量数据")
    metadata: ImageMetadata = Field(..., description="元数据")


class VectorUpsertRequest(BaseModel):
    """向量插入/更新请求"""
    id: str = Field(..., description="唯一标识符")
    vector: Optional[List[float]] = Field(
        None, description="向量数据（可选，不提供则自动生成）")
    metadata: ImageMetadata = Field(..., description="元数据")


class VectorBatchUpsertRequest(BaseModel):
    """批量向量插入/更新请求"""
    records: List[VectorUpsertRequest] = Field(..., description="记录列表")


class VectorUpdateMetadataRequest(BaseModel):
    """更新元数据请求"""
    tags: Optional[List[str]] = Field(None, description="标签列表")
    description: Optional[str] = Field(None, description="图片描述")
    extra: Optional[Dict[str, Any]] = Field(None, description="扩展字段")


class VectorQueryResult(BaseModel):
    """向量查询结果"""
    id: str = Field(..., description="记录ID")
    score: float = Field(..., description="相似度分数")
    metadata: ImageMetadata = Field(..., description="元数据")


class VectorSearchResponse(BaseResponse):
    """向量搜索响应"""
    data: Optional[List[VectorQueryResult]] = None
    total: int = Field(0, description="结果总数")


# ==================== 搜索相关模型 ====================

class SearchType(str, Enum):
    """搜索类型"""
    TEXT = "text"
    IMAGE = "image"
    HYBRID = "hybrid"


class SearchRequest(BaseModel):
    """搜索请求模型"""
    query_text: Optional[str] = Field(None, description="文本查询")
    query_image_id: Optional[str] = Field(None, description="图片ID查询")
    query_image_url: Optional[str] = Field(None, description="图片URL查询")
    instruction: Optional[str] = Field(None, description="查询指令")
    top_k: int = Field(10, ge=1, le=100, description="返回结果数量")
    score_threshold: Optional[float] = Field(
        None, ge=0, le=1, description="相似度阈值")
    filter_tags: Optional[List[str]] = Field(None, description="标签过滤")


class SearchResult(BaseModel):
    """搜索结果"""
    id: str = Field(..., description="图片ID")
    score: float = Field(..., description="相似度分数")
    metadata: ImageMetadata = Field(..., description="图片元数据")
    preview_url: Optional[str] = Field(None, description="预览URL")


class SearchResponse(BaseResponse):
    """搜索响应"""
    data: Optional[List[SearchResult]] = None
    query_type: SearchType = Field(..., description="查询类型")
    total: int = Field(0, description="结果总数")


# ==================== 图片存储相关模型 ====================

class ImageUploadResponse(BaseResponse):
    """图片上传响应"""
    data: Optional[Dict[str, Any]] = None


class ImageInfo(BaseModel):
    """图片信息"""
    id: str = Field(..., description="图片ID")
    filename: str = Field(..., description="文件名")
    file_path: str = Field(..., description="存储路径")
    file_size: int = Field(..., description="文件大小")
    width: int = Field(..., description="宽度")
    height: int = Field(..., description="高度")
    format: str = Field(..., description="格式")
    created_at: datetime = Field(..., description="上传时间")
    url: str = Field(..., description="访问URL")


class ImageListResponse(BaseResponse):
    """图片列表响应"""
    data: Optional[List[ImageInfo]] = None
    total: int = Field(0, description="总数")
    page: int = Field(1, description="当前页")
    page_size: int = Field(20, description="每页数量")


# ==================== Agent接口相关模型（预留）====================

class AgentAction(str, Enum):
    """Agent动作类型"""
    SEARCH = "search"
    UPLOAD = "upload"
    DELETE = "delete"
    UPDATE = "update"
    ANALYZE = "analyze"


class AgentRequest(BaseModel):
    """Agent请求模型（预留）"""
    action: AgentAction = Field(..., description="动作类型")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="动作参数")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class AgentResponse(BaseResponse):
    """Agent响应模型（预留）"""
    action: AgentAction = Field(..., description="执行的动作")
    result: Optional[Any] = None
    suggestions: Optional[List[str]] = Field(None, description="后续建议动作")


# ==================== 系统状态模型 ====================

class SystemStatus(BaseModel):
    """系统状态"""
    status: str = Field(..., description="系统状态")
    version: str = Field(..., description="版本号")
    model_loaded: bool = Field(..., description="模型是否加载")
    vector_db_connected: bool = Field(..., description="向量数据库是否连接")
    storage_available: bool = Field(..., description="存储是否可用")
    total_images: int = Field(0, description="图片总数")
    total_vectors: int = Field(0, description="向量总数")


# ==================== 图片推荐模型 ====================

class ImageRecommendation(BaseModel):
    """图片推荐结果"""
    recommended_image_id: Optional[str] = Field(None, description="推荐的最佳图片ID")
    alternative_image_ids: List[str] = Field(default_factory=list, description="其他未被推荐的图片ID列表")
    recommendation_reason: str = Field(..., description="推荐理由文本")
    user_prompt_for_deletion: bool = Field(False, description="是否提示用户删除其他图片")
    total_images_analyzed: int = Field(0, description="分析的图片总数")


# ==================== 删除确认模型 ====================

class DeleteConfirmationRequest(BaseModel):
    """删除确认请求"""
    image_ids: List[str] = Field(..., description="要删除的图片ID列表")
    confirmed: bool = Field(True, description="用户是否确认删除")
    reason: Optional[str] = Field(None, description="删除原因")


class DeleteConfirmationResponse(BaseModel):
    """删除确认响应"""
    deleted_count: int = Field(0, description="已删除的图片数量")
    failed_count: int = Field(0, description="删除失败的图片数量")
    deleted_image_ids: List[str] = Field(default_factory=list, description="成功删除的图片ID列表")
    failed_image_ids: List[str] = Field(default_factory=list, description="删除失败的图片ID列表")


# ==================== 图片编辑模型 ====================

class ImageEditRequest(BaseModel):
    """图片编辑请求模型"""
    image_id: str = Field(..., description="源图片ID")
    prompt: str = Field(..., description="编辑提示词，例如：'将图片转换为动漫风格'")
    negative_prompt: str = Field(" ", description="反向提示词，描述不希望出现的内容")
    prompt_extend: bool = Field(True, description="是否开启智能提示词改写（默认为 True）")
    n: int = Field(1, ge=1, le=6, description="生成图片数量（1-6）")
    size: Optional[str] = Field(None, description="输出图片分辨率，格式为 '宽*高'，例如 '1024*1536'")
    watermark: bool = Field(False, description="是否添加水印")
    seed: Optional[int] = Field(None, description="随机数种子")
    style_tag: Optional[str] = Field(None, description="风格标签，用于元数据记录，例如：'anime', 'cartoon'")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "image_id": "img-uuid-1234",
                    "prompt": "将图片转换为动漫风格",
                    "negative_prompt": "模糊，多余的手指",
                    "prompt_extend": True,
                    "n": 2,
                    "style_tag": "anime"
                }
            ]
        }


class EditedImageInfo(BaseModel):
    """编辑后的图片信息"""
    image_id: str = Field(..., description="图片ID")
    url: str = Field(..., description="访问URL")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据信息")


class ImageEditResponse(BaseResponse):
    """图片编辑响应模型"""
    data: Optional[Dict[str, Any]] = None


class ImageEditResult(BaseModel):
    """图片编辑结果详情"""
    success: bool = Field(..., description="操作是否成功")
    saved_images: List[EditedImageInfo] = Field(default_factory=list, description="保存的图片列表")
    total_generated: int = Field(0, description="生成的图片总数")
    total_saved: int = Field(0, description="成功保存的图片数量")
    edit_result: Dict[str, Any] = Field(default_factory=dict, description="原始编辑结果")
