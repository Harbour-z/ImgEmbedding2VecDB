# 智慧相册Agent（Smart Album Agent）

本作品是一个面向“个人/企业相册管理”的多模态智能检索与对话系统：用户用自然语言描述“内容”和“约束”（例如日期/标签），Agent 自动选择合适的检索工具（元数据过滤/语义相似度/组合检索），并把命中的图片以缩略图形式直接回传到对话界面。

> 提交命名要求为：`队伍名称+Agent名称`。如需改名，请将本目录 `比赛提交/智慧相册队+智慧相册Agent/` 重命名为你的队伍名称与Agent名称。

## 1. Agent 应用场景

### 1.1 场景概述

传统相册检索主要依赖文件夹/时间线/手动标签；当用户只记得“画面语义”或“模糊线索”时（例如“海边日落”“有表格的截图”），检索成本高。本项目提供对话式入口：

- **语义检索**：描述画面内容即可找图
- **元数据检索**：按日期、标签等结构化字段筛选
- **组合检索**：同时包含日期与语义（如“1.18 海边”）时，先过滤再相似度排序

### 1.2 典型用户场景

1. **工作资料检索**：在聊天里输入“表格/报表/会议纪要”，快速找到截图或照片
2. **生活回忆检索**：输入“海边日落”“红色跑车”，从大量照片中定位目标
3. **按日期定位**：输入“1.18 的照片”或“2026-01-17 的照片”，直接按拍摄/上传时间筛选
4. **组合需求**：输入“1.18 海边”，要求日期约束 + 内容相似度联合检索

### 1.3 交互示例

- 用户：帮我找找相册里面关于表格的照片
- Agent：直接返回若干张图片缩略图（并给出必要的解释与建议）

## 2. Agent 技术方案

### 2.1 整体架构

```text
┌─────────────────────────────────────────────────────────────┐
│                         Web 前端（React）                     │
│  /chat 对话页：展示文本 + results.images 缩略图 + 建议问题     │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP (/api/v1)
┌───────────────────────────▼─────────────────────────────────┐
│                        FastAPI 后端（app/）                  │
│  /agent/chat：会话管理 + 工具路由 + 结果回传（含图片列表）     │
└───────────────┬───────────────────────────────┬─────────────┘
                │                               │
┌───────────────▼───────────────┐   ┌───────────▼─────────────┐
│  Embedding 服务（Qwen3-VL）     │   │   Storage 本地存储        │
│  文本/图片 -> 2048-d 向量       │   │   文件落盘 + 预览下载       │
└───────────────┬───────────────┘   └───────────┬─────────────┘
                │                               │
                └───────────────┬───────────────┘
                                ▼
                    ┌───────────────────────────┐
                    │      Qdrant 向量数据库     │
                    │  向量检索 + payload 过滤    │
                    │  payload: created_at/tags… │
                    └───────────────────────────┘
```

### 2.2 核心能力拆解

#### 2.2.1 双检索范式：语义 vs 元数据

图片的可用元数据（存储在 Qdrant payload 中）包括：

- `created_at`：创建/上传时间（ISO datetime）
- `tags`：标签列表
- `filename/file_size/width/height/format/description/extra` 等

Agent 会根据用户表达选择工具：

- **元数据检索**：当用户在“按日期/标签/文件名”等筛选条件下找图
- **语义检索**：当用户用自然语言描述画面内容，希望相似度排序

实现参考：

- 搜索服务：[search_service.py](file:///Users/harbour/Desktop/huawei-intern-2026/ImgEmbedding2VecDB/app/services/search_service.py)
- 向量库过滤（含 `created_at` DATETIME 索引、ID集合过滤）：[vector_db_service.py](file:///Users/harbour/Desktop/huawei-intern-2026/ImgEmbedding2VecDB/app/services/vector_db_service.py)

#### 2.2.2 组合检索：日期过滤 + 语义相似度

对“1.18 海边”这类混合表达，系统做两步：

1. 解析出 `date_text=1.18`，得到日期过滤条件（有年份则直接 DATETIME range，无年份则先扫描 payload 得到 ID 集合）
2. 对剩余文本 `query=海边` 做 embedding，并在过滤条件下做向量相似度排序

为了避免仅靠大模型拆参不稳定，服务端提供 `split_date_and_query()` 的正则兜底解析。

#### 2.2.3 对话式工具调用（Agent Orchestration）

系统同时支持两条链路：

- **OpenJiuwen ReActAgent**：用于更强的规划/工具调用能力
- **OpenAI Compatible Function Calling fallback**：当 ReActAgent 调用失败时，自动降级到 OpenAI 兼容接口完成工具调用

并在 `/agent/chat` 响应中统一回传 `results.images`，让前端直接渲染缩略图，而不是让用户手动复制 ID。

实现参考：

- Agent 服务：[agent_service.py](file:///Users/harbour/Desktop/huawei-intern-2026/ImgEmbedding2VecDB/app/services/agent_service.py)
- Agent API：[agent.py](file:///Users/harbour/Desktop/huawei-intern-2026/ImgEmbedding2VecDB/app/routers/agent.py)

### 2.3 数据流与一致性

#### 上传与索引

1. `/storage/upload`：图片落盘（`storage/images/...`），生成 `created_at` 与初始 metadata
2. Embedding 服务生成向量
3. 写入 Qdrant：向量 + payload(metadata)

#### 搜索

- 语义检索：`text -> embedding -> qdrant.query_points`
- 元数据检索：`payload filter (created_at/tags/ids) -> scroll/search`

### 2.4 工程化与鲁棒性

- **避免SSL误配置导致模型调用失败**：在Agent初始化阶段统一处理 `LLM_SSL_VERIFY/LLM_SSL_CERT`
- **避免OpenAI兼容接口400**：强校验 `OPENAI_MODEL_NAME`，并使用 `BaseModelInfo(model=...)` 确保请求携带 `model`
- **慢检索不误报“网络错误”**：前端聊天请求超时策略适配 embedding/向量检索耗时

## 3. 目录结构（提交说明）

本项目为前后端一体：

- 后端：`app/`（FastAPI + Embedding + Qdrant + Agent）
- 前端：`frontend/`（React + Vite + Ant Design）
- 模型：`qwen3-vl-embedding-2B/`（本地多模态 embedding）

更完整的运行方式请见项目根目录 [README.md](file:///Users/harbour/Desktop/huawei-intern-2026/ImgEmbedding2VecDB/README.md)。

