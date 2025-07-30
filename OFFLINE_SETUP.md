# 离线模型和向量持久化配置

## 概述

本项目已配置为使用离线BGE-M3模型和FAISS向量持久化存储，确保在没有网络连接的情况下也能正常工作。

## 配置说明

### 1. 离线模型配置

#### 环境变量设置
```bash
# 强制离线模式
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
export HF_ENDPOINT=https://hf-mirror.com
```

#### 模型缓存目录
- 默认缓存目录: `./model_cache`
- 模型文件会自动下载到该目录
- 首次运行后，模型将保存在本地

### 2. 向量持久化配置

#### FAISS索引存储
- 索引文件路径: `./faiss_indexes/`
- 索引文件: `faiss.index`
- 映射文件: `term_mapping.pkl`

#### 自动保存配置
- 自动保存间隔: 每100次操作
- 可配置参数: `auto_save_interval`

### 3. 目录结构

```
project/
├── model_cache/           # 模型缓存目录
│   └── BAAI/
│       └── bge-m3/       # BGE-M3模型文件
├── faiss_indexes/        # FAISS索引目录
│   ├── faiss.index      # FAISS索引文件
│   └── term_mapping.pkl # 术语ID映射文件
└── app/
    └── config.py         # 配置文件
```

## 使用方法

### 1. 首次运行（需要网络下载模型）

```python
from faiss_engine.embeddings import BGE_M3EmbeddingService
from faiss_engine.vector_store import FAISSVectorStore

# 首次运行会下载模型到本地缓存
embedding_service = BGE_M3EmbeddingService(cache_dir="./model_cache")
vector_store = FAISSVectorStore(index_path="./faiss_indexes")
```

### 2. 离线运行

```python
# 设置离线环境变量
import os
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

# 使用本地缓存的模型
embedding_service = BGE_M3EmbeddingService(cache_dir="./model_cache")
vector_store = FAISSVectorStore(index_path="./faiss_indexes")
```

### 3. 测试离线功能

```bash
# 运行测试脚本
python test_offline_persistence.py
```

## 配置参数

### 模型配置 (`app/config.py`)

```python
# 离线模型配置
TRANSFORMERS_OFFLINE: bool = True
HF_HUB_OFFLINE: bool = True
HF_ENDPOINT: str = "https://hf-mirror.com"
MODEL_CACHE_DIR: str = "./model_cache"

# FAISS向量持久化配置
FAISS_INDEX_PATH: str = "./faiss_indexes"
VECTOR_PERSISTENCE_ENABLED: bool = True
AUTO_SAVE_INTERVAL: int = 100
```

### 向量存储配置

```python
# 初始化向量存储
vector_store = FAISSVectorStore(
    index_path="./faiss_indexes",      # 索引存储路径
    embedding_dim=1024,                # 向量维度
    auto_save_interval=100             # 自动保存间隔
)
```

## 性能优化

### 1. 模型优化
- 使用半精度浮点数 (`use_fp16=True`)
- CPU/GPU设备选择
- 批处理大小配置

### 2. 向量存储优化
- 自动保存间隔调整
- 索引类型选择 (`IndexFlatIP`)
- 向量归一化

### 3. 内存管理
- 模型缓存复用
- 向量索引压缩
- 定期清理临时文件

## 故障排除

### 1. 模型加载失败
```bash
# 检查模型缓存目录
ls -la ./model_cache/

# 重新下载模型
rm -rf ./model_cache/
python -c "from faiss_engine.embeddings import BGE_M3EmbeddingService; BGE_M3EmbeddingService()"
```

### 2. 向量索引损坏
```bash
# 备份并重建索引
cp -r ./faiss_indexes ./faiss_indexes_backup
rm ./faiss_indexes/faiss.index ./faiss_indexes/term_mapping.pkl
```

### 3. 权限问题
```bash
# 确保目录权限正确
chmod 755 ./model_cache/
chmod 755 ./faiss_indexes/
```

## 注意事项

1. **首次运行**: 需要网络连接下载模型文件
2. **磁盘空间**: 确保有足够的磁盘空间存储模型和索引
3. **内存使用**: BGE-M3模型需要约2GB内存
4. **备份策略**: 定期备份向量索引文件
5. **版本兼容**: 确保transformers和torch版本兼容

## 监控和维护

### 1. 日志监控
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### 2. 性能监控
```python
# 获取向量存储统计信息
stats = vector_store.get_stats()
print(f"Total vectors: {stats['total_vectors']}")
print(f"Index size: {stats['index_size_mb']} MB")
```

### 3. 定期维护
- 清理临时文件
- 检查磁盘空间
- 验证索引完整性
- 更新模型缓存 