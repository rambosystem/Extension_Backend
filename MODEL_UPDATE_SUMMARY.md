# 模型更新总结

## 更新内容

### 1. 模型更换
- **原模型**: BGE-M3 (多语言模型)
- **新模型**: BGE-Large-EN-v1.5 (英文专用模型)
- **模型位置**: `./models/bge-large-en-v1.5/`

### 2. 主要改进

#### 2.1 专注英文术语
- ✅ 移除了多语言融合策略
- ✅ 只对英文术语（en字段）进行embedding
- ✅ 搜索时只匹配英文术语
- ✅ 提高了英文术语匹配的准确性

#### 2.2 使用预加载模型
- ✅ 使用本地预加载的模型，避免每次下载
- ✅ 更快的启动速度
- ✅ 离线环境友好

#### 2.3 简化embedding流程
- ✅ 使用SentenceTransformer替代FlagEmbedding
- ✅ 自动归一化，无需手动处理
- ✅ 更简洁的代码结构

### 3. 技术变更

#### 3.1 文件修改
- `faiss_engine/embeddings.py`: 完全重写，使用BGE-Large-EN模型
- `faiss_engine/vector_store.py`: 移除手动归一化代码
- `app/api/router/ search.py`: 更新API文档注释
- `README.md`: 更新模型相关信息

#### 3.2 依赖变更
- 使用 `sentence-transformers` 库
- 移除 `FlagEmbedding` 相关依赖
- 保持向后兼容性（类名别名）

### 4. 性能提升

#### 4.1 准确性提升
- 英文术语匹配更准确
- 相似度计算更精确
- 减少了多语言混合带来的噪声

#### 4.2 效率提升
- 模型加载更快（预加载）
- 推理速度更快（专用英文模型）
- 内存使用更高效

### 5. 测试验证

已通过以下测试：
- ✅ 模型加载测试
- ✅ 单个术语embedding生成
- ✅ 批量术语处理
- ✅ 相似度计算验证
- ✅ 向量维度验证（1024维）

### 6. 使用说明

#### 6.1 环境要求
- 确保 `./models/bge-large-en-v1.5/` 目录存在
- 安装 `sentence-transformers` 依赖

#### 6.2 API使用
- 搜索API现在只支持英文查询
- 术语匹配基于英文术语进行
- 中文和日文翻译仅用于显示，不参与embedding

#### 6.3 重建索引
如果需要重建向量索引：
```bash
# 重建所有用户的索引
curl -X POST "http://localhost:8000/search/rebuild-index"

# 重建特定用户的索引
curl -X POST "http://localhost:8000/search/rebuild-index?user_id=1"
```

### 7. 注意事项

1. **数据兼容性**: 新模型生成的向量与旧模型不兼容，需要重建索引
2. **语言限制**: 现在只支持英文术语的embedding和搜索
3. **模型路径**: 确保模型文件路径正确，否则会启动失败

### 8. 后续优化建议

1. 考虑添加模型版本管理
2. 可以添加模型性能监控
3. 考虑支持模型热更新
4. 可以添加embedding质量评估指标 