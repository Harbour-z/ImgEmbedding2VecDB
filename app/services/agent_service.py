"""
AI Agent服务模块
处理自然语言查询、意图识别、查询优化和工具调用
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentService:
    """
    Agent服务类

    职责：
    1. 查询优化：将用户自然语言转换为更精确的搜索语义
    2. 意图识别：判断用户想做什么（搜索/上传/删除等）
    3. 工具调用：根据意图调用相应的后端服务
    4. 响应生成：组织自然语言回复

    预留接口：
    - LLM集成：接入小参数量LLM做查询优化
    - 多轮对话：管理会话上下文
    - 工具链：Function Calling / ReAct模式
    """

    _instance: Optional["AgentService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._initialized = getattr(self, '_initialized', False)
        self._sessions: Dict[str, Dict[str, Any]] = {}  # 会话管理
        self._llm_client = None  # 预留LLM客户端

    def initialize(
        self,
        llm_model_path: Optional[str] = None,
        llm_api_url: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        初始化Agent服务

        Args:
            llm_model_path: 本地LLM模型路径（预留）
            llm_api_url: LLM API地址（预留）
        """
        if self._initialized:
            logger.info("Agent服务已初始化")
            return

        # 预留：初始化LLM客户端
        # if llm_model_path:
        #     self._llm_client = load_llm_model(llm_model_path)
        # elif llm_api_url:
        #     self._llm_client = LLMAPIClient(llm_api_url)

        self._initialized = True
        logger.info("Agent服务初始化完成（当前为简化模式，LLM功能预留）")

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def create_session(self, user_id: Optional[str] = None) -> str:
        """创建新会话"""
        import uuid
        session_id = str(uuid.uuid4())

        self._sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now(),
            "history": [],  # 对话历史
            "context": {}   # 上下文信息
        }

        logger.info(f"创建会话: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        return self._sessions.get(session_id)

    def optimize_query(self, user_query: str, session_id: Optional[str] = None) -> str:
        """
        查询优化：将自然语言转换为更精确的搜索语义

        示例：
        - "我昨天拍的照片" → "2024年1月14日拍摄的照片"
        - "小狗狗" → "可爱的狗 宠物犬"
        - "那张模糊的" → 保持原样（当前版本）

        预留：接入LLM做语义理解和改写
        """
        logger.info(f"查询优化: '{user_query}'")

        # 当前简化版本：直接返回原查询
        # TODO: 接入LLM做查询改写
        # if self._llm_client:
        #     optimized = self._llm_client.optimize_query(user_query)
        #     logger.info(f"优化后: '{optimized}'")
        #     return optimized

        # 简单的关键词扩展（示例）
        optimized_query = user_query

        # 保存到会话历史
        if session_id:
            session = self.get_session(session_id)
            if session:
                session["history"].append({
                    "type": "query_optimize",
                    "original": user_query,
                    "optimized": optimized_query,
                    "timestamp": datetime.now()
                })

        return optimized_query

    def detect_intent(self, user_query: str) -> Dict[str, Any]:
        """
        意图识别：判断用户想做什么

        返回格式：
        {
            "intent": "search" | "upload" | "delete" | "analyze" | "unknown",
            "confidence": 0.0-1.0,
            "entities": {...}  # 提取的实体信息
        }

        预留：接入LLM做意图分类
        """
        logger.info(f"意图识别: '{user_query}'")

        # 简化版本：基于关键词规则
        query_lower = user_query.lower()

        # 删除意图
        if any(kw in query_lower for kw in ["删除", "删掉", "remove", "delete"]):
            return {
                "intent": "delete",
                "confidence": 0.8,
                "entities": {}
            }

        # 上传意图
        if any(kw in query_lower for kw in ["上传", "添加", "upload", "add"]):
            return {
                "intent": "upload",
                "confidence": 0.8,
                "entities": {}
            }

        # 分析意图
        if any(kw in query_lower for kw in ["分析", "识别", "这是什么", "analyze"]):
            return {
                "intent": "analyze",
                "confidence": 0.7,
                "entities": {}
            }

        # 默认为搜索意图
        return {
            "intent": "search",
            "confidence": 0.9,
            "entities": {}
        }

    def generate_response(
        self,
        intent: str,
        results: Any,
        user_query: str
    ) -> str:
        """
        生成自然语言回复

        预留：接入LLM生成更自然的对话式回复
        """
        if intent == "search":
            if isinstance(results, dict):
                total = results.get("total", 0)
                if total == 0:
                    return f"抱歉，没有找到与「{user_query}」相关的照片。可以尝试换个描述方式。"
                elif total == 1:
                    return f"找到 1 张符合「{user_query}」的照片。"
                else:
                    return f"为您找到了 {total} 张与「{user_query}」相关的照片。"

        elif intent == "delete":
            return "删除操作已完成。"

        elif intent == "upload":
            return "图片上传成功。"

        elif intent == "analyze":
            return "图片分析功能即将上线，敬请期待。"

        return "已完成您的请求。"

    def generate_suggestions(
        self,
        intent: str,
        results: Any,
        history: Optional[List[str]] = None
    ) -> List[str]:
        """
        生成后续建议

        预留：基于对话历史和搜索结果智能推荐
        """
        suggestions = []

        if intent == "search":
            if isinstance(results, dict):
                total = results.get("total", 0)

                if total == 0:
                    suggestions = [
                        "换个描述试试",
                        "查看所有照片",
                        "按日期筛选"
                    ]
                elif total > 10:
                    suggestions = [
                        "添加更多细节缩小范围",
                        "按标签过滤",
                        "查看相似图片"
                    ]
                else:
                    suggestions = [
                        "查找相似的照片",
                        "这些照片是什么时候拍的",
                        "给这些照片打标签"
                    ]

        return suggestions


# 全局服务实例
_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """获取Agent服务实例"""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
