# Embedding API 废弃说明

## 概述

为了统一API架构，提高系统一致性，我们决定废弃原有的embedding相关API，统一使用term-match API。

## 废弃的API端点

### 1. `/embedding/build/user/{user_id}`
**替代方案：** `/term-match/build/user/{user_id}`

**功能：** 为用户构建索引（后台任务）

**请求方式：** `POST`

**响应示例：**
```json
{
  "message": "Index build task started",
  "user_id": 1,
  "status": "building"
}
```

### 2. `/embedding/build/all`
**替代方案：** `/term-match/build/all`

**功能：** 为所有用户构建索引（后台任务）

**请求方式：** `POST`

**响应示例：**
```json
{
  "message": "Index build task started for all users",
  "status": "building"
}
```

### 3. `/embedding/search`
**替代方案：** `/term-match/search`

**功能：** 搜索相似术语

**请求方式：** `GET`

**参数：**
- `query`: 搜索查询文本
- `top_k`: 返回结果数量（默认5）
- `threshold`: 相似度阈值（默认0.7）

**响应示例：**
```json
{
  "query": "machine learning",
  "results": [
    {
      "term_id": 1,
      "en": "machine learning",
      "cn": "机器学习",
      "jp": "機械学習"
    }
  ],
  "total_results": 1
}
```

### 4. `/embedding/stats`
**替代方案：** `/term-match/stats`

**功能：** 获取索引统计信息

**请求方式：** `GET`

**响应示例：**
```json
{
  "status": "success",
  "performance_stats": {
    "faiss_stats": {
      "total_vectors": 21,
      "embedding_dimension": 1024,
      "mapped_terms": 21,
      "index_type": "IndexFlatIP",
      "is_loaded": true
    }
  },
  "index_stats": {
    "total_vectors": 21,
    "embedding_dimension": 1024,
    "mapped_terms": 21,
    "index_type": "IndexFlatIP",
    "is_loaded": true
  }
}
```

### 5. `/embedding/status/{user_id}`
**替代方案：** `/term-match/status/{user_id}`

**功能：** 获取指定用户的索引构建状态

**请求方式：** `GET`

**响应示例：**
```json
{
  "user_id": 1,
  "index_status": "completed",
  "last_build_time": "2024-01-01T10:30:00"
}
```

### 6. `/embedding/status/{user_id}` (PUT)
**替代方案：** `/term-match/status/{user_id}`

**功能：** 更新指定用户的索引构建状态

**请求方式：** `PUT`

**参数：**
- `status`: 状态值（pending, building, completed, failed）

## 新增的term-match API端点

### 1. `/term-match/match`
**功能：** 完整的术语匹配接口

**请求方式：** `POST`

**参数：**
- `texts`: 待匹配的文本列表
- `similarity_threshold`: 相似度阈值（默认0.7）
- `top_k`: 每个文本返回的最大匹配数（默认10）
- `max_ngram`: 最大N-gram长度（默认3）
- `user_id`: 限制搜索特定用户的术语（可选）

**响应示例：**
```json
[
  {
    "en": "machine learning",
    "cn": "机器学习",
    "jp": "機械学習"
  }
]
```

### 2. `/term-match/update-index`
**功能：** 增量更新FAISS索引（添加新术语）

**请求方式：** `POST`

**响应示例：**
```json
{
  "message": "Successfully added 1 new terms to index",
  "status": "updated",
  "new_terms_count": 1,
  "total_terms": 18,
  "indexed_terms": 19,
  "new_terms": ["Budget Manager"]
}
```

### 3. `/term-match/index` (DELETE)
**功能：** 删除整个FAISS索引

**请求方式：** `DELETE`

**响应示例：**
```json
{
  "message": "Successfully deleted index with 18 terms",
  "status": "deleted",
  "deleted_files": ["faiss.index", "term_mapping.pkl"],
  "terms_deleted": 18
}
```

### 4. `/term-match/terms` (DELETE)
**功能：** 从索引中删除指定的术语

**请求方式：** `DELETE`

**请求体：**
```json
[1, 2, 3]
```

**响应示例：**
```json
{
  "message": "Successfully deleted 2 terms from index",
  "status": "deleted",
  "deleted_count": 2,
  "deleted_ids": [1, 2],
  "invalid_ids": []
}
```

### 5. `/term-match/user/{user_id}` (DELETE)
**功能：** 删除指定用户的所有术语

**请求方式：** `DELETE`

**响应示例：**
```json
{
  "message": "Successfully deleted 16 terms for user 1",
  "status": "deleted",
  "user_id": 1,
  "deleted_count": 16,
  "deleted_ids": [63, 64, 65, 67, 68, 69, 75, 76, 77, 78, 79, 80, 82, 83, 84, 85]
}
```

## 迁移指南

### 1. 搜索功能迁移
**旧代码：**
```python
response = requests.get("http://localhost:8000/embedding/search", params={
    "query": "machine learning",
    "top_k": 5,
    "threshold": 0.7
})
```

**新代码：**
```python
response = requests.get("http://localhost:8000/term-match/search", params={
    "query": "machine learning",
    "top_k": 5,
    "threshold": 0.7
})
```

### 2. 构建索引迁移
**旧代码：**
```python
response = requests.post("http://localhost:8000/embedding/build/all")
```

**新代码：**
```python
response = requests.post("http://localhost:8000/term-match/build/all")
```

### 3. 获取状态迁移
**旧代码：**
```python
response = requests.get("http://localhost:8000/embedding/status/1")
```

**新代码：**
```python
response = requests.get("http://localhost:8000/term-match/status/1")
```

## 优势

1. **统一架构：** 所有向量搜索和索引管理功能都通过term-match API提供
2. **一致性：** 使用相同的TermMatcher引擎，确保结果一致性
3. **简化维护：** 减少代码重复，降低维护成本
4. **性能优化：** 统一的索引管理和搜索算法

## 时间表

- **立即生效：** 新的term-match API已可用
- **过渡期：** 旧的embedding API将在下一个版本中完全移除
- **建议：** 尽快迁移到新的API

## 技术支持

如果在迁移过程中遇到问题，请参考：
1. API文档：`/docs`
2. 测试脚本：`test_api_endpoints.py`
3. 调试脚本：`debug_embedding_issue.py` 