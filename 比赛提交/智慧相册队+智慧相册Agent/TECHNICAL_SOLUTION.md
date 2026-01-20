# 智慧相册Agent 技术方案（Detailed）

本文档面向评审与开发者，给出系统的详细技术设计：核心模块划分、数据流、Agent 工具协议、关键实现细节与可运行说明。

## 1. 技术选型

| 领域 | 选型 | 说明 |
|---|---|---|
| 后端框架 | FastAPI | 异步高性能、OpenAPI 自动生成 |
| 向量数据库 | Qdrant | 本地/容器可切换；支持 payload 过滤与索引 |
| Embedding | Qwen3-VL embedding (本地) | 文本/图片/图文多模态 embedding，2048 维 |
| Agent 框架 | OpenJiuwen ReActAgent + OpenAI Compatible fallback | ReAct 做规划；fallback 保证可用性 |
| 前端 | React + Vite + Ant Design + Zustand | 单页应用；聊天/画廊/上传 |

## 2. 模块划分与职责

```text
app/
  main.py                应用启动与生命周期；初始化各服务
  config.py              Settings(.env)；路径与参数配置
  routers/               HTTP API 路由层
    agent.py             /agent/chat 等接口，统一对话入口
    search.py            /search/text 等检索接口
    storage.py           /storage/upload 等存储接口
    embedding.py         /embedding/* embedding 生成接口
    vector_db.py         /vectors/* 向量与元数据管理接口
  services/              业务服务层
    agent_service.py     Agent（ReAct + fallback）、工具调用、会话管理
    search_service.py    语义检索/元数据检索/组合检索
    vector_db_service.py Qdrant client 封装（search/scroll/filter/index）
    storage_service.py   文件存储、图片信息、索引触发
    embedding_service.py 本地模型加载与向量生成

frontend/
  src/pages/ChatPage.tsx  对话页：渲染文本 + results.images
  src/store/chatStore.ts  对话状态与调用 /agent/chat
  src/api/*               Axios client + API 模块
```

## 3. Agent 设计

### 3.1 可用工具（Tooling）

Agent 通过工具把自然语言转换为“可执行的检索动作”。当前工具集：

- `semantic_search_images(query, top_k)`：语义相似度检索
- `meta_search_images(date_text?, query?, tags?, top_k)`：元数据检索或组合检索
- `get_photo_meta_schema()`：返回可用 metadata 字段说明
- `get_current_time()`：时间查询

其中组合检索约定：当用户混合表达（例如 `1.18 海边`）时，传入 `date_text=1.18` 与 `query=海边`。

### 3.2 组合检索的“兜底解析”

为了避免仅依赖大模型拆参导致不稳定，服务端实现 `split_date_and_query(text)`：

- 从任意 query 中提取 `YYYY-MM-DD` / `M.D` / `M月D日` 片段
- 剩余文本作为语义 query

这样即便模型误选工具或参数未拆分，服务端仍能稳定命中组合检索路径。

### 3.3 结果回传到对话前端

对话接口 `/api/v1/agent/chat` 的响应里包含：

```json
{
  "session_id": "...",
  "answer": "...",
  "results": {
    "total": 3,
    "images": [
      {"id": "...", "score": 0.29, "metadata": {...}, "preview_url": "/api/v1/storage/images/..."}
    ]
  }
}
```

前端 ChatPage 只要拿到 `results.images` 即可展示缩略图。

### 3.4 ReAct Agent 与 fallback 的一致性

- ReActAgent 工具调用（OpenJiuwen）会通过工具函数 `search_tool()` 获取命中结果。
- 为了让 API 层能拿到“工具调用产生的图片列表”，后端使用 `ContextVar` 将当前会话与工具执行绑定，并缓存本轮 `images`，由 `/agent/chat` 统一回传。
- 当 ReActAgent 调用失败，会自动降级到 OpenAI-compatible function calling；此路径同样会收集工具返回的图片并回传。

## 4. 向量检索与元数据

### 4.1 Metadata 存储

图片的结构化信息作为 Qdrant payload 存储：

- `created_at`：datetime（写入时转为 ISO string）
- `tags`：keyword list（可过滤）
- `filename/width/height/...`：用于展示或筛选

Qdrant collection 初始化时建立 payload index：

- `tags`：KEYWORD
- `created_at`：DATETIME

### 4.2 过滤能力

- `created_at` 范围过滤：DATETIME range
- `tags` 过滤：MatchAny
- `ids` 集合过滤：HasIdCondition（用于“无年份日期”的组合检索）

## 5. API 说明（关键端点）

- `POST /api/v1/agent/chat`：对话入口（推荐前端只接这个）
- `GET /api/v1/search/text`：纯语义搜索（调试/开发）
- `POST /api/v1/storage/upload`：上传并索引
- `GET /api/v1/storage/images/{id}`：图片预览

详细参数以 Swagger 为准：`http://localhost:8000/docs`

## 6. 可运行性与环境配置

### 6.1 必要环境变量

- `MODEL_PATH`：本地 Qwen3-VL embedding 模型目录
- `OPENAI_API_KEY/OPENAI_BASE_URL/OPENAI_MODEL_NAME`：启用 Agent（ReAct/fallback）时需要
- `QDRANT_MODE=local`：默认本地落盘

模板见项目根目录 `.env.template`。

### 6.2 启动方式

- 后端：`uvicorn app.main:create_app --reload --host 0.0.0.0 --port 8000`
- 前端：`cd frontend && npm i && npm run dev`

## 7. 可扩展点

- 引入更强的意图识别（多轮记忆 + 结构化槽位抽取）
- 更丰富的元数据字段（EXIF 时间/地点/设备），并完善 payload 索引
- 结果卡片化：在聊天中展示“可操作卡片”（查看/删除/打标签/分享）

