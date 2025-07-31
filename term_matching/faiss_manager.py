"""
FAISS索引管理器

提供基于bge-large-en-v1.5模型的FAISS索引管理功能，包括：
- 模型加载和文本编码
- FAISS索引构建和保存
- 向量搜索
"""

import os
import pickle
import logging
from typing import List, Tuple, Dict, Optional
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class FAISSManager:
    """FAISS索引管理器"""

    def __init__(self, model_path: str = "../models/bge-large-en-v1.5"):
        """
        初始化FAISS管理器

        Args:
            model_path: 预加载的BGE-Large-EN模型路径
        """
        self.model_path = model_path
        self.model = None
        self.index = None
        self.term_id_to_index = {}  # term_id -> index_position 映射
        self.index_to_term_id = {}  # index_position -> term_id 映射
        self.embedding_dim = 1024   # BGE-Large-EN的嵌入维度

        # 确保模型路径存在
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path not found: {model_path}")

        # 加载模型
        self._load_model()

    def _load_model(self):
        """加载预加载的BGE-Large-EN模型"""
        try:
            logger.info(f"Loading BGE-Large-EN model from: {self.model_path}")

            self.model = SentenceTransformer(self.model_path)

            logger.info("BGE-Large-EN model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading BGE-Large-EN model: {e}")
            raise e

    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """
        将文本列表编码为向量

        Args:
            texts: 文本列表

        Returns:
            编码后的向量数组，形状为 (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([])

        try:
            # 使用SentenceTransformer生成embedding
            embeddings = self.model.encode(
                texts,
                batch_size=32,
                normalize_embeddings=True,  # 自动归一化
                show_progress_bar=False
            )

            return np.array(embeddings).astype(np.float32)

        except Exception as e:
            logger.error(f"Error encoding texts: {e}")
            raise e

    def build_index(self, term_texts: List[str], term_ids: List[int]) -> None:
        """
        构建FAISS索引

        Args:
            term_texts: 术语文本列表
            term_ids: 对应的术语ID列表
        """
        if not term_texts or not term_ids:
            raise ValueError("term_texts and term_ids cannot be empty")

        if len(term_texts) != len(term_ids):
            raise ValueError(
                "term_texts and term_ids must have the same length")

        try:
            logger.info(f"Building FAISS index for {len(term_texts)} terms")

            # 编码术语文本
            embeddings = self.encode_texts(term_texts)

            # 创建FAISS索引（使用内积索引，适合归一化向量）
            self.index = faiss.IndexFlatIP(self.embedding_dim)

            # 添加向量到索引
            self.index.add(embeddings)

            # 构建ID映射
            self.term_id_to_index = {}
            self.index_to_term_id = {}

            for i, term_id in enumerate(term_ids):
                self.term_id_to_index[term_id] = i
                self.index_to_term_id[i] = term_id

            logger.info(
                f"FAISS index built successfully with {self.index.ntotal} vectors")

        except Exception as e:
            logger.error(f"Error building FAISS index: {e}")
            raise e

    def save_index(self, index_path: str, mapping_path: str) -> None:
        """
        保存FAISS索引和ID映射到文件

        Args:
            index_path: FAISS索引文件路径
            mapping_path: ID映射文件路径
        """
        if self.index is None:
            raise ValueError("No index to save. Please build index first.")

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            os.makedirs(os.path.dirname(mapping_path), exist_ok=True)

            # 保存FAISS索引
            faiss.write_index(self.index, index_path)

            # 保存ID映射
            mapping_data = {
                'term_id_to_index': self.term_id_to_index,
                'index_to_term_id': self.index_to_term_id
            }

            with open(mapping_path, 'wb') as f:
                pickle.dump(mapping_data, f)

            logger.info(f"Index saved to {index_path}")
            logger.info(f"Mapping saved to {mapping_path}")

        except Exception as e:
            logger.error(f"Error saving index: {e}")
            raise e

    def load_index(self, index_path: str, mapping_path: str) -> None:
        """
        从文件加载FAISS索引和ID映射

        Args:
            index_path: FAISS索引文件路径
            mapping_path: ID映射文件路径
        """
        if not os.path.exists(index_path):
            raise FileNotFoundError(f"Index file not found: {index_path}")

        if not os.path.exists(mapping_path):
            raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

        try:
            # 加载FAISS索引
            self.index = faiss.read_index(index_path)

            # 加载ID映射
            with open(mapping_path, 'rb') as f:
                mapping_data = pickle.load(f)

            self.term_id_to_index = mapping_data['term_id_to_index']
            self.index_to_term_id = mapping_data['index_to_term_id']

            logger.info(f"Index loaded from {index_path}")
            logger.info(f"Mapping loaded from {mapping_path}")
            logger.info(f"Loaded {self.index.ntotal} vectors")

        except Exception as e:
            logger.error(f"Error loading index: {e}")
            raise e

    def search(self, query_texts: List[str], top_k: int = 10, threshold: float = 0.7) -> List[List[Tuple[int, float]]]:
        """
        批量搜索

        Args:
            query_texts: 查询文本列表
            top_k: 每个查询返回的最大结果数
            threshold: 相似度阈值

        Returns:
            搜索结果列表，每个查询对应一个结果列表
            格式: [[(term_id, similarity_score), ...], ...]
        """
        if self.index is None:
            raise ValueError(
                "No index available. Please build or load index first.")

        if not query_texts:
            return []

        try:
            # 编码查询文本
            query_embeddings = self.encode_texts(query_texts)

            # 搜索相似向量
            similarities, indices = self.index.search(
                query_embeddings,
                min(top_k, self.index.ntotal)
            )

            # 处理搜索结果
            results = []
            for i, query_text in enumerate(query_texts):
                query_results = []

                for j, (similarity, idx) in enumerate(zip(similarities[i], indices[i])):
                    # 检查索引是否有效且相似度达到阈值
                    if idx in self.index_to_term_id and similarity >= threshold:
                        term_id = self.index_to_term_id[idx]
                        query_results.append((term_id, float(similarity)))

                # 按相似度降序排序
                query_results.sort(key=lambda x: x[1], reverse=True)
                results.append(query_results)

            logger.info(f"Search completed for {len(query_texts)} queries")
            return results

        except Exception as e:
            logger.error(f"Error during search: {e}")
            raise e

    def get_stats(self) -> Dict:
        """
        获取索引统计信息

        Returns:
            统计信息字典
        """
        stats = {
            'total_vectors': self.index.ntotal if self.index else 0,
            'embedding_dimension': self.embedding_dim,
            'mapped_terms': len(self.term_id_to_index),
            'model_path': self.model_path
        }

        return stats

    def is_index_loaded(self) -> bool:
        """
        检查索引是否已加载

        Returns:
            True如果索引已加载，否则False
        """
        return self.index is not None
