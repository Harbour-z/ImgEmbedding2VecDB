"""
AI Agent服务模块
处理自然语言查询、意图识别、查询优化和工具调用
"""

import logging
import asyncio
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextvars import ContextVar
from ..config import get_settings

# 引入 OpenJiuwen Core 组件
try:
    from openjiuwen.agent.react_agent.react_agent import ReActAgent
    from openjiuwen.agent.config.react_config import ReActAgentConfig, ConstrainConfig
    from openjiuwen.core.component.common.configs.model_config import ModelConfig
    from openjiuwen.core.utils.llm.base import BaseModelInfo
    from openjiuwen.core.utils.tool.param import Param
    from openjiuwen.core.agent.agent import BaseAgent
    from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
    HAS_OPENJIUWEN = True
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"OpenJiuwen import failed: {e}")
    HAS_OPENJIUWEN = False
    ReActAgent = None
    RestfulApi = None
    Param = None
    BaseModelInfo = None

logger = logging.getLogger(__name__)


class AgentService:
    """
    Agent服务类

    职责：
    1. 查询优化：将用户自然语言转换为更精确的搜索语义
    2. 意图识别：判断用户想做什么（搜索/上传/删除等）
    3. 工具调用：根据意图调用相应的后端服务
    4. 响应生成：组织自然语言回复

    核心升级：
    - 集成 OpenJiuwen ReActAgent
    - 支持 OpenAI 兼容 API
    """

    _instance: Optional["AgentService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._initialized = getattr(self, '_initialized', False)
        self._sessions: Dict[str, Dict[str, Any]] = {}  # 会话管理
        self._agent: Optional[ReActAgent] = None  # ReActAgent实例
        self._tools: List[Any] = []    # 注册的工具列表
        self._current_conversation_id: ContextVar[Optional[str]] = ContextVar("current_conversation_id", default=None)
        self._last_images_by_conversation: Dict[str, List[Dict[str, Any]]] = {}

    def initialize(
        self,
        llm_model_path: Optional[str] = None,
        llm_api_url: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        初始化Agent服务
        """
        if self._initialized:
            logger.info("Agent服务已初始化")
            return

        settings = get_settings()
        logger.info(f"开始初始化Agent服务... (Enabled: {settings.AGENT_ENABLED})")
        
        # 配置OpenAI兼容的API接入并初始化Agent
        if settings.AGENT_ENABLED and settings.OPENAI_API_KEY:
            if not HAS_OPENJIUWEN:
                logger.error("OpenJiuwen库未安装或导入失败，无法启用Agent功能")
                return

            try:
                logger.info(f"正在配置ReAct Agent (Provider: {settings.AGENT_PROVIDER}, Model: {settings.OPENAI_MODEL_NAME})...")
                self._setup_agent(settings)
                
                # 验证连接性 (可选)
                logger.info("Agent服务初始化完成，已准备就绪")
            except Exception as e:
                logger.error(f"Agent初始化失败: {e}", exc_info=True)
                logger.warning("系统将以无Agent模式运行 (Rule-based Fallback)")
        else:
            logger.info("Agent服务初始化完成（简化模式，未配置OpenAI API）")

        self._initialized = True

    def _setup_agent(self, settings):
        """配置并初始化 ReActAgent"""
        ssl_verify = bool(settings.LLM_SSL_VERIFY)
        ssl_cert = settings.LLM_SSL_CERT
        if ssl_verify and not ssl_cert:
            logger.warning("LLM_SSL_VERIFY=true but LLM_SSL_CERT is missing; forcing LLM_SSL_VERIFY=false")
            ssl_verify = False

        os.environ["LLM_SSL_VERIFY"] = "true" if ssl_verify else "false"
        if ssl_cert:
            os.environ["LLM_SSL_CERT"] = ssl_cert
        else:
            os.environ.pop("LLM_SSL_CERT", None)

        logger.info(
            "LLM SSL config applied (LLM_SSL_VERIFY=%s, LLM_SSL_CERT=%s)",
            os.environ.get("LLM_SSL_VERIFY"),
            "set" if os.environ.get("LLM_SSL_CERT") else "unset",
        )

        # 禁用 OpenJiuwen 的 SSRF 保护，允许访问本地服务
        os.environ["SSRF_PROTECT_ENABLED"] = "false"
        logger.info("OpenJiuwen SSRF protection disabled for local API access")

        # 1. 注册核心工具
        self._register_core_tools()
        
        # 2. 构建模型配置
        # 注意：BaseModelInfo 使用 api_base 而非 base_url
        model_name = (settings.OPENAI_MODEL_NAME or "").strip()
        if not model_name:
            raise ValueError("OPENAI_MODEL_NAME 为空，无法初始化Agent")

        model_info = BaseModelInfo(
            model=model_name,
            api_key=settings.OPENAI_API_KEY,
            api_base=settings.OPENAI_BASE_URL,
            streaming=False
        )
        
        # 构建 ModelConfig
        # 假设 settings.AGENT_PROVIDER 是 "openai" 或 "deepseek" 等
        model_config = ModelConfig(
            model_provider=settings.AGENT_PROVIDER,
            model_info=model_info
        )
        
        # 3. 构建Agent配置
        agent_config = ReActAgentConfig(
            id="smart_album_agent",
            version="1.0.0",
            description="Smart Album Agent powered by OpenJiuwen",
            model=model_config,
            constrain=ConstrainConfig(
                max_iteration=6
            ),
            prompt_template=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful smart album assistant for a photo album. "
                        "Each photo has metadata fields available for filtering: filename, file_size, width, height, format, created_at (ISO datetime), tags (list of strings), description, extra (object). "
                        
                        "IMPORTANT INSTRUCTIONS FOR TIME-BASED QUERIES:\n"
                        "1. When user asks for photos from a specific time period (e.g., 'last year', '2023年7月', 'yesterday', '去年的海边照片'), "
                        "   first use get_current_time to understand the current date, then calculate the target date range.\n"
                        "2. For date-based searches, use meta_search_images with the appropriate date_text parameter.\n"
                        "3. Supported date formats: '1.18', '1月18日', '2026-01-18', '2023.7', '2023年7月'.\n"
                        "4. If the user provides both date and semantic description (e.g., '2023年7月 海边', '去年的海边照片'), use meta_search_hybrid.\n"
                        "5. When user says 'last year' or '去年', calculate the previous year based on current date.\n"
                        
                        "TOOL USAGE GUIDELINES:\n"
                        "- Use semantic_search_images when the user describes visual/semantic content and wants similarity matching without metadata constraints.\n"
                        "- Use meta_search_images when the user wants to filter by metadata only (date, tags, filename, etc.).\n"
                        "- Use meta_search_hybrid when the user mixes metadata filtering + semantic description.\n"
                        "- Use search_by_image_id when user provides an image ID for similar image search.\n"
                        "- Use get_current_time when user asks for time or when you need to calculate date ranges.\n"
                        "- Use get_photo_meta_schema when user needs to understand available metadata fields.\n"
                        
                        "IMAGE EDITING:\n"
                        "- Use edit_image when user wants to edit or transform photos, especially for style conversions.\n"
                        "- Supported editing operations include: style conversion (anime, cartoon, oil painting, watercolor, sketch, cyberpunk, retro, cinematic), text editing, object addition/deletion/modification, background replacement, photo restoration.\n"
                        "- Common trigger phrases: '转成动漫风格', '换个风格', '编辑这张图片', '改成XXX风格', '把这张图转成...', '用动漫风格', '生成卡通版本'.\n"
                        "- When editing images, you MUST first search for the image to get its ID, then call edit_image with the image_id and appropriate prompt.\n"
                        "- The edit_image tool automatically enables intelligent prompt extension to optimize simple descriptions.\n"
                        "- After editing, display the generated images using Markdown format: ![edited image](/api/v1/storage/images/{image_id}).\n"
                        "\n"
                        "3D POINT CLOUD GENERATION:\n"
                        "- Use generate_pointcloud when user wants to generate 3D models or point clouds from photos.\n"
                        "- This tool converts 2D photos into 3DGS point cloud (PLY format) for 3D visualization and modeling.\n"
                        "- Common trigger phrases: '生成3D点云', '转成3D', '制作3D模型', '查看3D效果', '生成点云模型'.\n"
                        "- When generating point clouds, you MUST first search for the image to get its ID, then call generate_pointcloud with the image_id.\n"
                        "- Quality options: 'balanced' for high quality (recommended), 'fast' for faster generation.\n"
                        "- The tool supports async mode (recommended) which returns immediately with a task ID, avoiding long wait times.\n"
                        "- The response includes download_url for the PLY file and view_url for 3D browser preview.\n"
                        
                        "ERROR HANDLING:\n"
                        "- If a tool call fails, try to understand the error and provide helpful feedback to the user.\n"
                        "- If you cannot find photos matching the criteria, suggest alternative search terms or ask for clarification.\n"
                        "- Always be specific about what you searched for and what results you found.\n"
                        "- If get_current_time tool fails, ask the user to provide the specific date directly.\n"
                        
                        "RESPONSE STYLE:\n"
                        "- Be conversational and helpful.\n"
                        "- When you find photos, mention how many you found and briefly describe them.\n"
                        "- When you don't find photos, suggest alternative search strategies.\n"
                        "- Always provide the actual search results when available.\n"
                        "\n"
                        "IMPORTANT - INCLUDE IMAGE LINKS IN RESPONSE:\n"
                        "- When you find photos, you MUST include Markdown image links in your response.\n"
                        "- Format: ![image description](/api/v1/storage/images/{image_id})\n"
                        "- Include the image_id from the tool result in the URL.\n"
                        "- This allows the frontend to display image previews.\n"
                        "- Example: ![柴犬照片](/api/v1/storage/images/308385fb-1792-4e49-93c3-55c8d4ed5eae)"
                    )
                }
            ]
        )
        
        # 4. 实例化 ReActAgent
        self._agent = ReActAgent(agent_config=agent_config)
        
        # 5. 绑定工具 (使用 BaseAgent 的 add_tools 方法)
        if self._tools:
            self._agent.add_tools(self._tools)

    def _register_core_tools(self):
        """
        注册Agent可用工具

        遵循OpenJiuwen标准构建流程：
        1. 后端API端点已在 routers/search.py 和 routers/agent.py 中定义
        2. 使用RestfulApi和Param显式创建API工具对象
        3. 通过add_tools方法注册到Agent

        已注册的工具列表：
        - semantic_search_images: 语义相似度检索图片（/search/text）
        - search_by_image_id: 以图搜图（/search/image/{image_id}）
        - meta_search_images: 元数据检索（/search/meta）
        - meta_search_hybrid: 元数据+语义混合检索（/search/meta/hybrid）
        - agent_execute_action: 执行Agent动作（/agent/execute）
        - get_current_time: 获取当前时间（/agent/time）
        - get_photo_meta_schema: 获取元数据字段定义（/agent/meta/schema）
        - generate_social_media_caption: 朋友圈/小红书文案生成（/social/caption）
        - recommend_images: 智能图片推荐（/image-recommendation/analyze）
        - edit_image: 图片编辑和风格转换（/image-edit/edit）
        - generate_pointcloud: 3D点云生成（/pointcloud/generate）
        - knowledge_qa: 基于图片的智能知识问答（/knowledge-qa/qa）
        """
        settings = get_settings()
        
        # 从配置中读取 API 基础 URL，支持环境变量覆盖
        # 使用 127.0.0.1 代替 localhost，避免 OpenJiuwen 的 URL 验证问题
        api_base = os.getenv("AGENT_API_BASE_URL", "http://127.0.0.1:8000")
        api_prefix = "/api/v1"
        
        logger.info(f"Agent工具注册，API基础URL: {api_base}")

        tool_semantic_search_images = RestfulApi(
            name="semantic_search_images",
            description="语义相似度检索图片工具。当用户用自然语言描述画面内容并想要查找相似图片时使用此工具。例如：'海边日落'、'红色跑车'、'穿着白色连衣裙的女孩'。",
            params=[
                Param(name="query", description="用户的搜索描述，例如 '穿红衣服的人' 或 '海边的日落'", param_type="string", required=True),
                Param(name="instruction", description="自定义指令（可选）", param_type="string", required=False, default_value="", method="Query"),
                Param(name="top_k", description="返回结果的数量，默认为10", param_type="integer", default_value=10, required=False, method="Query"),
                Param(name="score_threshold", description="相似度阈值（可选），范围0-1", param_type="number", required=False, method="Query"),
                Param(name="tags", description="标签过滤（可选），逗号分隔的字符串，例如 'cat,outdoor'", param_type="string", required=False, default_value="", method="Query")
            ],
            path=f"{api_base}{api_prefix}/search/text",
            headers={"Content-Type": "application/json"},
            method="GET",
            response=[
                Param(name="status", description="响应状态", param_type="string"),
                Param(name="message", description="响应消息", param_type="string"),
                Param(name="data", description="搜索结果列表", param_type="array"),
                Param(name="total", description="结果总数", param_type="integer")
            ]
        )
        self._tools.append(tool_semantic_search_images)

        tool_search_by_image_id = RestfulApi(
            name="search_by_image_id",
            description="以图搜图工具。根据指定图片ID搜索相似图片。",
            params=[
                Param(name="image_id", description="查询图片的ID", param_type="string", required=True),
                Param(name="instruction", description="自定义指令（可选）", param_type="string", required=False, default_value="", method="Query"),
                Param(name="top_k", description="返回结果的数量，默认为10", param_type="integer", default_value=10, required=False, method="Query"),
                Param(name="score_threshold", description="相似度阈值（可选），范围0-1", param_type="number", required=False, method="Query"),
                Param(name="tags", description="标签过滤（可选），逗号分隔的字符串", param_type="string", required=False, default_value="", method="Query")
            ],
            path=f"{api_base}{api_prefix}/search/image/{{image_id}}",
            headers={"Content-Type": "application/json"},
            method="GET",
            response=[
                Param(name="status", description="响应状态", param_type="string"),
                Param(name="message", description="响应消息", param_type="string"),
                Param(name="data", description="搜索结果列表", param_type="array"),
                Param(name="total", description="结果总数", param_type="integer")
            ]
        )
        self._tools.append(tool_search_by_image_id)

        tool_meta_search_images = RestfulApi(
            name="meta_search_images",
            description="按元数据检索图片，或做组合检索（日期过滤 + 语义相似度）。适用于以下场景：纯日期检索：'1.18 的照片'、'1月18日的照片'、'2026-01-18'；标签检索：'标签是猫的照片'；组合检索：'1.18 海边'、'1月18日 红色跑车'。",
            params=[
                Param(name="date_text", description="日期文本，支持格式：1.18 / 1月18日 / 2026-01-18", param_type="string", required=False, method="Query"),
                Param(name="tags", description="标签过滤（可选），逗号分隔的字符串，例如 'cat,outdoor'", param_type="string", required=False, method="Query"),
                Param(name="top_k", description="返回结果数量，默认为5", param_type="integer", default_value=5, required=False, method="Query")
            ],
            path=f"{api_base}{api_prefix}/search/meta",
            headers={"Content-Type": "application/json"},
            method="GET",
            response=[
                Param(name="status", description="响应状态", param_type="string"),
                Param(name="message", description="响应消息", param_type="string"),
                Param(name="data", description="搜索结果列表", param_type="array"),
                Param(name="total", description="结果总数", param_type="integer")
            ]
        )
        self._tools.append(tool_meta_search_images)

        tool_meta_search_hybrid = RestfulApi(
            name="meta_search_hybrid",
            description="元数据+语义混合检索。当用户同时提供日期和语义描述时使用此工具。例如：'1.18 海边'、'1月18日 红色跑车'。",
            params=[
                Param(name="date_text", description="日期文本，支持格式：1.18 / 1月18日 / 2026-01-18", param_type="string", required=False, method="Query"),
                Param(name="tags", description="标签过滤（可选），逗号分隔的字符串，例如 'cat,outdoor'", param_type="string", required=False, method="Query"),
                Param(name="query", description="语义查询描述，例如 '海边日落'", param_type="string", required=False, method="Query"),
                Param(name="top_k", description="返回结果数量，默认为5", param_type="integer", default_value=5, required=False, method="Query")
            ],
            path=f"{api_base}{api_prefix}/search/meta/hybrid",
            headers={"Content-Type": "application/json"},
            method="GET",
            response=[
                Param(name="status", description="响应状态", param_type="string"),
                Param(name="message", description="响应消息", param_type="string"),
                Param(name="data", description="搜索结果列表", param_type="array"),
                Param(name="total", description="结果总数", param_type="integer")
            ]
        )
        self._tools.append(tool_meta_search_hybrid)

        tool_agent_execute = RestfulApi(
            name="agent_execute_action",
            description="执行Agent动作。支持：search（搜索图片）、delete（删除图片）、update（更新图片信息）等操作。",
            params=[
                Param(name="action", description="动作类型：search/delete/update/analyze", param_type="string", required=True, method="Body"),
                Param(name="parameters", description="动作参数对象，包含查询、图片ID等信息", param_type="object", required=True, method="Body", schema=[
                    {"name": "query", "description": "搜索查询文本", "type": "string", "required": False},
                    {"name": "image_id", "description": "图片ID", "type": "string", "required": False},
                    {"name": "top_k", "description": "返回结果数量", "type": "integer", "required": False}
                ]),
                Param(name="context", description="上下文信息（可选）", param_type="object", required=False, method="Body", schema=[
                    {"name": "session_id", "description": "会话ID", "type": "string", "required": False},
                    {"name": "user_id", "description": "用户ID", "type": "string", "required": False}
                ])
            ],
            path=f"{api_base}{api_prefix}/agent/execute",
            headers={"Content-Type": "application/json"},
            method="POST",
            response=[
                Param(name="status", description="响应状态", param_type="string"),
                Param(name="message", description="响应消息", param_type="string"),
                Param(name="data", description="执行结果", param_type="object", schema=[
                    {"name": "results", "description": "搜索结果列表", "type": "array", "required": False},
                    {"name": "total", "description": "结果总数", "type": "integer", "required": False}
                ])
            ]
        )
        self._tools.append(tool_agent_execute)

        tool_get_current_time = RestfulApi(
            name="get_current_time",
            description="获取当前系统时间，格式为 YYYY-MM-DD HH:MM:SS",
            params=[],
            path=f"{api_base}{api_prefix}/agent/time",
            headers={"Content-Type": "application/json"},
            method="GET",
            response=[
                Param(name="status", description="响应状态", param_type="string"),
                Param(name="time", description="当前时间", param_type="string")
            ]
        )
        self._tools.append(tool_get_current_time)

        tool_get_photo_meta_schema = RestfulApi(
            name="get_photo_meta_schema",
            description="获取相册图片可用的元数据字段与含义。用于指导后续的元数据检索操作。",
            params=[],
            path=f"{api_base}{api_prefix}/agent/meta/schema",
            headers={"Content-Type": "application/json"},
            method="GET",
            response=[
                Param(name="status", description="响应状态", param_type="string"),
                Param(name="fields", description="元数据字段定义", param_type="object", schema=[
                    {"name": "filename", "description": "文件名", "type": "string", "required": False},
                    {"name": "file_size", "description": "文件大小（字节）", "type": "integer", "required": False},
                    {"name": "width", "description": "图片宽度", "type": "integer", "required": False},
                    {"name": "height", "description": "图片高度", "type": "integer", "required": False},
                    {"name": "format", "description": "图片格式", "type": "string", "required": False},
                    {"name": "created_at", "description": "创建时间", "type": "string", "required": False},
                    {"name": "tags", "description": "标签列表", "type": "array", "required": False},
                    {"name": "description", "description": "图片描述", "type": "string", "required": False},
                    {"name": "extra", "description": "扩展字段", "type": "string", "required": False}
                ]),
                Param(name="date_formats", description="支持的日期格式列表", param_type="array", schema=[
                    {"name": "format", "description": "日期格式字符串", "type": "string", "required": False}
                ]),
                Param(name="examples", description="使用示例", param_type="array", schema=[
                    {"name": "description", "description": "示例描述", "type": "string", "required": False},
                    {"name": "usage", "description": "使用方法", "type": "string", "required": False}
                ])
            ]
        )
        self._tools.append(tool_get_photo_meta_schema) 

        tool_generate_social_media_caption = RestfulApi(
            name="generate_social_media_caption",
            description="根据指定的图片UUID生成符合用户偏好的朋友圈/小红书文案。当用户说'用这张图写个文案'或'生成朋友圈文案'时使用。注意：你需要先通过检索工具获取图片的UUID。",
            params=[
                Param(name="image_uuid", description="存储在系统storage中的图片的唯一标识符（UUID）。通常来自先前的图片检索结果。", param_type="string", required=True),
                Param(name="style", description="文案风格，例如：'幽默'、'文艺'、'简洁'、'详细'。", param_type="string", required=False, default_value="简洁"),
                Param(name="purpose", description="文案用途，例如：'产品推广'、'生活分享'、'活动宣传'。", param_type="string", required=False, default_value="生活分享")
            ],
            path=f"{api_base}{api_prefix}/social/caption",
            headers={"Content-Type": "application/json"},
            method="POST",
            response=[
                Param(name="status", description="响应状态", param_type="string"),
                Param(name="message", description="响应消息", param_type="string"),
                Param(name="caption", description="生成的文案内容", param_type="string")
            ]
        )
        self._tools.append(tool_generate_social_media_caption)
        
        tool_recommend_images = RestfulApi(
            name="recommend_images",
            description="智能图片推荐工具。使用多模态AI模型（qwen3-max + qwen3-vl-plus）对多张照片进行深度分析，从构图美学、色彩搭配、光影运用、主题表达、情感传达、创意独特性、故事性等艺术维度进行评估，并推荐最佳照片。适用于用户询问'哪一张拍的最好'、'帮我选一张最好的'、'推荐最佳照片'等场景。严禁仅基于分辨率、文件大小等技术参数进行评价。",
            params=[
                Param(name="images", description="图片ID列表（最多10张），JSON数组格式：[\"id1\", \"id2\"]", param_type="array", required=True),
                Param(name="user_preference", description="用户偏好或分析维度（可选），例如：'我更喜欢构图好的'、'关注色彩搭配'", param_type="string", required=False, default_value="")
            ],
            path=f"{api_base}{api_prefix}/image-recommendation/analyze",
            headers={"Content-Type": "application/json"},
            method="POST",
            response=[
                Param(name="status", description="响应状态", param_type="string"),
                Param(name="message", description="响应消息", param_type="string"),
                Param(
                    name="data",
                    description="推荐结果，包含分析详情和推荐信息",
                    param_type="object",
                    required=True,
                    schema=[
                        {
                            "name": "success",
                            "description": "操作是否成功",
                            "type": "boolean",
                            "required": True
                        },
                        {
                            "name": "analysis",
                            "description": "图片分析结果，key为图片ID，value为详细分析",
                            "type": "object",
                            "required": True,
                            "schema": [
                                {
                                    "name": "composition_score",
                                    "description": "构图美学评分（0-10）",
                                    "type": "number",
                                    "required": True
                                },
                                {
                                    "name": "color_score",
                                    "description": "色彩搭配评分（0-10）",
                                    "type": "number",
                                    "required": True
                                },
                                {
                                    "name": "lighting_score",
                                    "description": "光影运用评分（0-10）",
                                    "type": "number",
                                    "required": True
                                },
                                {
                                    "name": "theme_score",
                                    "description": "主题表达评分（0-10）",
                                    "type": "number",
                                    "required": True
                                },
                                {
                                    "name": "emotion_score",
                                    "description": "情感传达评分（0-10）",
                                    "type": "number",
                                    "required": True
                                },
                                {
                                    "name": "creativity_score",
                                    "description": "创意独特性评分（0-10）",
                                    "type": "number",
                                    "required": True
                                },
                                {
                                    "name": "story_score",
                                    "description": "故事性评分（0-10）",
                                    "type": "number",
                                    "required": True
                                },
                                {
                                    "name": "overall_score",
                                    "description": "综合评分（0-10）",
                                    "type": "number",
                                    "required": True
                                },
                                {
                                    "name": "overall_analysis",
                                    "description": "综合评价总结",
                                    "type": "string",
                                    "required": True
                                }
                            ]
                        },
                        {
                            "name": "recommendation",
                            "description": "推荐结果",
                            "type": "object",
                            "required": True,
                            "schema": [
                                {
                                    "name": "best_image_id",
                                    "description": "最佳图片的ID",
                                    "type": "string",
                                    "required": True
                                },
                                {
                                    "name": "recommendation_reason",
                                    "description": "推荐理由详细说明",
                                    "type": "string",
                                    "required": True
                                },
                                {
                                    "name": "alternative_image_ids",
                                    "description": "其他图片ID列表",
                                    "type": "array<string>",
                                    "required": True
                                },
                                {
                                    "name": "key_strengths",
                                    "description": "主要优势点列表",
                                    "type": "array<string>",
                                    "required": True
                                },
                                {
                                    "name": "potential_improvements",
                                    "description": "可改进点列表",
                                    "type": "array<string>",
                                    "required": True
                                }
                            ]
                        },
                        {
                            "name": "model_used",
                            "description": "使用的模型名称",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "total_images",
                            "description": "分析的图片总数",
                            "type": "integer",
                            "required": True
                        }
                    ]
                )
            ]
        )
        self._tools.append(tool_recommend_images)

        tool_edit_image = RestfulApi(
            name="edit_image",
            description="图片编辑工具。使用 qwen-image-edit-plus 模型对图片进行风格转换和编辑。支持动漫风格、卡通风格、油画风格、水彩风格、素描风格、赛博朋克风格、复古风格、电影风格等多种风格转换，以及文字编辑、物体增删改、背景替换等编辑操作。当用户说'把这张图转成动漫风格'、'帮我换个风格'、'编辑这张图片'等时使用。重要：此工具会自动开启智能提示词改写功能以优化生成效果。",
            params=[
                Param(name="image_id", description="要编辑的图片ID（必须先通过检索工具获取图片ID）", param_type="string", required=True, method="Body"),
                Param(name="prompt", description="编辑提示词，例如：'将图片转换为动漫风格'", param_type="string", required=True, method="Body"),
                Param(name="negative_prompt", description="反向提示词，描述不希望出现的内容，例如：'模糊，多余的手指'", param_type="string", required=False, default_value=" ", method="Body"),
                Param(name="prompt_extend", description="是否开启智能提示词改写功能（默认为 true，会优化简单描述的生成效果）", param_type="boolean", required=False, default_value=True, method="Body"),
                Param(name="n", description="生成图片数量（1-6张）", param_type="integer", required=False, default_value=1, method="Body"),
                Param(name="size", description="输出图片分辨率，格式为 '宽*高'，例如 '1024*1536'", param_type="string", required=False, method="Body"),
                Param(name="watermark", description="是否添加水印", param_type="boolean", required=False, default_value=False, method="Body"),
                Param(name="seed", description="随机数种子（可选）", param_type="integer", required=False, method="Body"),
                Param(name="style_tag", description="风格标签，用于元数据记录，例如：'anime', 'cartoon'", param_type="string", required=False, method="Body")
            ],
            path=f"{api_base}{api_prefix}/image-edit/edit",
            headers={"Content-Type": "application/json"},
            method="POST",
            response=[
                Param(name="status", description="响应状态", param_type="string"),
                Param(name="message", description="响应消息", param_type="string"),
                Param(name="data", description="编辑结果，包含生成的图片信息", param_type="object", schema=[
                    Param(name="success", description="操作是否成功", param_type="boolean", required=True),
                    Param(name="saved_images", description="保存的图片列表", param_type="array", required=True, schema=[
                        Param(name="image_id", description="图片ID", param_type="string", required=True),
                        Param(name="url", description="图片URL", param_type="string", required=True),
                        Param(name="metadata", description="元数据信息", param_type="object", required=True, schema=[
                            Param(name="source_image_id", description="源图片ID", param_type="string", required=False),
                            Param(name="edit_prompt", description="编辑提示词", param_type="string", required=False),
                            Param(name="edit_style", description="编辑风格", param_type="string", required=False),
                            Param(name="edit_model", description="使用的编辑模型", param_type="string", required=False),
                            Param(name="edit_parameters", description="编辑参数", param_type="object", required=False, schema=[
                                Param(name="negative_prompt", description="反向提示词", param_type="string", required=False),
                                Param(name="prompt_extend", description="是否开启智能提示词改写", param_type="boolean", required=False),
                                Param(name="n", description="生成图片数量", param_type="integer", required=False),
                                Param(name="size", description="输出图片分辨率", param_type="string", required=False),
                                Param(name="watermark", description="是否添加水印", param_type="boolean", required=False),
                                Param(name="seed", description="随机数种子", param_type="integer", required=False)
                            ]),
                            Param(name="edit_time", description="编辑时间", param_type="string", required=False),
                            Param(name="tags", description="标签列表", param_type="array", required=False, schema=[
                                Param(name="tag", description="标签名称", param_type="string", required=False)
                            ])
                        ])
                    ]),
                    Param(name="total_generated", description="生成的图片总数", param_type="integer", required=True),
                    Param(name="total_saved", description="成功保存的图片数量", param_type="integer", required=True)
                ])
            ]
        )
        self._tools.append(tool_edit_image)

        tool_generate_pointcloud = RestfulApi(
            name="generate_pointcloud",
            description="3D点云生成工具。将图片转换为3DGS点云(PLY格式)。当用户要求生成3D模型、生成点云、将图片转换成3D、或想要查看照片的3D效果时使用此工具。例如：'生成3D点云'、'把这张图转成3D'、'制作3D模型'。重要：必须先通过检索工具获取图片ID才能使用此工具。生成过程支持异步模式，推荐使用异步模式以避免长时间等待。",
            params=[
                Param(name="image_id", description="来源图片ID（必须先通过检索工具获取）", param_type="string", required=True, method="Body"),
                Param(name="quality", description="生成质量：'balanced'（高质量）或 'fast'（快速模式）", param_type="string", required=False, default_value="balanced", method="Body"),
                Param(name="async_mode", description="是否异步生成（推荐true，立即返回任务ID）", param_type="boolean", required=False, default_value=True, method="Body")
            ],
            path=f"{api_base}{api_prefix}/pointcloud/generate",
            headers={"Content-Type": "application/json"},
            method="POST",
            response=[
                Param(name="status", description="响应状态", param_type="string"),
                Param(name="message", description="响应消息", param_type="string"),
                Param(name="data", description="点云生成结果", param_type="object", schema=[
                    Param(name="pointcloud_id", description="点云ID", param_type="string"),
                    Param(name="status", description="生成状态（pending/processing/completed/failed）", param_type="string"),
                    Param(name="source_image_id", description="来源图片ID", param_type="string"),
                    Param(name="file_path", description="PLY文件路径", param_type="string"),
                    Param(name="download_url", description="下载URL", param_type="string"),
                    Param(name="view_url", description="3D预览URL（浏览器可直接查看）", param_type="string"),
                    Param(name="created_at", description="创建时间", param_type="string"),
                    Param(name="completed_at", description="完成时间", param_type="string"),
                    Param(name="file_size", description="文件大小(bytes)", param_type="integer"),
                    Param(name="point_count", description="点云点数", param_type="integer"),
                    Param(name="error_message", description="错误信息", param_type="string")
                ])
            ]
        )
        self._tools.append(tool_generate_pointcloud)

        tool_knowledge_qa = RestfulApi(
            name="knowledge_qa",
            description="基于图片的智能知识问答工具。使用多模态模型（qwen3-vl-plus）对图片进行深度理解和分析，结合用户问题提供准确、有用的回答。适用于以下场景：1. 植物识别与养护：如'这是什么植物？'、'多肉植物怎么养？'；2. 情感分析与祝福：如'这张照片里妈妈开心吗？'、'帮我写个生日祝福文案'；3. 物体识别与推荐：如'冰箱里有什么食材？'、'用这些食材推荐个菜谱'；4. 通用问答：如'这是什么地方？'、'图片里有什么内容？'。重要：必须先通过检索工具获取图片ID才能使用此工具。",
            params=[
                Param(name="image_uuid", description="存储在系统storage中的图片的唯一标识符（UUID）。通常来自先前的图片检索结果。", param_type="string", required=True),
                Param(name="question", description="用户的问题，例如：'这是什么植物？'、'妈妈开心吗？'、'有什么食材？'", param_type="string", required=True),
                Param(name="context", description="额外上下文信息（可选），例如：'这是妈妈60岁生日'、'准备做晚餐'", param_type="string", required=False, default_value="")
            ],
            path=f"{api_base}{api_prefix}/knowledge-qa/qa",
            headers={"Content-Type": "application/json"},
            method="POST",
            response=[
                Param(name="status", description="响应状态", param_type="string"),
                Param(name="message", description="响应消息", param_type="string"),
                Param(name="answer", description="模型生成的回答内容", param_type="string")
            ]
        )
        self._tools.append(tool_knowledge_qa)

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

    def ensure_session(self, session_id: str, user_id: Optional[str] = None) -> str:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "user_id": user_id,
                "created_at": datetime.now(),
                "history": [],
                "context": {},
            }
            logger.info(f"恢复会话: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        return self._sessions.get(session_id)

    async def chat(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        使用ReAct Agent进行对话

        Args:
            query: 用户查询
            session_id: 会话ID

        Returns:
            {"answer": str, "images": list, "recommendation": dict}
        """
        conversation_id = session_id or "default_session"
        self._last_images_by_conversation.pop(conversation_id, None)
        token = self._current_conversation_id.set(conversation_id)

        logger.info(f"[Agent] 开始处理查询: '{query}', session_id: {session_id}, conversation_id: {conversation_id}")

        try:
            if not self._agent:
                logger.warning("[Agent] ReAct Agent未初始化，使用规则引擎回退")
                intent_data = self.detect_intent(query)
                return {
                    "answer": self.generate_response(intent_data["intent"], {"total": 0}, query),
                    "images": [],
                    "recommendation": None
                }

            if session_id:
                self.ensure_session(session_id)

            inputs = {
                "query": query,
                "conversation_id": conversation_id
            }

            logger.info(f"[Agent] 调用ReAct Agent, inputs: {inputs}")
            result = await self._agent.invoke(inputs)
            
            logger.info(f"[Agent] ReAct Agent返回结果类型: {type(result)}")
            logger.debug(f"[Agent] ReAct Agent返回结果: {result}")
            
            response = result.get("output", "抱歉，我没有理解您的意思。")
            logger.info(f"[Agent] 生成的回复: {response[:200]}...")

            if session_id:
                self._update_history(session_id, query, response)

            # 提取回复中的图片链接
            images = self._extract_images_from_response(response, query)
            logger.info(f"[Agent] 返回图片数量: {len(images)}")

            # 初始化推荐信息
            recommendation = {
                "recommended_image_id": None,
                "alternative_image_ids": [],
                "recommendation_reason": "",
                "total_images_analyzed": 0,
                "user_prompt_for_deletion": False
            }

            # 判断是否为点云生成场景
            is_pointcloud = self._detect_pointcloud_generation(query)

            # 只在非点云生成场景下提取推荐信息
            if not is_pointcloud:
                recommendation = self._extract_recommendation_from_response(
                    response=response,
                    context_images=images,
                    is_pointcloud_generation=False
                )
            else:
                # 点云生成场景下，检查是否为多图片分析场景
                if (len(images) > 0 and
                    any(keyword in query.lower() for keyword in ["最好", "推荐", "分析", "比较", "哪一张"])):
                    # 从图片列表中推断推荐
                    if len(images) > 1:
                        logger.info(f"[Agent] 检测到多图片分析场景，使用第一张作为推荐")
                        recommendation["recommended_image_id"] = images[0].get("id")
                        recommendation["alternative_image_ids"] = [img.get("id") for img in images[1:]]
                        recommendation["user_prompt_for_deletion"] = True
                        recommendation["total_images_analyzed"] = len(images)
                    elif len(images) == 1:
                        recommendation["recommended_image_id"] = images[0].get("id")
                        recommendation["alternative_image_ids"] = []
                        recommendation["total_images_analyzed"] = 1

            # 判断是否返回推荐信息
            has_recommendation = (
                recommendation.get("recommended_image_id") is not None and
                recommendation.get("total_images_analyzed", 0) > 0
            )

            if has_recommendation:
                logger.info(
                    f"[Agent] 返回推荐信息: "
                    f"推荐ID={recommendation['recommended_image_id']}, "
                    f"备选数量={len(recommendation['alternative_image_ids'])}"
                )

            # 检测是否为点云生成请求，返回点云ID供前端使用
            pointcloud_id = None
            if self._detect_pointcloud_generation(query):
                pointcloud_id = self._extract_pointcloud_id_from_response(response)
                if pointcloud_id:
                    logger.info(f"[Agent] 检测到点云生成任务，返回点云ID: {pointcloud_id}")
                    # 注意：后台监控任务由API路由层使用BackgroundTasks启动
                else:
                    logger.warning(f"[Agent] 点云生成请求但未找到点云ID")

            return {
                "answer": response,
                "images": images,
                "recommendation": recommendation if has_recommendation else None,
                "pointcloud_id": pointcloud_id  # 返回点云ID供前端使用
            }
        except Exception as e:
            logger.error(f"[Agent] 执行异常: {e}", exc_info=True)
            logger.error(f"[Agent] 异常详情 - query: {query}, session_id: {session_id}")
            return {
                "answer": f"抱歉，智慧相册Agent暂时无法响应。错误信息: {str(e)}",
                "images": [],
                "recommendation": None
            }
        finally:
            try:
                self._current_conversation_id.reset(token)
            except Exception:
                pass

    def _update_history(self, session_id: str, query: str, response: str):
        """更新会话历史"""
        session = self.get_session(session_id)
        if session:
            session["history"].append({
                "role": "user",
                "content": query,
                "timestamp": datetime.now()
            })
            session["history"].append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now()
            })

    async def _monitor_pointcloud_generation(
        self,
        pointcloud_id: str,
        max_wait_seconds: Optional[int] = None
    ) -> Optional[str]:
        """
        监控点云生成状态，等待预览链接

        Args:
            pointcloud_id: 点云ID
            max_wait_seconds: 最大等待时间（秒），默认从配置读取

        Returns:
            预览URL，如果超时或失败则返回None
        """
        from ..config import get_settings
        settings = get_settings()
        
        # 如果未指定，从配置读取监控超时时间
        if max_wait_seconds is None:
            max_wait_seconds = settings.POINTCLOUD_MONITOR_TIMEOUT
        from ..services import get_pointcloud_service
        pointcloud_svc = get_pointcloud_service()

        if not pointcloud_svc.is_initialized:
            logger.warning("点云服务未初始化，无法监控")
            return None

        logger.info(f"[Agent] 开始监控点云生成任务: {pointcloud_id}, 最大等待时间: {max_wait_seconds}秒")

        poll_interval = 5  # 每5秒轮询一次
        elapsed_time = 0

        while elapsed_time < max_wait_seconds:
            try:
                pointcloud_info = pointcloud_svc.get_pointcloud(pointcloud_id)

                if not pointcloud_info:
                    logger.warning(f"[Agent] 点云信息不存在: {pointcloud_id}")
                    return None

                status = pointcloud_info.get("status")
                view_url = pointcloud_info.get("view_url")

                logger.debug(f"[Agent] 点云状态: {status}, view_url: {view_url}, 已等待: {elapsed_time}秒")

                if status == "completed" and view_url:
                    logger.info(f"[Agent] 点云生成完成，预览URL: {view_url}")
                    return view_url
                elif status == "failed":
                    error_msg = pointcloud_info.get("error_message", "未知错误")
                    logger.error(f"[Agent] 点云生成失败: {error_msg}")
                    return None

                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval

            except Exception as e:
                logger.error(f"[Agent] 监控点云状态异常: {e}", exc_info=True)
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval

        logger.warning(f"[Agent] 点云生成超时（{max_wait_seconds}秒），任务ID: {pointcloud_id}")
        return None

    async def _monitor_and_update_pointcloud(
        self,
        pointcloud_id: str,
        session_id: Optional[str] = None
    ) -> None:
        """
        后台监控点云生成并更新会话信息

        Args:
            pointcloud_id: 点云ID
            session_id: 会话ID（可选）
        """
        try:
            logger.info(f"[Agent] ========== 后台监控点云任务开始 ==========")
            logger.info(f"[Agent] 点云ID: {pointcloud_id}")
            logger.info(f"[Agent] 会话ID: {session_id}")

            # 监控点云生成状态
            logger.info(f"[Agent] 开始调用 _monitor_pointcloud_generation...")
            view_url = await self._monitor_pointcloud_generation(pointcloud_id)
            logger.info(f"[Agent] _monitor_pointcloud_generation 返回: {view_url}")

            if view_url:
                logger.info(f"[Agent] 点云生成成功，获取详细信息...")
                # 获取点云详细信息
                from ..services import get_pointcloud_service
                pointcloud_svc = get_pointcloud_service()
                pointcloud_info = pointcloud_svc.get_pointcloud(pointcloud_id)
                
                logger.info(f"[Agent] 点云信息: {pointcloud_info}")

                if pointcloud_info:
                    # 构造更新消息
                    update_message = (
                        f"\n\n✨ **3D点云生成完成！**\n\n"
                        f"📸 源图片ID: `{pointcloud_info.get('source_image_id')}`\n"
                        f"🎯 点云ID: `{pointcloud_id}`\n"
                        f"📊 点数: {pointcloud_info.get('point_count', 'N/A'):,}\n"
                        f"📁 文件大小: {pointcloud_info.get('file_size', 0) / 1024:.1f} KB\n"
                        f"🔗 **预览链接**: [{view_url}]({view_url})\n\n"
                        f"点击上方链接即可在浏览器中查看3D模型！"
                    )

                    # 更新会话历史
                    if session_id:
                        logger.info(f"[Agent] 更新会话历史...")
                        session = self.get_session(session_id)
                        if session:
                            # 添加系统更新消息
                            session["history"].append({
                                "role": "system",
                                "content": update_message,
                                "timestamp": datetime.now(),
                                "event": "pointcloud_completed",
                                "pointcloud_id": pointcloud_id,
                                "view_url": view_url
                            })
                            logger.info(f"[Agent] ✅ 会话已更新，点云完成事件已添加: {session_id}")
                        else:
                            logger.error(f"[Agent] ❌ 会话不存在: {session_id}")
                    else:
                        logger.warning(f"[Agent] ⚠️  会话ID为空，无法更新会话")
                else:
                    logger.error(f"[Agent] ❌ 无法获取点云信息: {pointcloud_id}")
            else:
                # 超时或失败
                logger.info(f"[Agent] ⚠️  点云生成未能在预期时间内完成: {pointcloud_id}")
            
            logger.info(f"[Agent] ========== 后台监控点云任务结束 ==========")

        except Exception as e:
            logger.error(f"[Agent] ❌ 后台监控点云任务异常: {e}", exc_info=True)

    def _extract_pointcloud_id_from_response(self, response: str) -> Optional[str]:
        """
        从Agent回复中提取点云ID

        Args:
            response: Agent生成的回复文本

        Returns:
            点云ID，如果未找到则返回None
        """
        import re

        # 按优先级匹配模式，先匹配带明确前缀的，最后才匹配纯UUID
        patterns = [
            r'点云ID[:\s]*([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
            r'pointcloud_id[:\s]*([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
            r'任务ID[:\s]*([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
        ]

        # 先匹配带明确前缀的ID
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                pointcloud_id = matches[0].lower()
                logger.info(f"[Agent] 从回复中提取到点云ID（带前缀）: {pointcloud_id}")
                return pointcloud_id

        # 如果没有找到带前缀的ID，则匹配纯UUID（但排除图片URL中的）
        # 匹配所有UUID
        uuid_pattern = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
        all_uuids = re.findall(uuid_pattern, response, re.IGNORECASE)
        
        if all_uuids:
            # 过滤掉在图片URL中出现的UUID
            for uuid_match in all_uuids:
                uuid_lower = uuid_match.lower()
                # 检查这个UUID是否出现在图片URL中
                if f'/api/v1/storage/images/{uuid_lower}' not in response.lower() and \
                   f'/storage/images/{uuid_lower}' not in response.lower():
                    pointcloud_id = uuid_lower
                    logger.info(f"[Agent] 从回复中提取到点云ID（纯UUID）: {pointcloud_id}")
                    return pointcloud_id

        return None

    def _detect_pointcloud_generation(self, query: str) -> bool:
        """
        检测用户请求是否为点云生成

        Args:
            query: 用户查询

        Returns:
            是否为点云生成请求
        """
        pointcloud_keywords = [
            "3d点云", "3d模型", "点云生成", "生成3d", "转成3d", "制作3d",
            "3d效果", "点云模型", "三维", "立体", "3d预览"
        ]

        query_lower = query.lower()
        return any(keyword in query_lower for keyword in pointcloud_keywords)

    def _extract_images_from_response(self, response: str, query: str = "") -> List[Dict[str, Any]]:
        """
        从 Agent 回复中提取图片信息
        
        支持以下格式：
        1. Markdown 格式: ![alt](url)
        2. API 路径: /api/v1/storage/images/{image_id}
        
        Args:
            response: Agent 生成的回复文本
            query: 用户原始查询（用于判断是否为点云生成场景）
            
        Returns:
            图片信息列表，每个包含 id, preview_url, score
        """
        import re
        images = []
        
        logger.debug(f"[Agent] 原始回复内容:\n{response}")
        
        # 检查是否为点云生成场景
        is_pointcloud_generation = self._detect_pointcloud_generation(query)
        
        # 匹配 Markdown 图片格式: ![alt](url)
        # 使用 re.DOTALL 匹配多行
        markdown_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = re.findall(markdown_pattern, response, re.DOTALL)
        
        logger.debug(f"[Agent] 正则匹配到 {len(matches)} 个 Markdown 图片")
        for i, (alt_text, url) in enumerate(matches, 1):
            logger.debug(f"[Agent] 图片 {i}: alt='{alt_text}', url='{url}'")
            
            # 提取图片 ID
            if "/api/v1/storage/images/" in url:
                image_id = url.split("/")[-1]
                
                # 如果是点云生成场景，验证ID是否为真实图片ID
                if is_pointcloud_generation:
                    # 尝试从存储服务验证图片是否存在
                    try:
                        from ..services import get_storage_service
                        storage_svc = get_storage_service()
                        if storage_svc.is_initialized:
                            image_info = storage_svc.get_image_info(image_id)
                            if not image_info:
                                logger.info(f"[Agent] 在点云生成场景中，排除非图片ID: {image_id}")
                                continue
                    except Exception as e:
                        logger.warning(f"[Agent] 验证图片信息失败: {e}")
                
                # 尝试从存储服务获取完整的图片信息
                try:
                    from ..services import get_storage_service
                    storage_svc = get_storage_service()
                    if storage_svc.is_initialized:
                        image_info = storage_svc.get_image_info(image_id)
                        if image_info:
                            logger.debug(f"[Agent] 成功获取图片信息: {image_id}")
                            images.append({
                                "id": image_id,
                                "preview_url": url,
                                "alt_text": alt_text,
                                "score": 1.0,
                                "metadata": image_info
                            })
                            continue
                except Exception as e:
                    logger.warning(f"[Agent] 获取图片信息失败: {e}")
                
                # 降级：只返回基本信息
                logger.debug(f"[Agent] 使用降级模式返回图片: {image_id}")
                images.append({
                    "id": image_id,
                    "preview_url": url,
                    "alt_text": alt_text,
                    "score": 1.0,
                    "metadata": None
                })
        
        logger.info(f"[Agent] 从回复中提取到 {len(images)} 张图片")
        return images

    def _extract_recommendation_from_response(
        self,
        response: str,
        context_images: Optional[List[Dict[str, Any]]] = None,
        is_pointcloud_generation: bool = False
    ) -> Dict[str, Any]:
        """
        从 Agent 回复中提取图片推荐信息
        
        支持以下格式：
        1. 文本中明确提到"第X张照片（ID: xxx）"
        2. 文本中提到"图片ID: xxx"
        3. 直接在上下文中获取图片ID列表
        
        Args:
            response: Agent 生成的回复文本
            context_images: 上下文中的图片列表（降级使用）
            is_pointcloud_generation: 是否为点云生成场景
            
        Returns:
            推荐信息字典，包含 recommended_image_id, alternative_image_ids, 
            recommendation_reason, total_images_analyzed
        """
        import re
        
        logger.info(f"[Agent] 开始解析推荐信息...")
        logger.debug(f"[Agent] 回复内容:\n{response}")
        
        # 初始化结果
        recommendation = {
            "recommended_image_id": None,
            "alternative_image_ids": [],
            "recommendation_reason": response,
            "total_images_analyzed": 0,
            "user_prompt_for_deletion": False
        }
        
        # 点云生成场景下，不进行推荐提取
        if is_pointcloud_generation:
            logger.info(f"[Agent] 点云生成场景，跳过推荐提取")
            return recommendation
        
        # 方法1: 从文本中提取所有图片ID（UUID格式）
        uuid_pattern = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
        all_image_ids = re.findall(uuid_pattern, response, re.IGNORECASE)
        all_image_ids = list(set(all_image_ids))  # 去重
        
        logger.info(f"[Agent] 从回复中提取到 {len(all_image_ids)} 个图片ID: {all_image_ids}")
        
        # 方法2: 尝试识别推荐的图片ID
        # 匹配"第X张照片（ID: xxx）"或"图片ID: xxx"等模式
        recommend_patterns = [
            r'(?:第[一二三四五六七八九十\d]+张照片|推荐.*照片|最佳.*照片).*?ID[:：]\s*([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
            r'(?:推荐|最佳).*?ID[:：]\s*([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
            r'ID[:：]\s*([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}).*?(?:推荐|最佳)',
        ]
        
        recommended_id = None
        for pattern in recommend_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                recommended_id = match.group(1)
                logger.info(f"[Agent] 识别到推荐图片ID: {recommended_id}")
                break
        
        # 方法3: 如果没有从文本中识别，尝试从上下文获取
        if not all_image_ids and context_images:
            all_image_ids = [img.get("id") for img in context_images if img.get("id")]
            logger.info(f"[Agent] 从上下文获取图片ID: {all_image_ids}")
        
        # 更新推荐信息
        if all_image_ids:
            recommendation["total_images_analyzed"] = len(all_image_ids)
            
            if recommended_id:
                recommendation["recommended_image_id"] = recommended_id
                # 其他图片ID作为备选
                recommendation["alternative_image_ids"] = [
                    img_id for img_id in all_image_ids if img_id != recommended_id
                ]
                recommendation["user_prompt_for_deletion"] = len(recommendation["alternative_image_ids"]) > 0
            else:
                # 没有明确的推荐，使用第一个ID作为推荐
                if len(all_image_ids) > 1:
                    recommendation["recommended_image_id"] = all_image_ids[0]
                    recommendation["alternative_image_ids"] = all_image_ids[1:]
                    recommendation["user_prompt_for_deletion"] = True
                elif len(all_image_ids) == 1:
                    recommendation["recommended_image_id"] = all_image_ids[0]
                    recommendation["alternative_image_ids"] = []
                    recommendation["user_prompt_for_deletion"] = False
        
        logger.info(
            f"[Agent] 推荐解析完成: "
            f"推荐ID={recommendation['recommended_image_id']}, "
            f"备选ID数量={len(recommendation['alternative_image_ids'])}, "
            f"总图片数={recommendation['total_images_analyzed']}"
        )
        
        return recommendation

    def optimize_query(self, user_query: str, session_id: Optional[str] = None) -> str:
        """
        查询优化：将自然语言转换为更精确的搜索语义
        (保留原有接口兼容性)
        """
        logger.info(f"查询优化: '{user_query}'")

        # 如果Agent可用，可使用Agent进行改写
        # if self._agent: ...

        optimized_query = user_query
        return optimized_query

    def detect_intent(self, user_query: str) -> Dict[str, Any]:
        """
        意图识别：判断用户想做什么
        (保留原有接口兼容性)
        """
        logger.info(f"意图识别: '{user_query}'")

        query_lower = user_query.lower()

        # 删除意图
        if any(kw in query_lower for kw in ["删除", "删掉", "remove", "delete"]):
            return {"intent": "delete", "confidence": 0.8, "entities": {}}

        # 上传意图
        if any(kw in query_lower for kw in ["上传", "添加", "upload", "add"]):
            return {"intent": "upload", "confidence": 0.8, "entities": {}}

        # 分析意图
        if any(kw in query_lower for kw in ["分析", "识别", "这是什么", "analyze"]):
            return {"intent": "analyze", "confidence": 0.7, "entities": {}}

        # 默认为普通聊天意图，而非搜索
        return {"intent": "chat", "confidence": 0.9, "entities": {}}

    def generate_response(
        self,
        intent: str,
        results: Any,
        user_query: str
    ) -> str:
        """
        生成自然语言回复
        (保留原有接口兼容性)
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

        elif intent == "chat":
            return "我是智慧相册助手，有什么可以帮您？我可以帮您搜索图片、管理相册。"

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
        (保留原有接口兼容性)
        """
        suggestions = []
        if intent == "search":
            if isinstance(results, dict):
                total = results.get("total", 0)
                if total == 0:
                    suggestions = ["换个描述试试", "查看所有照片", "按日期筛选"]
                elif total > 10:
                    suggestions = ["添加更多细节缩小范围", "按标签过滤", "查看相似图片"]
                else:
                    suggestions = ["查找相似的照片", "这些照片是什么时候拍的", "给这些照片打标签"]
        return suggestions


# 全局服务实例
_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """获取Agent服务实例"""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
