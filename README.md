# 智慧相册后端系统 (Smart Album Backend)

基于语义检索的智能图片管理系统，支持多模态Embedding生成、语义化图片检索、以图搜图等功能。

## 核心特性

- **多模态Embedding生成**: 支持文本、图片、图文混合输入的向量表示生成
- **语义化图片检索**: 通过自然语言描述搜索图片（如「日落时的海滩」）
- **以图搜图**: 查找视觉相似的图片
- **异步索引**: 上传图片后台生成Embedding，响应速度提升10倍
- **智能设备选择**: 自动选择最优推理设备（CUDA > MPS > CPU）
- **存储索引一致性**: 统一ID管理，确保文件与向量数据库同步
- **AI Agent集成**: 为openjiuwen等框架预留标准化接口

## 技术架构

```
ImgEmbedding2VecDB/
├── app/                      # 后端API服务
│   ├── main.py              # FastAPI主应用入口
│   ├── config.py            # 配置管理
│   ├── models/              # Pydantic数据模型
│   ├── services/            # 业务服务层
│   │   ├── embedding_service.py    # Embedding生成
│   │   ├── vector_db_service.py    # 向量数据库操作
│   │   ├── storage_service.py      # 图片存储管理
│   │   ├── search_service.py       # 搜索服务
│   │   └── agent_service.py        # Agent智能体逻辑
│   └── routers/             # API路由
│       ├── embedding.py     # Embedding接口
│       ├── vector_db.py     # 向量数据库接口
│       ├── storage.py       # 存储接口
│       ├── search.py        # 搜索接口
│       └── agent.py         # Agent聊天接口
├── qwen3-vl-embedding-2B/   # 多模态Embedding模型
├── storage/                 # 图片存储目录
├── qdrant_data/             # Qdrant本地数据
└── requirements.txt
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置模型路径

系统会自动查找项目根目录下的 `qwen3-vl-embedding-2B/` 模型，无需额外配置。

**如果模型在其他位置**，通过以下任一方式指定：

#### 方式1：环境变量（推荐）
```bash
export MODEL_PATH=/path/to/your/qwen3-vl-embedding-2B
uvicorn app.main:app --reload
```

#### 方式2：.env 文件
```bash
# 项目根目录创建 .env 文件
echo "MODEL_PATH=/path/to/your/qwen3-vl-embedding-2B" > .env
```

#### 方式3：创建软链接
```bash
# 将模型链接到项目目录（适合模型在其他盘符）
ln -s /path/to/your/qwen3-vl-embedding-2B ./qwen3-vl-embedding-2B
```

**模型目录结构示例：**
```
qwen3-vl-embedding-2B/
├── config.json
├── model.safetensors（或 .bin）
├── tokenizer_config.json
├── preprocessor_config.json
└── scripts/
    ├── qwen3_vl_embedding.py
    └── chat_template.jinja
```

### 3. 启动服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**启动日志示例：**
```
INFO - ==================================================
INFO - 智慧相册后端系统启动中...
INFO - ==================================================
INFO - 初始化存储服务...
INFO - 初始化向量数据库服务...
INFO - 初始化Embedding服务...
INFO - 正在初始化Embedding模型: ./qwen3-vl-embedding-2B
INFO - 使用CUDA设备进行推理  # 或 MPS / CPU
INFO - Embedding模型初始化完成
INFO - 所有服务初始化完成!
```

### 4. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API接口说明

### Embedding服务 (`/api/v1/embedding`)

| 接口         | 方法 | 说明                                   |
| ------------ | ---- | -------------------------------------- |
| `/generate`  | POST | 生成多模态Embedding向量                |
| `/text`      | POST | 快捷：纯文本Embedding                  |
| `/image`     | POST | 快捷：图片Embedding（支持URL自动存储） |
| `/dimension` | GET  | 获取向量维度                           |

**`/image` 参数说明：**
```python
image_url: str           # 图片URL
auto_store: bool = False # 是否下载并存储图片
auto_index: bool = False # 是否自动索引到向量库（需auto_store=True）
tags: str = None         # 标签，逗号分隔
```

**使用场景：**
```bash
# 场景1：仅生成Embedding（不存储）
curl "http://localhost:8000/api/v1/embedding/image?image_url=https://example.com/img.png"

# 场景2：下载+存储+索引（一步到位）
curl "http://localhost:8000/api/v1/embedding/image?image_url=https://example.com/img.png&auto_store=true&auto_index=true&tags=风景"
```

### 向量数据库 (`/api/v1/vectors`)

| 接口                    | 方法   | 说明              |
| ----------------------- | ------ | ----------------- |
| `/upsert`               | POST   | 插入/更新向量记录 |
| `/upsert/batch`         | POST   | 批量插入/更新     |
| `/{vector_id}`          | GET    | 获取向量记录      |
| `/{vector_id}`          | DELETE | 删除向量记录      |
| `/{vector_id}/metadata` | PATCH  | 更新元数据        |
| `/`                     | GET    | 列出向量记录      |
| `/stats/info`           | GET    | 集合统计信息      |

### 智能搜索 (`/api/v1/search`)

| 接口                | 方法 | 说明             |
| ------------------- | ---- | ---------------- |
| `/`                 | POST | 统一搜索接口     |
| `/text`             | GET  | 文本语义搜索     |
| `/image/{image_id}` | GET  | 以图搜图（按ID） |
| `/image`            | POST | 上传图片搜索     |
| `/hybrid`           | POST | 图文混合搜索     |

**示例请求:**
```json
POST /api/v1/search/
{
  "query_text": "日落时的海滩",
  "top_k": 10,
  "score_threshold": 0.5
}
```

### 图片存储 (`/api/v1/storage`)

| 接口                      | 方法   | 说明                           |
| ------------------------- | ------ | ------------------------------ |
| `/upload`                 | POST   | 上传图片（支持异步/同步索引）  |
| `/upload/batch`           | POST   | 批量上传                       |
| `/images/{image_id}`      | GET    | 获取图片文件                   |
| `/images/{image_id}/info` | GET    | 获取图片信息                   |
| `/images/{image_id}`      | DELETE | 删除图片（同步清理向量数据库） |
| `/images`                 | GET    | 列出图片                       |
| `/index/{image_id}`       | POST   | 手动索引单张图片               |
| `/index/all`              | POST   | 批量索引所有未索引图片         |

**上传参数说明：**
```python
auto_index: bool = True      # 是否自动索引
async_index: bool = True     # 是否异步索引（推荐）
tags: str = "风景,海滩"      # 标签，逗号分隔
description: str = "..."     # 图片描述
```

**性能对比：**
- 异步模式：~200ms 响应，后台处理
- 同步模式：~2-5s 响应，立即可搜索

### Agent智能体 (`/api/v1/agent`)

| 接口              | 方法 | 说明                     |
| ----------------- | ---- | ------------------------ |
| `/chat`           | POST | 智能聊天接口（主要入口） |
| `/session/create` | POST | 创建新会话               |
| `/session/{id}`   | GET  | 获取会话信息             |
| `/actions`        | GET  | 获取可用动作列表         |
| `/execute`        | POST | 执行Agent动作（高级）    |
| `/status`         | GET  | 获取系统状态             |

**聊天接口示例：**
```bash
# 第一次对话
curl -X POST "http://localhost:8000/api/v1/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "我昨天拍的小狗照片",
    "top_k": 5
  }'

# 响应：
{
  "session_id": "a1b2c3d4-...",
  "answer": "为您找到了 3 张相关照片。",
  "intent": "search",
  "optimized_query": "昨天拍的小狗照片",
  "results": {
    "total": 3,
    "images": [...]
  },
  "suggestions": [
    "查找相似的照片",
    "这些照片是什么时候拍的"
  ]
}

# 多轮对话（带上session_id）
curl -X POST "http://localhost:8000/api/v1/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "第一张是在哪拍的",
    "session_id": "a1b2c3d4-..."
  }'
```

**功能特点：**
- ✅ 自然语言理解：识别用户意图（搜索/上传/删除）
- ✅ 查询优化：将口语化描述转为精确语义（预留LLM集成）
- ✅ 自动工具调用：根据意图调用后端服务
- ✅ 对话式响应：生成自然语言回复
- ✅ 后续建议：智能推荐下一步操作
- ✅ 多轮对话：支持上下文记忆

## 配置说明

可通过环境变量或 `.env` 文件配置：

| 配置项             | 默认值                    | 说明                           |
| ------------------ | ------------------------- | ------------------------------ |
| `MODEL_PATH`       | `./qwen3-vl-embedding-2B` | Embedding模型路径              |
| `QDRANT_MODE`      | `local`                   | Qdrant模式：local/docker/cloud |
| `QDRANT_HOST`      | `localhost`               | Qdrant主机（docker/cloud模式） |
| `QDRANT_PORT`      | `6333`                    | Qdrant端口                     |
| `QDRANT_PATH`      | `./qdrant_data`           | 本地存储路径（local模式）      |
| `STORAGE_PATH`     | `./storage/images`        | 图片存储路径                   |
| `VECTOR_DIMENSION` | `2048`                    | 向量维度                       |

## Docker部署

切换到Docker模式部署Qdrant：

```bash
# 启动Qdrant容器
docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# 设置环境变量
export QDRANT_MODE=docker
export QDRANT_HOST=localhost
export QDRANT_PORT=6333

# 启动应用
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 使用示例

### Python客户端示例

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. 使用Agent聊天接口（推荐）
response = requests.post(
    f"{BASE_URL}/agent/chat",
    json={
        "query": "我想找一些海边的照片",
        "top_k": 5
    }
).json()
print(response["answer"])  # "为您找到了 3 张相关照片。"
print(response["results"])  # 搜索结果

# 2. 直接调用底层API（适合管理/调试）
# 上传图片
with open("photo.jpg", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/storage/upload",
        files={"file": f},
        data={"auto_index": True, "tags": "风景,海滩"}
    )
    image_id = response.json()["data"]["id"]

# 文本搜索
results = requests.get(
    f"{BASE_URL}/search/text",
    params={"query": "蓝天白云", "top_k": 5}
).json()["data"]

# 以图搜图
similar = requests.get(
    f"{BASE_URL}/search/image/{image_id}",
    params={"top_k": 10}
).json()["data"]

# 从URL下载并索引图片
result = requests.post(
    f"{BASE_URL}/embedding/image",
    params={
        "image_url": "https://example.com/photo.jpg",
        "auto_store": True,
        "auto_index": True,
        "tags": "风景"
    }
).json()
stored_id = result.get("stored_image_id")
```

### cURL示例

```bash
# Agent聊天接口
curl -X POST "http://localhost:8000/api/v1/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "我想找一些海边的照片", "top_k": 5}'

# 上传图片
curl -X POST "http://localhost:8000/api/v1/storage/upload" \
  -F "file=@photo.jpg" \
  -F "auto_index=true" \
  -F "tags=风景,海滩"

# 文本搜索
curl "http://localhost:8000/api/v1/search/text?query=蓝天白云&top_k=5"

# 获取系统状态
curl "http://localhost:8000/status"
```

## 前端集成指南

**推荐架构：前端只调用 `/agent/chat` 接口**

```javascript
// React 示例
const [messages, setMessages] = useState([]);
const [sessionId, setSessionId] = useState(null);

async function sendMessage(query) {
  const res = await fetch('/api/v1/agent/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ query, session_id: sessionId, top_k: 10 })
  });
  
  const data = await res.json();
  setSessionId(data.session_id);
  
  setMessages([...messages, {
    user: query,
    agent: data.answer,
    images: data.results?.images || [],
    suggestions: data.suggestions
  }]);
}
```

**为什么使用 Agent 接口？**
- ✅ 前端逐辑简单：只需一个聊天框
- ✅ 自然语言交互：用户体验好
- ✅ 后端灵活：内部服务可随意调整
- ✅ 易于扩展：加新功能不影响前端

**直接调用底层API的场景：**
- 管理后台：需要精细控制（`/storage`, `/vectors`）
- 文件上传：直接上传文件流（`/storage/upload`）
- API调试：开发阶段测试

## 系统要求

- Python 3.10+
- PyTorch 2.0+
- 推理设备（按优先级）：
  - NVIDIA GPU (CUDA) - 最快
  - Apple Silicon (MPS) - 次之
  - CPU - 可用但较慢
- 16GB+ 内存（加载模型）

## License

MIT License
