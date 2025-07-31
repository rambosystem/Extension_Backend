# FAISS术语匹配算法

基于FAISS + bge-large-en-v1.5模型的英文术语匹配算法，支持多粒度匹配（1-3个词）和重叠去重处理。

## 功能特性

- 🔍 **多粒度匹配**: 支持1-gram、2-gram、3-gram匹配
- 🧠 **语义相似度**: 基于bge-large-en-v1.5模型的语义匹配
- 🔄 **重叠去重**: 最大长度优先的重叠处理策略
- ⚡ **高性能**: 基于FAISS的高效向量搜索
- 📦 **批量处理**: 支持批量文本输入和匹配
- 💾 **索引持久化**: 支持索引的保存和加载

## 项目结构

```
term_matching/
├── __init__.py              # 包初始化文件
├── text_preprocessor.py     # 文本预处理模块
├── faiss_manager.py         # FAISS索引管理器
├── overlap_handler.py       # 重叠去重处理器
├── term_matcher.py          # 主匹配算法类
├── example.py              # 完整测试示例
├── simple_example.py       # 简单使用示例
├── requirements.txt        # 依赖包列表
└── README.md              # 项目文档
```

## 安装依赖

```bash
# 安装核心依赖
pip install faiss-cpu sentence-transformers nltk numpy

# 或者使用requirements.txt
pip install -r requirements.txt
```

## 快速开始

### 1. 基本使用

```python
from term_matching import TermMatcher

# 初始化匹配器
matcher = TermMatcher()

# 准备术语数据
terms_data = [
    {"term_id": 1, "en": "machine learning"},
    {"term_id": 2, "en": "artificial intelligence"},
    {"term_id": 3, "en": "deep learning"}
]

# 构建索引
matcher.build_index_from_terms(terms_data)

# 进行匹配
input_texts = ["We use machine learning algorithms"]
results = matcher.match_terms(input_texts, similarity_threshold=0.7)

print(f"匹配结果: {results}")
# 输出: [[1]] (匹配到term_id=1的"machine learning")
```

### 2. 详细匹配

```python
# 获取详细匹配信息
detailed_results = matcher.match_terms_detailed(input_texts)

for matches in detailed_results:
    for match in matches:
        print(f"术语ID: {match['term_id']}")
        print(f"N-gram: {match['ngram']}")
        print(f"相似度: {match['similarity']}")
        print(f"N-gram长度: {match['ngram_length']}")
```

### 3. 索引持久化

```python
# 保存索引
matcher.save_index("index.faiss", "mapping.pkl")

# 加载索引
new_matcher = TermMatcher()
new_matcher.load_index("index.faiss", "mapping.pkl")
```

## 核心模块说明

### TextPreprocessor (文本预处理)

- **停用词过滤**: 使用NLTK英文停用词
- **文本清理**: 去除标点符号，转换为小写
- **N-gram生成**: 生成1-gram到max_n-gram的所有组合

### FAISSManager (FAISS索引管理)

- **模型加载**: 加载预训练的bge-large-en-v1.5模型
- **索引构建**: 构建和保存FAISS索引
- **向量搜索**: 批量向量相似度搜索

### OverlapHandler (重叠去重)

- **重叠检测**: 检测N-gram在原文中的位置重叠
- **最大长度优先**: 优先选择更长的N-gram
- **去重处理**: 移除重叠的匹配结果

### TermMatcher (主匹配器)

- **统一接口**: 整合所有模块的匹配接口
- **批量处理**: 支持批量文本输入
- **参数配置**: 可配置相似度阈值、top_k等参数

## 配置参数

### 匹配参数

- `similarity_threshold`: 相似度阈值，默认0.7
- `top_k`: 每个N-gram返回的最大结果数，默认10
- `max_ngram`: 最大N-gram长度，默认3

### 模型配置

- `model_path`: 预加载的bge-large-en-v1.5模型路径，默认"./models/bge-large-en-v1.5"

## 运行示例

### 简单示例

```bash
cd term_matching
python simple_example.py
```

### 完整测试

```bash
cd term_matching
python example.py
```

## 性能优化

### 服务器配置建议

- **CPU**: 双核以上
- **内存**: 4GB以上
- **存储**: 足够的磁盘空间存储模型和索引

### 性能特点

- **索引构建**: 一次性构建，可重复使用
- **匹配速度**: 毫秒级响应
- **内存使用**: 模型加载后常驻内存

## 错误处理

### 常见错误

1. **模型路径不存在**
   ```
   FileNotFoundError: Model path not found: ./models/bge-large-en-v1.5
   ```
   解决：确保模型文件存在于指定路径

2. **索引未加载**
   ```
   ValueError: No index available. Please build or load index first.
   ```
   解决：先调用`build_index_from_terms()`或`load_index()`

3. **依赖包缺失**
   ```
   ModuleNotFoundError: No module named 'faiss'
   ```
   解决：安装缺失的依赖包

## 扩展功能

### 自定义停用词

```python
# 添加自定义停用词
matcher.update_stop_words(add_words=["custom", "stop", "words"])

# 移除停用词
matcher.update_stop_words(remove_words=["remove", "these", "words"])
```

### 重叠检测测试

```python
# 测试重叠检测功能
has_overlap = matcher.test_overlap_detection(
    "machine learning algorithms",
    "machine learning",
    "learning algorithms"
)
print(f"是否有重叠: {has_overlap}")
```

## 集成到FastAPI

```python
from fastapi import FastAPI
from term_matching import TermMatcher

app = FastAPI()
matcher = TermMatcher()

@app.post("/match_terms")
async def match_terms(texts: List[str]):
    results = matcher.match_terms(texts)
    return {"results": results}
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！ 