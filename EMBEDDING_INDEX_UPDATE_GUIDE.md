# Embedding索引更新指南

## 问题描述

在原有的embedding系统中，当用户添加新术语后，这些新术语不会自动添加到FAISS索引中，导致在搜索时找不到新添加的词汇。

### 原有问题

1. **缺少增量更新机制**: `rebuild_faiss_index.py` 只是完全重建索引，效率低下
2. **没有自动同步**: 用户通过API添加术语后，索引不会自动更新
3. **需要手动触发**: 用户需要手动调用重建接口来更新索引

## 解决方案

### 1. 自动索引更新

在用户添加新术语时，系统会自动触发索引更新：

```python
# 在 app/api/router/user.py 中已添加自动更新逻辑
@router.post("/{user_id}/terms")
async def create_user_terms(user_id: int, terms: List[TermCreate], db: Session = Depends(get_db)):
    # ... 创建术语逻辑 ...
    
    # 如果有新术语添加，自动触发索引更新
    if new_terms_added:
        asyncio.create_task(update_index_for_user(user_id, embedding_service))
```

### 2. 增量更新方法

新增了 `add_terms_to_index()` 方法，支持增量更新：

```python
# 在 TermMatcher 类中
def add_terms_to_index(self, new_terms_data: List[Dict]) -> None:
    """
    向现有索引添加新的术语（增量更新）
    
    Args:
        new_terms_data: 新术语数据列表，格式为[{"term_id": int, "en": str}, ...]
    """
```

### 3. 手动更新API

新增了手动触发增量更新的API接口：

```bash
POST /term-match/update-index
```

**响应示例:**
```json
{
  "message": "Successfully added 5 new terms to index",
  "status": "updated",
  "new_terms_count": 5,
  "total_terms": 100,
  "indexed_terms": 100,
  "new_terms": ["machine learning", "deep learning", "neural network", "AI", "ML"]
}
```

### 4. 增量更新脚本

创建了 `update_faiss_index_incremental.py` 脚本：

```bash
python update_faiss_index_incremental.py
```

这个脚本会：
- 检查现有索引中的术语
- 从数据库获取新术语
- 只添加新术语到索引，不重建整个索引

## 使用方法

### 方法1: 自动更新（推荐）

用户添加术语时，系统会自动更新索引，无需手动操作。

### 方法2: 手动API更新

```bash
# 手动触发增量更新
curl -X POST "http://localhost:8000/term-match/update-index"
```

### 方法3: 脚本更新

```bash
# 运行增量更新脚本
python update_faiss_index_incremental.py
```

### 方法4: 完全重建（必要时）

```bash
# 完全重建索引（用于首次构建或修复索引）
python rebuild_faiss_index.py
```

## 监控和调试

### 1. 检查索引状态

```bash
# 获取索引统计信息
curl "http://localhost:8000/term-match/stats"
```

**响应示例:**
```json
{
  "status": "success",
  "performance_stats": {
    "total_batches": 10,
    "total_embeddings": 500,
    "total_processing_time": 2.5
  },
  "index_stats": {
    "total_vectors": 100,
    "embedding_dimension": 1024,
    "mapped_terms": 100,
    "index_type": "IndexFlatIP",
    "is_loaded": true
  }
}
```

### 2. 测试新术语

```bash
# 测试新添加的术语是否能被找到
curl -X POST "http://localhost:8000/term-match/test?text=your_new_term&similarity_threshold=0.6&top_k=5"
```

## 性能优化

### 1. 批量处理

- 新术语会批量编码和添加到索引
- 减少频繁的索引操作

### 2. 异步更新

- 索引更新在后台异步进行
- 不影响用户添加术语的响应速度

### 3. 增量更新

- 只添加新术语，不重建整个索引
- 大幅提升更新效率

## 故障排除

### 1. 索引未加载

**错误**: "Index not loaded, please rebuild index first"

**解决方案**:
```bash
python rebuild_faiss_index.py
```

### 2. 术语ID冲突

**错误**: "Term IDs already exist in index"

**解决方案**: 检查数据库中的术语ID是否重复，或重建索引

### 3. 编码失败

**错误**: "Error encoding texts"

**解决方案**: 检查模型文件是否存在，确保BGE模型正确加载

### 4. 索引文件损坏

**错误**: "Invalid mapping file format"

**解决方案**: 删除索引文件，重新构建索引

## 最佳实践

1. **定期监控**: 使用 `/term-match/stats` 接口监控索引状态
2. **备份索引**: 定期备份 `faiss_indexes/` 目录
3. **测试新术语**: 添加术语后测试是否能被正确匹配
4. **批量添加**: 尽量批量添加术语，减少索引更新频率
5. **错误处理**: 监控日志，及时处理索引更新错误

## 配置说明

### 数据库配置

确保数据库连接配置正确：

```python
DATABASE_URL = "mysql+pymysql://root:123456@localhost/Extension"
```

### 索引路径配置

索引文件默认保存在：

```
./faiss_indexes/
├── faiss.index          # FAISS索引文件
└── term_mapping.pkl     # 术语ID映射文件
```

### 模型路径配置

BGE模型文件路径：

```
./models/bge-large-en-v1.5/
```

## 更新日志

- **v1.0**: 基础embedding系统
- **v1.1**: 添加增量更新功能
- **v1.2**: 添加自动索引更新
- **v1.3**: 添加监控和调试接口 