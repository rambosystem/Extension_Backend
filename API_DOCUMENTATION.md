# API 文档

## 概述

FAISS Vector Search API 提供基于向量相似度的术语搜索和管理功能。

**Base URL:** `http://localhost:8000`

## 认证

目前API不需要认证，所有接口都是公开的。

## 通用响应格式

### 成功响应
```json
{
  "message": "操作成功",
  "data": {...}
}
```

### 错误响应
```json
{
  "detail": "错误描述"
}
```

## 用户管理 API

### 1. 获取用户术语列表

**接口:** `GET /users/{user_id}/terms`

**描述:** 获取指定用户的所有术语，按term_id倒序排列（最新添加的在前面）

**路径参数:**
- `user_id` (integer, required): 用户ID

**响应示例:**
```json
{
  "terms": [
    {
      "term_id": 3,
      "en": "machine learning",
      "cn": "机器学习",
      "jp": "機械学習",
      "created_at": "2024-01-01T10:00:00"
    },
    {
      "term_id": 2,
      "en": "artificial intelligence",
      "cn": "人工智能",
      "jp": "人工知能",
      "created_at": "2024-01-01T09:00:00"
    }
  ]
}
```

**错误响应:**
- `404`: 用户不存在

### 2. 添加术语

**接口:** `POST /users/{user_id}/terms`

**描述:** 为用户添加新的术语

**路径参数:**
- `user_id` (integer, required): 用户ID

**请求体:**
```json
{
  "en": "deep learning",
  "cn": "深度学习",
  "jp": "ディープラーニング"
}
```

**字段说明:**
- `en` (string, required): 英文术语
- `cn` (string, optional): 中文术语
- `jp` (string, optional): 日文术语

**响应示例:**
```json
{
  "term_id": 4,
  "en": "deep learning",
  "cn": "深度学习",
  "jp": "ディープラーニング",
  "created_at": "2024-01-01T11:00:00"
}
```

**错误响应:**
- `404`: 用户不存在
- `400`: 请求参数错误

### 3. 删除单个术语

**接口:** `DELETE /users/{user_id}/terms/{en}`

**描述:** 根据英文术语删除指定用户的术语

**路径参数:**
- `user_id` (integer, required): 用户ID
- `en` (string, required): 英文术语

**响应示例:**
```json
{
  "message": "Term deleted successfully",
  "deleted_term": "machine learning"
}
```

**错误响应:**
- `404`: 用户或术语不存在

### 4. 批量删除术语

**接口:** `DELETE /users/{user_id}/terms`

**描述:** 批量删除指定用户的多个术语

**路径参数:**
- `user_id` (integer, required): 用户ID

**请求体:**
```json
{
  "en_terms": ["term1", "term2", "term3"]
}
```

**字段说明:**
- `en_terms` (array, required): 要删除的英文术语列表

**响应示例:**
```json
{
  "message": "Terms deleted successfully",
  "deleted_count": 3
}
```

**错误响应:**
- `404`: 用户不存在
- `400`: 请求参数错误

### 5. 获取用户术语状态

**接口:** `GET /users/{user_id}/terms/status`

**描述:** 获取用户的术语统计信息

**路径参数:**
- `user_id` (integer, required): 用户ID

**响应示例:**
```json
{
  "total_terms": 25
}
```

**错误响应:**
- `404`: 用户不存在

## Embedding 管理 API

### 1. 构建用户Embedding

**接口:** `POST /embedding/build/user/{user_id}`

**描述:** 为指定用户构建embedding向量（后台异步任务）

**路径参数:**
- `user_id` (integer, required): 用户ID

**状态限制:**
- ✅ **允许构建:** `completed`, `failed`, 无记录
- ❌ **禁止构建:** `pending`, `building`

**成功响应示例:**
```json
{
  "message": "Embedding build task started",
  "user_id": 1,
  "status": "building"
}
```

**冲突响应 (409):**
```json
{
  "detail": "Embedding is already in progress. Current status: building"
}
```

**错误响应:**
- `404`: 用户不存在
- `409`: 构建任务已在进行中
- `500`: 服务器内部错误

### 2. 构建所有用户Embedding

**接口:** `POST /embedding/build/all`

**描述:** 为所有用户构建embedding向量（后台异步任务）

**状态限制:**
- 检查所有用户的embedding状态
- 如果有任何用户状态为 `pending` 或 `building`，返回409冲突

**成功响应示例:**
```json
{
  "message": "Embedding build task started for all users",
  "status": "building"
}
```

**冲突响应 (409):**
```json
{
  "detail": "Embedding is already in progress for users: [1, 2]. Please wait for completion."
}
```

**错误响应:**
- `409`: 有用户正在构建中
- `500`: 服务器内部错误

### 3. 获取用户Embedding状态

**接口:** `GET /embedding/status/{user_id}`

**描述:** 获取指定用户的embedding构建状态

**路径参数:**
- `user_id` (integer, required): 用户ID

**响应示例:**
```json
{
  "user_id": 1,
  "embedding_status": "completed",
  "last_embedding_time": "2024-01-01T10:30:00"
}
```

**状态说明:**
- `pending`: 待构建
- `building`: 构建中
- `completed`: 构建完成
- `failed`: 构建失败

**错误响应:**
- `500`: 服务器内部错误

### 4. 更新用户Embedding状态

**接口:** `PUT /embedding/status/{user_id}`

**描述:** 手动更新指定用户的embedding状态

**路径参数:**
- `user_id` (integer, required): 用户ID

**请求体:**
```json
{
  "embedding_status": "completed",
  "last_embedding_time": "2024-01-01T10:30:00"
}
```

**字段说明:**
- `embedding_status` (string, required): 状态值
- `last_embedding_time` (datetime, optional): 最后构建时间

**响应示例:**
```json
{
  "user_id": 1,
  "embedding_status": "completed",
  "last_embedding_time": "2024-01-01T10:30:00"
}
```

**错误响应:**
- `500`: 服务器内部错误

### 5. 搜索相似术语

**接口:** `GET /embedding/search`

**描述:** 基于向量相似度搜索相似术语

**查询参数:**
- `query` (string, required): 搜索查询文本
- `top_k` (integer, optional, default: 5): 返回结果数量
- `threshold` (float, optional, default: 0.7): 相似度阈值

**请求示例:**
```http
GET /embedding/search?query=artificial intelligence&top_k=10&threshold=0.8
```

**响应示例:**
```json
{
  "query": "artificial intelligence",
  "results": [
    {
      "term_id": 1,
      "similarity_score": 0.95
    },
    {
      "term_id": 2,
      "similarity_score": 0.87
    }
  ],
  "total_results": 2
}
```

**错误响应:**
- `400`: 查询参数错误
- `500`: 搜索失败

### 6. 获取Embedding统计信息

**接口:** `GET /embedding/stats`

**描述:** 获取embedding系统的统计信息

**响应示例:**
```json
{
  "total_terms": 100,
  "index_size": 100,
  "index_type": "IndexFlatIP",
  "embedding_dim": 1024
}
```

**字段说明:**
- `total_terms`: 总术语数量
- `index_size`: 索引大小
- `index_type`: 索引类型
- `embedding_dim`: 向量维度

**错误响应:**
- `500`: 获取统计信息失败

## 系统 API

### 1. 健康检查

**接口:** `GET /health`

**描述:** 检查API服务状态

**响应示例:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T10:00:00"
}
```

### 2. 根路径

**接口:** `GET /`

**描述:** API根路径，返回基本信息

**响应示例:**
```json
{
  "message": "FAISS Vector Search API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

## 状态码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 409 | 状态冲突（如embedding构建中） |
| 422 | 请求数据验证失败 |
| 500 | 服务器内部错误 |

## 数据模型

### TermCreate
```json
{
  "en": "string",
  "cn": "string | null",
  "jp": "string | null"
}
```

### TermResponse
```json
{
  "term_id": "integer",
  "en": "string",
  "cn": "string | null",
  "jp": "string | null",
  "created_at": "datetime"
}
```

### UserTermsResponse
```json
{
  "terms": "TermResponse[]"
}
```

### TermsStatusResponse
```json
{
  "total_terms": "integer"
}
```

### EmbeddingStatusResponse
```json
{
  "user_id": "integer",
  "embedding_status": "string",
  "last_embedding_time": "datetime | null"
}
```

### EmbeddingUpdateRequest
```json
{
  "embedding_status": "string",
  "last_embedding_time": "datetime | null"
}
```

### DeleteTermsRequest
```json
{
  "en_terms": "string[]"
}
```

### DeleteTermResponse
```json
{
  "message": "string",
  "deleted_term": "string"
}
```

### DeleteTermsResponse
```json
{
  "message": "string",
  "deleted_count": "integer"
}
```

## 使用示例

### Python 示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 获取用户术语
response = requests.get(f"{BASE_URL}/users/1/terms")
terms = response.json()

# 添加术语
new_term = {
    "en": "neural network",
    "cn": "神经网络",
    "jp": "ニューラルネットワーク"
}
response = requests.post(f"{BASE_URL}/users/1/terms", json=new_term)

# 构建embedding
response = requests.post(f"{BASE_URL}/embedding/build/user/1")

# 搜索相似术语
response = requests.get(f"{BASE_URL}/embedding/search?query=AI&top_k=5")
results = response.json()
```

### cURL 示例

```bash
# 获取用户术语
curl -X GET "http://localhost:8000/users/1/terms"

# 添加术语
curl -X POST "http://localhost:8000/users/1/terms" \
  -H "Content-Type: application/json" \
  -d '{"en": "machine learning", "cn": "机器学习"}'

# 构建embedding
curl -X POST "http://localhost:8000/embedding/build/user/1"

# 搜索相似术语
curl -X GET "http://localhost:8000/embedding/search?query=AI&top_k=5"
```

## 注意事项

1. **状态冲突保护**: embedding构建接口有状态检查，避免重复构建
2. **异步处理**: embedding构建是后台任务，不会阻塞API响应
3. **向量持久化**: FAISS索引会自动保存到磁盘
4. **离线模式**: 支持完全离线运行，无需网络连接
5. **多用户支持**: 每个用户有独立的embedding状态管理

## 更新日志

### v1.0.0
- 初始版本发布
- 支持用户术语CRUD操作
- 支持embedding构建和搜索
- 添加状态冲突保护
- 支持离线模式和向量持久化 