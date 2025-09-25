# FAISS Vector Search API

基于FAISS的向量搜索API，支持用户术语管理和相似度搜索。

## 功能特性

- 🔍 基于FAISS的高效向量相似度搜索
- 👤 多用户术语管理
- 🧠 BGE-Large-EN-v1.5预加载嵌入模型
- 💾 向量索引持久化
- 🔄 后台异步embedding构建
- 🛡️ 构建状态冲突保护

## 文件架构

```
extension_backend/
├── app/                          # 主应用目录
│   ├── __init__.py              # 应用包初始化
│   ├── main.py                  # FastAPI应用入口
│   ├── config.py                # 配置文件
│   └── dependencies.py          # 依赖注入
│
├── api/                         # API路由目录
│   ├── __init__.py
│   ├── routes/                  # 路由模块
│   │   ├── __init__.py
│   │   ├── documents.py         # 文档相关API
│   │   ├── search.py            # 搜索相关API
│   │   └── admin.py             # 管理相关API
│   └── middleware.py            # 中间件
│
├── db/                          # 数据库相关
│   ├── __init__.py
│   ├── database.py              # 数据库连接
│   ├── models.py                # 数据库模型
│   └── migrations/              # 数据库迁移文件
│
├── faiss_engine/                # FAISS向量引擎
│   ├── __init__.py
│   ├── vector_store.py          # 向量存储管理
│   ├── embeddings.py            # 文本嵌入服务
│   └── search_engine.py         # 搜索引擎
│
├── models/                      # Pydantic模型
│   ├── __init__.py
│   ├── schemas.py               # API请求/响应模型
│   └── base.py                  # 基础模型
│
├── services/                    # 业务逻辑服务
│   ├── __init__.py
│   ├── document_service.py      # 文档处理服务
│   ├── search_service.py        # 搜索服务
│   └── index_service.py         # 索引管理服务
│
├── venv/                        # 虚拟环境
├── .env                         # 环境变量配置
├── .gitignore                   # Git忽略文件
├── requirements.txt             # 项目依赖
└── main.py                      # 项目启动入口
```

## 快速开始

### 环境要求

- Python 3.8+
- MySQL 5.7+
- 预加载的BGE-Large-EN-v1.5模型文件（位于 `./models/bge-large-en-v1.5/`）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

创建 `.env` 文件：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=2069
DB_USER=rambo
DB_PASSWORD=Wx19971009.
DB_NAME=edge_extension_db

# 模型配置
MODEL_PATH=./models/bge-large-en-v1.5

# FAISS配置
FAISS_INDEX_PATH=./faiss_indexes
VECTOR_PERSISTENCE_ENABLED=true
AUTO_SAVE_INTERVAL=100
```

### 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API 文档

### 用户管理

#### 获取用户术语列表
```http
GET /users/{user_id}/terms
```

**响应示例：**
```json
{
  "terms": [
    {
      "term_id": 1,
      "en": "artificial intelligence",
      "cn": "人工智能",
      "jp": "人工知能",
      "created_at": "2024-01-01T10:00:00"
    }
  ]
}
```

#### 添加术语
```http
POST /users/{user_id}/terms
Content-Type: application/json

{
  "en": "machine learning",
  "cn": "机器学习",
  "jp": "機械学習"
}
```

#### 删除术语（单个）
```http
DELETE /users/{user_id}/terms/{en}
```

#### 批量删除术语
```http
DELETE /users/{user_id}/terms
Content-Type: application/json

{
  "en_terms": ["term1", "term2", "term3"]
}
```

#### 获取用户术语状态
```http
GET /users/{user_id}/terms/status
```

**响应示例：**
```json
{
  "total_terms": 25
}
```

### Embedding 管理

#### 构建用户Embedding
```http
POST /embedding/build/user/{user_id}
```

**状态限制：**
- ✅ 允许构建：`completed`, `failed`, 无记录
- ❌ 禁止构建：`pending`, `building`

**响应示例：**
```json
{
  "message": "Embedding build task started",
  "user_id": 1,
  "status": "building"
}
```

**冲突响应（409）：**
```json
{
  "detail": "Embedding is already in progress. Current status: building"
}
```

#### 构建所有用户Embedding
```http
POST /embedding/build/all
```

**状态限制：**
- 检查所有用户的embedding状态
- 如果有任何用户状态为 `pending` 或 `building`，返回409冲突

**冲突响应（409）：**
```json
{
  "detail": "Embedding is already in progress for users: [1, 2]. Please wait for completion."
}
```

#### 获取用户Embedding状态
```http
GET /embedding/status/{user_id}
```

**响应示例：**
```json
{
  "user_id": 1,
  "embedding_status": "completed",
  "last_embedding_time": "2024-01-01T10:30:00"
}
```

**状态说明：**
- `pending`: 待构建
- `building`: 构建中
- `completed`: 构建完成
- `failed`: 构建失败

#### 更新用户Embedding状态
```http
PUT /embedding/status/{user_id}
Content-Type: application/json

{
  "embedding_status": "completed",
  "last_embedding_time": "2024-01-01T10:30:00"
}
```

#### 搜索相似术语
```http
GET /embedding/search?query=artificial intelligence&top_k=5&threshold=0.7
```

**参数说明：**
- `query`: 搜索查询文本
- `top_k`: 返回结果数量（默认5）
- `threshold`: 相似度阈值（默认0.7）

**响应示例：**
```json
{
  "query": "artificial intelligence",
  "results": [
    {
      "term_id": 1,
      "similarity_score": 0.95
    }
  ],
  "total_results": 1
}
```

#### 获取Embedding统计信息
```http
GET /embedding/stats
```

**响应示例：**
```json
{
  "total_terms": 100,
  "index_size": 100,
  "index_type": "IndexFlatIP",
  "embedding_dim": 1024
}
```

## 数据库结构

### users 表
```sql
CREATE TABLE users (
  user_id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### terms 表
```sql
CREATE TABLE terms (
  term_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  en VARCHAR(255) NOT NULL,
  cn VARCHAR(255),
  jp VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

### embedding 表
```sql
CREATE TABLE embedding (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  embedding_status VARCHAR(20) NOT NULL DEFAULT 'pending',
  last_embedding_time DATETIME NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

## 离线模式配置

### 模型下载
```bash
# 下载BGE-M3模型到本地
python -c "
from FlagEmbedding import BGEM3FlagModel
model = BGEM3FlagModel('BAAI/bge-m3', cache_folder='./model_cache')
"
```

### 环境变量设置
```bash
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
export HF_ENDPOINT=https://hf-mirror.com
```

## 向量持久化

FAISS索引会自动保存到 `./faiss_indexes` 目录：

- `index.faiss`: FAISS索引文件
- `metadata.pkl`: 术语元数据
- `term_id_map.pkl`: 术语ID映射

### 自动保存配置
- `AUTO_SAVE_INTERVAL`: 每N次操作自动保存（默认100）
- `VECTOR_PERSISTENCE_ENABLED`: 启用持久化（默认true）

## 错误处理

### HTTP状态码
- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `409`: 状态冲突（embedding构建中）
- `500`: 服务器内部错误

### 常见错误
```json
{
  "detail": "User not found"
}
```

```json
{
  "detail": "Term not found"
}
```

```json
{
  "detail": "Embedding is already in progress. Current status: building"
}
```

## 开发指南

### 项目结构
```
extension_backend/
├── app/
│   ├── api/
│   │   └── router/
│   │       ├── user.py
│   │       └── embedding.py
│   ├── models/
│   │   ├── models.py
│   │   └── schemas.py
│   ├── services/
│   │   └── embedding_service.py
│   ├── db/
│   │   └── database.py
│   ├── config.py
│   └── main.py
├── faiss_engine/
│   ├── embeddings.py
│   └── vector_store.py
├── requirements.txt
└── README.md
```

### 添加新功能
1. 在 `app/models/` 中定义数据模型
2. 在 `app/models/schemas.py` 中定义API模式
3. 在 `app/services/` 中实现业务逻辑
4. 在 `app/api/router/` 中定义API路由
5. 在 `app/main.py` 中注册路由

## 测试

### 运行测试
```bash
# 测试embedding构建限制
python test_building_restriction.py

# 测试API功能
python -m pytest tests/
```

### 健康检查
```http
GET /health
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
