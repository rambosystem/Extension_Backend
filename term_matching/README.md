# FAISS术语匹配算法

基于FAISS + bge-large-en-v1.5模型的英文术语匹配算法，支持多粒度匹配（1-3个词）和重叠去重处理。**集成智能批处理优化，使用最优批处理大小64，显著提升性能。**

## 功能特性

- ✅ **多粒度匹配**: 支持1-gram、2-gram、3-gram匹配
- ✅ **重叠去重**: 最大长度优先的重叠去重策略
- ✅ **高性能**: 基于FAISS的高效向量搜索
- ✅ **智能批处理**: 集成批处理优化，减少模型调用次数
- ✅ **英文专用**: 使用bge-large-en-v1.5模型，专为英文优化
- ✅ **易于使用**: 简洁的API接口
- ✅ **完整文档**: 详细的使用说明和示例
- ✅ **性能监控**: 详细的性能统计和优化建议

## 项目结构

```
term_matching/
├── __init__.py              # 包初始化文件
├── term_matcher.py          # 主匹配器类（集成智能批处理）
├── text_preprocessor.py     # 文本预处理模块
├── faiss_manager.py         # FAISS索引管理器
├── overlap_handler.py       # 重叠去重处理器
├── simple_example.py        # 简单使用示例
├── requirements.txt         # 依赖包列表
└── README.md               # 项目文档
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 基本使用

```python
from term_matching import TermMatcher

# 初始化匹配器（使用最优批处理大小64）
matcher = TermMatcher(batch_size=64)

# 准备术语数据
terms_data = [
    {"term_id": 1, "en": "machine learning"},
    {"term_id": 2, "en": "artificial intelligence"},
    {"term_id": 3, "en": "deep learning"},
    # ... 更多术语
]

# 构建索引
matcher.build_index_from_terms(terms_data)

# 进行匹配（使用智能批处理）
input_texts = [
    "We use machine learning algorithms for data analysis",
    "Artificial intelligence is transforming industries"
]

results = matcher.match_terms(input_texts, similarity_threshold=0.7)
print(f"匹配结果: {results}")
```

### 详细匹配

```python
# 获取详细匹配信息
detailed_results = matcher.match_terms_detailed(input_texts)

for i, matches in enumerate(detailed_results):
    print(f"\n文本 {i+1}: {input_texts[i]}")
    for match in matches:
        print(f"  - 术语ID: {match['term_id']}")
        print(f"    N-gram: '{match['ngram']}'")
        print(f"    相似度: {match['similarity']:.4f}")
```

### 性能监控

```python
# 获取详细统计信息
stats = matcher.get_stats()

print(f"批处理大小: {stats['batch_size']}")
print(f"批处理启用: {stats['batch_processing_enabled']}")

# 性能统计
perf_stats = stats['performance_stats']
print(f"总批次数: {perf_stats['total_batches']}")
print(f"总嵌入数: {perf_stats['total_embeddings']}")
print(f"编码时间: {perf_stats['total_encoding_time']:.3f}s")
```

### 批处理大小优化

```python
# 自动优化批处理大小
sample_texts = ["sample text 1", "sample text 2", ...]
optimal_batch_size = matcher.optimize_batch_size(sample_texts)
print(f"最优批处理大小: {optimal_batch_size}")
```

## 核心模块

### TermMatcher

主要的术语匹配器类，集成智能批处理优化。

**主要方法**:
- `build_index_from_terms(terms_data)`: 从术语数据构建FAISS索引
- `match_terms(input_texts, ...)`: 进行术语匹配（智能批处理）
- `match_terms_detailed(input_texts, ...)`: 获取详细匹配信息
- `get_stats()`: 获取系统统计信息
- `optimize_batch_size(sample_texts)`: 自动优化批处理大小

**智能批处理特性**:
- 收集所有n-grams后一次性批量编码
- 减少模型调用次数，提升性能
- 支持批处理大小自动优化
- 详细的性能统计监控

### TextPreprocessor

文本预处理模块，负责文本清理、分词和N-gram生成。

**主要功能**:
- 英文停用词过滤
- 文本分词和清理
- N-gram生成（1-3个词）
- 标点符号和特殊字符处理

### FAISSManager

FAISS索引管理器，负责向量编码和相似度搜索。

**主要功能**:
- 加载bge-large-en-v1.5模型
- 文本向量编码
- FAISS索引构建和管理
- 相似度搜索

### OverlapHandler

重叠去重处理器，实现最大长度优先的去重策略。

**主要功能**:
- 检测N-gram重叠
- 最大长度优先去重
- 位置重叠检测

## 配置参数

### 匹配参数

- `similarity_threshold`: 相似度阈值，默认0.7
- `top_k`: 每个查询返回的最大结果数，默认10
- `max_ngram`: 最大N-gram长度，默认3

### 批处理配置

- `batch_size`: 批处理大小，默认64（经过优化的最优值）
- `model_path`: 模型路径，默认"../models/bge-large-en-v1.5"
- `enable_stats`: 是否启用性能统计，默认True

## 性能特点

- **智能批处理**: 减少模型调用次数，提升17-20%性能
- **最优批处理大小**: 64（经过自动优化得出）
- **处理速度**: 支持大批量文本处理
- **内存效率**: 优化的内存使用
- **准确性**: 基于高质量嵌入模型的精确匹配
- **可扩展性**: 支持大规模术语库

## 使用示例

运行简单示例：

```bash
python simple_example.py
```

示例输出：
```
🚀 FAISS术语匹配算法简单示例
========================================
1. 初始化TermMatcher...
✅ 初始化完成

2. 准备术语数据...
✅ 准备了 8 个术语

3. 构建FAISS索引...
✅ 索引构建完成

4. 准备输入文本...
✅ 准备了 4 个输入文本

5. 进行术语匹配...
✅ 匹配完成

6. 匹配结果:
----------------------------------------
📝 文本 1: We use machine learning algorithms for data analysis.
🎯 匹配到的术语ID: [1, 1, 5, 1, 5, 4, 3, 7, 5, 5, 1]
📖 匹配到的术语: ['machine learning', 'machine learning', 'data science', ...]

7. 系统统计信息:
----------------------------------------
📊 FAISS索引统计: {'total_vectors': 8, 'embedding_dimension': 1024, ...}
🛑 停用词数量: 208
⚙️  批处理大小: 64
🔄 批处理启用: True
📈 性能统计:
  - 总批次数: 3
  - 总嵌入数: 90
  - 总处理时间: 4.447s
  - 编码时间: 4.443s
  - 搜索时间: 0.002s
  - 重叠处理时间: 0.002s

🎉 示例运行完成！
```

## 性能优化建议

### 1. 批处理大小调优
- **小规模数据** (<100 n-grams): 16-32
- **中等规模数据** (100-500 n-grams): 32-64
- **大规模数据** (>500 n-grams): 64-128

### 2. 内存优化
- **监控内存使用**: 避免超出系统限制
- **调整批处理大小**: 根据可用内存调整
- **清理临时数据**: 及时释放不需要的数据

### 3. 使用建议
- **大批量处理**: 优先使用批处理模式
- **实时处理**: 小批量时使用单线程模式
- **性能监控**: 定期检查性能统计信息
- **自动优化**: 使用`optimize_batch_size()`自动找到最优参数

## 注意事项

1. **模型路径**: 确保bge-large-en-v1.5模型已正确加载
2. **内存要求**: 模型加载需要约1.5GB内存
3. **英文专用**: 当前版本仅支持英文文本处理
4. **相似度阈值**: 根据实际需求调整相似度阈值
5. **批处理大小**: 默认使用最优值64，可根据实际情况调整

## 依赖包

- `faiss-cpu==1.7.4`: FAISS向量搜索库
- `sentence-transformers==2.2.2`: 句子嵌入模型
- `nltk==3.9.1`: 自然语言处理工具包
- `numpy==1.24.3`: 数值计算库

## 许可证

本项目采用MIT许可证。 