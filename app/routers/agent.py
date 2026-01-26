"""
AI Agent框架集成预留接口
为openjiuwen等AI Agent框架提供标准化的服务调用入口
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks
from pydantic import BaseModel, Field

from ..models import (
    AgentAction,
    AgentRequest,
    AgentResponse,
    ResponseStatus,
    BaseResponse,
    SearchRequest,
    ImageRecommendation,
    DeleteConfirmationRequest,
    DeleteConfirmationResponse,
)
from ..services import (
    get_search_service,
    SearchService,
    get_storage_service,
    StorageService,
    get_vector_db_service,
    VectorDBService,
    get_embedding_service,
    EmbeddingService,
    get_agent_service,
    AgentService,
    get_image_recommendation_service,
    ImageRecommendationService,
)

router = APIRouter(prefix="/agent", tags=["Agent Integration"])


class AgentInterface:
    """
    Agent接口类
    为AI Agent框架提供标准化的服务调用方法

    设计原则：
    1. 统一的输入输出格式，便于Agent理解和调用
    2. 清晰的动作语义，便于LLM进行决策
    3. 丰富的上下文信息，支持多轮对话
    4. 可扩展的动作类型，便于后续功能扩展
    """

    def __init__(
        self,
        search_service: SearchService,
        storage_service: StorageService,
        vector_db_service: VectorDBService,
        embedding_service: EmbeddingService,
        image_recommendation_service: ImageRecommendationService
    ):
        self.search_service = search_service
        self.storage_service = storage_service
        self.vector_db_service = vector_db_service
        self.embedding_service = embedding_service
        self.image_recommendation_service = image_recommendation_service

    def get_available_actions(self) -> List[Dict[str, Any]]:
        """
        获取可用的动作列表
        供Agent了解可以执行的操作
        """
        return [
            {
                "action": "search",
                "description": "搜索图片，支持文本描述、图片相似度、图文混合搜索",
                "parameters": {
                    "query_text": {"type": "string", "description": "文本查询", "required": False},
                    "query_image_id": {"type": "string", "description": "图片ID查询", "required": False},
                    "top_k": {"type": "integer", "description": "返回数量", "default": 10},
                    "filter_tags": {"type": "array", "description": "标签过滤", "required": False}
                },
                "examples": [
                    {"query_text": "日落时的海滩", "top_k": 5},
                    {"query_image_id": "img_abc123", "top_k": 10}
                ]
            },
            {
                "action": "upload",
                "description": "上传新图片到相册",
                "parameters": {
                    "image_url": {"type": "string", "description": "图片URL", "required": True},
                    "tags": {"type": "array", "description": "标签列表", "required": False},
                    "description": {"type": "string", "description": "图片描述", "required": False}
                }
            },
            {
                "action": "delete",
                "description": "删除指定图片",
                "parameters": {
                    "image_id": {"type": "string", "description": "图片ID", "required": True}
                }
            },
            {
                "action": "update",
                "description": "更新图片信息",
                "parameters": {
                    "image_id": {"type": "string", "description": "图片ID", "required": True},
                    "tags": {"type": "array", "description": "新标签", "required": False},
                    "description": {"type": "string", "description": "新描述", "required": False}
                }
            },
            {
                "action": "analyze",
                "description": "分析图片内容，使用qwen3-vl-plus多模态模型进行深度分析，从构图美学、色彩搭配、光影运用、主题表达、情感传达、创意独特性、故事性等维度进行评估",
                "parameters": {
                    "image_id": {"type": "string", "description": "图片ID", "required": True}
                }
            }
        ]

    async def execute_action(
        self,
        action: AgentAction,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行Agent动作

        Args:
            action: 动作类型
            parameters: 动作参数
            context: 上下文信息（如对话历史、用户偏好等）

        Returns:
            执行结果
        """
        if action == AgentAction.SEARCH:
            return self._execute_search(parameters)
        elif action == AgentAction.UPLOAD:
            return self._execute_upload(parameters)
        elif action == AgentAction.DELETE:
            return self._execute_delete(parameters)
        elif action == AgentAction.UPDATE:
            return self._execute_update(parameters)
        elif action == AgentAction.ANALYZE:
            return await self._execute_analyze(parameters)
        else:
            raise ValueError(f"不支持的动作类型: {action}")

    def _execute_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行搜索动作"""
        if not self.search_service.is_initialized:
            raise RuntimeError("搜索服务未初始化")

        result = self.search_service.search(
            query_text=params.get("query_text"),
            query_image_id=params.get("query_image_id"),
            query_image_url=params.get("query_image_url"),
            top_k=params.get("top_k", 10),
            filter_tags=params.get("filter_tags")
        )

        return {
            "success": True,
            "action": "search",
            "result": result,
            "message": f"找到 {result['total']} 张相关图片"
        }

    def _execute_upload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行上传动作（预留，需要实现URL下载）"""
        # 预留：从URL下载并保存图片
        return {
            "success": False,
            "action": "upload",
            "message": "URL上传功能暂未实现，请使用/storage/upload接口"
        }

    def _execute_delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行删除动作"""
        image_id = params.get("image_id")
        if not image_id:
            raise ValueError("必须提供image_id")

        # 删除文件
        file_deleted = self.storage_service.delete_image(image_id)

        # 删除向量
        vector_deleted = False
        if self.vector_db_service.is_initialized:
            vector_deleted = self.vector_db_service.delete(image_id)

        return {
            "success": file_deleted,
            "action": "delete",
            "result": {
                "file_deleted": file_deleted,
                "vector_deleted": vector_deleted
            },
            "message": "图片已删除" if file_deleted else "图片不存在"
        }

    def _execute_update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行更新动作"""
        image_id = params.get("image_id")
        if not image_id:
            raise ValueError("必须提供image_id")

        update_data = {}
        if "tags" in params:
            update_data["tags"] = params["tags"]
        if "description" in params:
            update_data["description"] = params["description"]

        if not update_data:
            return {
                "success": False,
                "action": "update",
                "message": "未提供任何更新内容"
            }

        success = self.vector_db_service.update_metadata(image_id, update_data)

        return {
            "success": success,
            "action": "update",
            "message": "更新成功" if success else "更新失败"
        }

    def _execute_analyze(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行分析动作"""
        if not self.image_recommendation_service.is_initialized:
            raise RuntimeError("图片推荐服务未初始化")
            
        image_id = params.get("image_id")
        if not image_id:
            raise ValueError("必须提供image_id")
        
        # 从存储服务获取图片数据
        image_path = self.storage_service.get_image_path(image_id)
        if not image_path:
            raise ValueError(f"图片不存在: {image_id}")
        
        # 读取图片数据
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
        except Exception as e:
            raise RuntimeError(f"无法读取图片 {image_id}: {e}")
        
        # 使用图片推荐服务进行分析
        try:
            import asyncio
            result = asyncio.run(self.image_recommendation_service.recommend_images(
                images=[image_data],
                image_ids=[image_id],
                user_preference=""
            ))
            
            if result.get("success"):
                analysis = result.get("data", {}).get("analysis", {})
                image_key = list(analysis.keys())[0] if analysis else image_id
                image_analysis = analysis.get(image_key, {})
                
                return {
                    "success": True,
                    "action": "analyze",
                    "result": {
                        "image_id": image_id,
                        "analysis": image_analysis,
                        "model_used": result.get("data", {}).get("model_used", "unknown")
                    },
                    "message": f"图片 {image_id} 分析完成"
                }
            else:
                return {
                    "success": False,
                    "action": "analyze",
                    "message": result.get("error", "图片分析失败")
                }
        except Exception as e:
            logger.error(f"图片分析失败: {e}", exc_info=True)
            return {
                "success": False,
                "action": "analyze",
                "message": f"图片分析失败: {str(e)}"
            }

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态，供Agent了解当前系统能力"""
        return {
            "embedding_service": self.embedding_service.is_initialized if self.embedding_service else False,
            "search_service": self.search_service.is_initialized if self.search_service else False,
            "storage_service": self.storage_service.is_initialized if self.storage_service else False,
            "vector_db_service": self.vector_db_service.is_initialized if self.vector_db_service else False,
            "total_images": self.storage_service.get_storage_stats()["total_images"] if self.storage_service.is_initialized else 0,
            "total_vectors": self.vector_db_service.count() if self.vector_db_service.is_initialized else 0
        }


# 全局Agent接口实例
_agent_interface: Optional[AgentInterface] = None


def get_agent_interface() -> AgentInterface:
    """获取Agent接口实例"""
    global _agent_interface

    if _agent_interface is None:
        _agent_interface = AgentInterface(
            search_service=get_search_service(),
            storage_service=get_storage_service(),
            vector_db_service=get_vector_db_service(),
            embedding_service=get_embedding_service(),
            image_recommendation_service=get_image_recommendation_service()
        )

    return _agent_interface


# ==================== API路由 ====================

@router.get(
    "/actions",
    summary="获取可用动作列表",
    description="返回Agent可以执行的所有动作及其参数说明"
)
async def get_available_actions():
    """获取Agent可用动作列表"""
    agent = get_agent_interface()

    return {
        "status": "success",
        "actions": agent.get_available_actions()
    }


@router.post(
    "/execute",
    response_model=AgentResponse,
    summary="执行Agent动作",
    description="""
    统一的Agent动作执行接口，支持：
    - search: 搜索图片
    - upload: 上传图片（预留）
    - delete: 删除图片
    - update: 更新图片信息
    - analyze: 分析图片内容，使用qwen3-vl-plus多模态模型进行深度分析
    """
)
async def execute_agent_action(request: AgentRequest):
    """执行Agent动作"""
    agent = get_agent_interface()

    result = await agent.execute_action(
        action=request.action,
        parameters=request.parameters,
        context=request.context
    )

    # 生成后续建议
    suggestions = _generate_suggestions(request.action, result)

    return AgentResponse(
        status=ResponseStatus.SUCCESS if result.get(
            "success") else ResponseStatus.ERROR,
        message=result.get("message", ""),
        action=request.action,
        result=result.get("result"),
        suggestions=suggestions
    )


@router.get(
    "/status",
    summary="获取系统状态",
    description="返回当前系统各服务的状态信息"
)
async def get_system_status():
    """获取系统状态"""
    agent = get_agent_interface()

    return {
        "status": "success",
        "system": agent.get_system_status()
    }


@router.get(
    "/schema",
    summary="获取API Schema",
    description="返回Agent调用所需的完整API Schema定义（OpenAPI格式）"
)
async def get_api_schema():
    """
    获取API Schema
    供openjiuwen等框架生成工具调用
    """
    return {
        "status": "success",
        "schema": {
            "name": "smart_album_api",
            "description": "智慧相册后端API，支持语义化图片检索",
            "version": "1.0.0",
            "base_url": "/api/v1/agent",
            "endpoints": [
                {
                    "path": "/execute",
                    "method": "POST",
                    "description": "执行Agent动作",
                    "request_body": {
                        "action": "string (search|upload|delete|update|analyze)",
                        "parameters": "object",
                        "context": "object (optional)"
                    }
                },
                {
                    "path": "/actions",
                    "method": "GET",
                    "description": "获取可用动作列表"
                },
                {
                    "path": "/status",
                    "method": "GET",
                    "description": "获取系统状态"
                }
            ]
        }
    }


def _generate_suggestions(action: AgentAction, result: Dict[str, Any]) -> List[str]:
    """根据动作结果生成后续建议"""
    suggestions = []

    if action == AgentAction.SEARCH:
        if result.get("success"):
            total = result.get("result", {}).get("total", 0)
            if total == 0:
                suggestions.append("尝试使用不同的关键词搜索")
                suggestions.append("检查是否有相关标签可以过滤")
            elif total > 10:
                suggestions.append("可以添加更具体的描述来缩小搜索范围")
                suggestions.append("尝试使用标签过滤来精确结果")

    elif action == AgentAction.DELETE:
        if result.get("success"):
            suggestions.append("删除操作已完成，相关数据已清理")

    elif action == AgentAction.UPDATE:
        if result.get("success"):
            suggestions.append("更新成功，可以搜索验证更新效果")

    return suggestions


# ==================== 聊天接口 ====================

class ChatMessage(BaseModel):
    """聊天消息模型"""
    query: str = Field(..., description="用户输入的自然语言查询")
    session_id: Optional[str] = Field(None, description="会话ID，用于多轮对话")
    top_k: int = Field(10, description="返回结果数量", ge=1, le=50)
    score_threshold: Optional[float] = Field(
        None, description="相似度阈值", ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    """聊天响应模型"""
    session_id: str = Field(..., description="会话ID")
    answer: str = Field(..., description="自然语言回复")
    intent: str = Field(..., description="识别的用户意图")
    optimized_query: str = Field(..., description="优化后的查询")
    results: Optional[Dict[str, Any]] = Field(None, description="搜索结果")
    suggestions: List[str] = Field(default_factory=list, description="后续建议")
    recommendation: Optional[ImageRecommendation] = Field(None, description="图片推荐信息")
    pointcloud_id: Optional[str] = Field(None, description="点云任务ID（如果有）")
    timestamp: str = Field(..., description="响应时间戳")


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Agent聊天接口",
    description="""
    智能对话接口，支持：
    
    1. **自然语言理解**：理解用户意图
    2. **查询优化**：将口语化描述转为精确语义（预留LLM集成）
    3. **工具调用**：自动调用搜索、删除等后端服务
    4. **自然回复**：生成对话式响应
    5. **多轮对话**：通过session_id保持上下文
    
    **使用示例**：
    ```json
    {
      "query": "我昨天拍的小狗照片",
      "top_k": 5
    }
    ```
    
    **预留扩展**：
    - 接入小参数LLM做查询优化
    - Function Calling工具链
    - RAG增强生成
    """
)
async def agent_chat(
    message: ChatMessage,
    background_tasks: BackgroundTasks,
    search_svc: SearchService = Depends(get_search_service),
    agent_svc: AgentService = Depends(get_agent_service)
):
    """
    Agent聊天主接口

    处理流程：
    1. 创建/获取会话
    2. 意图识别
    3. 查询优化（预留LLM）
    4. 执行工具调用
    5. 生成自然语言响应
    6. 返回结果+建议
    """
    from datetime import datetime

    # 初始化Agent服务
    if not agent_svc.is_initialized:
        agent_svc.initialize()

    # 创建或获取会话
    session_id = message.session_id
    if not session_id:
        session_id = agent_svc.create_session()

    agent_svc.ensure_session(session_id)

    # 1. 意图识别
    # 优先使用 ReAct Agent 进行智能对话和意图处理
    if agent_svc.is_initialized and agent_svc._agent:
        try:
            # ReAct Agent 会自动判断是否需要调用工具（如搜索）
            # 对于 "你好"、"你是谁" 等闲聊，它会直接回复而不调用工具
            agent_result = await agent_svc.chat(message.query, session_id)
            response = agent_result.get("answer", "")
            images = agent_result.get("images") or []
            recommendation = agent_result.get("recommendation")
            
            # 构建响应
            chat_response = ChatResponse(
                session_id=session_id,
                answer=response,
                intent="auto",
                optimized_query=message.query,
                results={"total": len(images), "images": images} if len(images) > 0 else None,
                suggestions=[],
                recommendation=recommendation,
                pointcloud_id=agent_result.get("pointcloud_id"),
                timestamp=datetime.now().isoformat()
            )
            
            # 如果有推荐信息，记录日志
            if recommendation:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(
                    f"[API] 返回图片推荐: "
                    f"推荐ID={recommendation.get('recommended_image_id')}, "
                    f"备选数量={len(recommendation.get('alternative_image_ids', []))}, "
                    f"提示删除={recommendation.get('user_prompt_for_deletion')}"
                )
            
            # 启动点云后台监控（如果有）
            pointcloud_id = agent_result.get("pointcloud_id")
            if pointcloud_id:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"[API] 检测到点云生成任务，启动后台监控: {pointcloud_id}")
                background_tasks.add_task(
                    agent_svc._monitor_and_update_pointcloud,
                    pointcloud_id=pointcloud_id,
                    session_id=session_id
                )
            
            return chat_response
        except Exception as e:
            # Agent 执行失败，记录详细错误并返回有用的信息
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Agent执行失败: {e}", exc_info=True)
            
            # 返回详细的错误信息
            error_message = f"抱歉，智慧相册Agent暂时无法响应。错误信息: {str(e)}"
            
            return ChatResponse(
                session_id=session_id,
                answer=error_message,
                intent="error",
                optimized_query=message.query,
                results=None,
                suggestions=["请稍后再试", "检查网络连接", "联系管理员"],
                timestamp=datetime.now().isoformat()
            )

    # --- 以下为降级处理逻辑 (Rule-based) ---
    intent_result = agent_svc.detect_intent(message.query)
    intent = intent_result["intent"]

    # 2. 查询优化（当前简化版，预留LLM接入点）
    optimized_query = agent_svc.optimize_query(message.query, session_id)

    # 3. 执行工具调用（当前主要支持搜索）
    results = None

    if intent == "search":
        if not search_svc.is_initialized:
            raise HTTPException(status_code=503, detail="搜索服务未初始化")

        # 调用搜索服务
        search_results = search_svc.search_by_text(
            query_text=optimized_query,
            top_k=message.top_k,
            score_threshold=message.score_threshold
        )

        results = {
            "total": len(search_results),
            "images": search_results
        }
    
    elif intent == "chat":
        # 普通聊天，没有特定操作
        results = {}

    elif intent == "delete":
        results = {"message": "删除功能需要指定图片ID，请使用 /agent/execute 接口"}

    elif intent == "upload":
        results = {"message": "上传功能请使用 /storage/upload 接口"}

    elif intent == "analyze":
        results = {"message": "图片分析功能即将上线"}

    else:
        results = {"message": "抱歉，我还不太理解您的意思"}

    # 4. 生成自然语言回复
    answer = agent_svc.generate_response(intent, results, message.query)

    # 5. 生成后续建议
    suggestions = agent_svc.generate_suggestions(intent, results)

    # 6. 返回响应
    return ChatResponse(
        session_id=session_id,
        answer=answer,
        intent=intent,
        optimized_query=optimized_query,
        results=results,
        suggestions=suggestions,
        timestamp=datetime.now().isoformat()
    )


@router.post(
    "/session/create",
    summary="创建新会话",
    description="创建一个新的对话会话，用于多轮对话场景"
)
async def create_session(
    user_id: Optional[str] = Body(None, description="用户ID（可选）"),
    agent_svc: AgentService = Depends(get_agent_service)
):
    """创建新会话"""
    if not agent_svc.is_initialized:
        agent_svc.initialize()

    session_id = agent_svc.create_session(user_id)

    return {
        "status": "success",
        "session_id": session_id,
        "message": "会话创建成功"
    }


@router.get(
    "/session/{session_id}",
    summary="获取会话信息",
    description="查看指定会话的历史记录和上下文"
)
async def get_session_info(
    session_id: str,
    agent_svc: AgentService = Depends(get_agent_service)
):
    """获取会话信息"""
    session = agent_svc.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

    return {
        "status": "success",
        "session": {
            "session_id": session_id,
            "user_id": session.get("user_id"),
            "created_at": session.get("created_at").isoformat(),
            "history_count": len(session.get("history", [])),
            "context": session.get("context", {})
        }
    }


@router.get(
    "/session/{session_id}/events",
    summary="获取会话系统事件",
    description="获取指定会话中的系统事件（如点云生成完成等）"
)
async def get_session_events(
    session_id: str,
    agent_svc: AgentService = Depends(get_agent_service)
):
    """获取会话系统事件"""
    session = agent_svc.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

    # 从历史记录中提取系统事件
    events = [
        msg for msg in session.get("history", [])
        if msg.get("role") == "system" and msg.get("event")
    ]

    return {
        "status": "success",
        "events": events,
        "count": len(events)
    }


@router.get(
    "/time",
    summary="获取当前时间",
    description="返回当前系统时间，格式为 YYYY-MM-DD HH:MM:SS"
)
async def get_current_time():
    """获取当前系统时间"""
    from datetime import datetime
    return {
        "status": "success",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get(
    "/meta/schema",
    summary="获取图片元数据字段定义",
    description="返回相册图片可用的元数据字段与含义，用于指导后续的元数据检索操作"
)
async def get_photo_meta_schema():
    """获取图片元数据字段定义"""
    schema = {
        "fields": {
            "filename": "文件名",
            "file_size": "文件大小（字节）",
            "width": "图片宽度",
            "height": "图片高度",
            "format": "图片格式（如 JPEG、PNG）",
            "created_at": "创建时间（ISO 8601 格式，如 2026-01-18T15:30:00）",
            "tags": "标签列表，字符串数组",
            "description": "图片描述",
            "extra": "扩展字段对象"
        },
        "date_formats": [
            "1.18（表示1月18日）",
            "1.18.2026 或 2026.1.18（完整日期）",
            "1月18日 或 1月18（中文格式）",
            "2026-01-18（ISO 格式）"
        ],
        "examples": [
            {"description": "查找特定日期的照片", "usage": "使用 /api/v1/search/meta 接口，参数 date_text='1.18'"},
            {"description": "按标签筛选", "usage": "使用 /api/v1/search/meta 接口，参数 tags='cat,outdoor'"},
            {"description": "日期+语义组合检索", "usage": "使用 /api/v1/search/meta/hybrid 接口，参数 date_text='1.18', query='海边日落'"}
        ]
    }
    return {
        "status": "success",
        "schema": schema
    }


@router.post(
    "/recommendation/delete",
    response_model=BaseResponse,
    summary="根据推荐删除图片",
    description="""
    根据Agent的推荐结果删除图片
    
    使用场景：
    1. Agent分析多张照片后推荐最佳照片
    2. 用户确认删除其他照片
    3. 系统执行批量删除操作
    
    安全机制：
    - 必须用户明确确认（confirmed=true）
    - 记录删除原因
    - 返回详细的成功/失败统计
    """
)
async def delete_images_by_recommendation(
    request: DeleteConfirmationRequest,
    storage_svc: StorageService = Depends(get_storage_service),
    vector_db_svc: VectorDBService = Depends(get_vector_db_service)
):
    """
    根据推荐删除图片
    
    Args:
        request: 删除确认请求，包含图片ID列表和确认标志
        
    Returns:
        删除确认响应，包含成功和失败的统计
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 验证用户确认
    if not request.confirmed:
        logger.warning(f"[API] 用户未确认删除操作，拒绝执行")
        raise HTTPException(
            status_code=400,
            detail="必须确认删除操作（confirmed=true）才能执行"
        )
    
    # 验证图片ID列表不为空
    if not request.image_ids:
        logger.warning(f"[API] 图片ID列表为空")
        raise HTTPException(
            status_code=400,
            detail="图片ID列表不能为空"
        )
    
    logger.info(
        f"[API] 开始批量删除图片: "
        f"数量={len(request.image_ids)}, "
        f"原因={request.reason}"
    )
    
    # 批量删除
    deleted_ids = []
    failed_ids = []
    
    for image_id in request.image_ids:
        try:
            # 1. 从向量数据库删除
            vector_db_deleted = vector_db_svc.delete(image_id)
            
            if vector_db_deleted:
                # 2. 从存储服务删除
                storage_deleted = storage_svc.delete_image(image_id)
                
                if storage_deleted:
                    deleted_ids.append(image_id)
                    logger.info(f"[API] 成功删除图片: {image_id}")
                else:
                    failed_ids.append(image_id)
                    logger.warning(f"[API] 向量数据库删除成功，但存储删除失败: {image_id}")
            else:
                failed_ids.append(image_id)
                logger.warning(f"[API] 向量数据库删除失败: {image_id}")
                
        except Exception as e:
            failed_ids.append(image_id)
            logger.error(f"[API] 删除图片异常: {image_id}, 错误: {e}")
    
    # 构建响应
    response = DeleteConfirmationResponse(
        deleted_count=len(deleted_ids),
        failed_count=len(failed_ids),
        deleted_image_ids=deleted_ids,
        failed_image_ids=failed_ids
    )
    
    logger.info(
        f"[API] 批量删除完成: "
        f"成功={len(deleted_ids)}, 失败={len(failed_ids)}"
    )
    
    return BaseResponse(
        status=ResponseStatus.SUCCESS,
        message=f"成功删除 {len(deleted_ids)} 张图片，失败 {len(failed_ids)} 张",
        data=response.dict()
    )


@router.post(
    "/recommendation/preview-delete",
    summary="预览删除操作",
    description="""
    预览将要删除的图片信息，但不实际删除
    
    用于在用户确认前展示即将删除的图片信息
    """
)
async def preview_delete_operation(
    image_ids: List[str] = Body(..., description="要预览删除的图片ID列表"),
    storage_svc: StorageService = Depends(get_storage_service)
):
    """
    预览删除操作
    
    Args:
        image_ids: 图片ID列表
        
    Returns:
        图片信息列表
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[API] 预览删除操作: 数量={len(image_ids)}")
    
    # 获取图片信息
    images_info = []
    for image_id in image_ids:
        try:
            image_info = storage_svc.get_image_info(image_id)
            if image_info:
                images_info.append({
                    "id": image_id,
                    "filename": image_info.get("filename"),
                    "file_size": image_info.get("file_size"),
                    "width": image_info.get("width"),
                    "height": image_info.get("height"),
                    "created_at": image_info.get("created_at")
                })
        except Exception as e:
            logger.warning(f"[API] 获取图片信息失败: {image_id}, 错误: {e}")
    
    return {
        "status": "success",
        "total": len(images_info),
        "images": images_info
    }
