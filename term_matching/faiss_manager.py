"""
重构后的FAISS索引管理器

专注于FAISS索引的管理功能，不负责文本编码
与现有的BGE_Large_EN_EmbeddingService配合使用
"""

import os
import pickle
import logging
from typing import List, Tuple, Dict, Optional
import numpy as np
import faiss

logger = logging.getLogger(__name__)


class FAISSManager:
    """
    FAISS索引管理器 - 专注于索引操作

    职责：
    - FAISS索引的构建和管理
    - 索引文件的保存和加载
    - 向量搜索操作
    - ID映射管理

    不负责：
    - 文本编码（由BGE_Large_EN_EmbeddingService处理）
    """

    def __init__(self, embedding_dim: int = 1024):
        """
        初始化FAISS管理器

        Args:
            embedding_dim: 嵌入向量维度，BGE-Large-EN为1024
        """
        self.embedding_dim = embedding_dim
        self.index = None
        self.term_id_to_index = {}  # term_id -> index_position 映射
        self.index_to_term_id = {}  # index_position -> term_id 映射

    def build_index(self, embeddings: np.ndarray, term_ids: List[int]) -> None:
        """
        使用预计算的嵌入向量构建FAISS索引

        Args:
            embeddings: 预计算的嵌入向量数组，形状为 (n_terms, embedding_dim)
            term_ids: 对应的术语ID列表
        """
        if len(embeddings) == 0 or len(term_ids) == 0:
            raise ValueError("embeddings and term_ids cannot be empty")

        if len(embeddings) != len(term_ids):
            raise ValueError(
                "embeddings and term_ids must have the same length")

        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(f"Expected embedding dimension {self.embedding_dim}, "
                             f"got {embeddings.shape[1]}")

        try:
            logger.info(f"Building FAISS index for {len(term_ids)} terms")

            # 创建FAISS索引（使用内积索引，适合归一化向量）
            self.index = faiss.IndexFlatIP(self.embedding_dim)

            # 确保数据类型正确
            embeddings_f32 = embeddings.astype(np.float32)

            # 添加向量到索引
            self.index.add(embeddings_f32)

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

    def search_embeddings(self, query_embeddings: np.ndarray,
                          top_k: int = 10, threshold: float = 0.7) -> List[List[Tuple[int, float]]]:
        """
        使用预计算的查询嵌入向量搜索相似术语

        Args:
            query_embeddings: 查询的嵌入向量数组，形状为 (n_queries, embedding_dim)
            top_k: 每个查询返回的最大结果数
            threshold: 相似度阈值

        Returns:
            搜索结果列表，每个查询对应一个结果列表
            格式: [[(term_id, similarity_score), ...], ...]
        """
        if self.index is None:
            raise ValueError(
                "No index available. Please build or load index first.")

        if len(query_embeddings) == 0:
            return []

        try:
            # 确保数据类型正确
            query_embeddings_f32 = query_embeddings.astype(np.float32)

            # 搜索相似向量
            similarities, indices = self.index.search(
                query_embeddings_f32,
                min(top_k, self.index.ntotal)
            )

            # 处理搜索结果
            results = []
            for i in range(len(query_embeddings)):
                query_results = []

                for similarity, idx in zip(similarities[i], indices[i]):
                    # 检查索引是否有效且相似度达到阈值
                    if idx != -1 and idx in self.index_to_term_id and similarity >= threshold:
                        term_id = self.index_to_term_id[idx]
                        query_results.append((term_id, float(similarity)))

                # 按相似度降序排序
                query_results.sort(key=lambda x: x[1], reverse=True)
                results.append(query_results)

            logger.info(f"Search completed for {len(query_embeddings)} queries, "
                        f"found {sum(len(r) for r in results)} total matches")
            return results

        except Exception as e:
            logger.error(f"Error during search: {e}")
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
                'index_to_term_id': self.index_to_term_id,
                'embedding_dim': self.embedding_dim
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

            # 统一使用新格式
            if not isinstance(mapping_data, dict):
                raise ValueError(
                    f"Invalid mapping file format: {type(mapping_data)}")

            if 'term_id_to_index' not in mapping_data or 'index_to_term_id' not in mapping_data:
                raise ValueError(
                    "Mapping file must contain 'term_id_to_index' and 'index_to_term_id' fields")

            self.term_id_to_index = mapping_data['term_id_to_index']
            self.index_to_term_id = mapping_data['index_to_term_id']

            # 检查嵌入维度是否匹配
            if 'embedding_dim' in mapping_data:
                loaded_dim = mapping_data['embedding_dim']
                if loaded_dim != self.embedding_dim:
                    logger.warning(f"Embedding dimension mismatch: "
                                   f"expected {self.embedding_dim}, loaded {loaded_dim}")
                    self.embedding_dim = loaded_dim

            logger.info(f"Index loaded from {index_path}")
            logger.info(f"Mapping loaded from {mapping_path}")
            logger.info(f"Loaded {self.index.ntotal} vectors")

        except Exception as e:
            logger.error(f"Error loading index: {e}")
            raise e

    def add_terms(self, new_embeddings: np.ndarray, new_term_ids: List[int]) -> None:
        """
        向现有索引添加新的术语

        Args:
            new_embeddings: 新术语的嵌入向量
            new_term_ids: 新术语的ID列表
        """
        if self.index is None:
            raise ValueError("No existing index. Please build index first.")

        if len(new_embeddings) != len(new_term_ids):
            raise ValueError(
                "new_embeddings and new_term_ids must have the same length")

        # 检查ID冲突
        for term_id in new_term_ids:
            if term_id in self.term_id_to_index:
                raise ValueError(f"Term ID {term_id} already exists in index")

        try:
            # 获取当前索引大小
            current_size = self.index.ntotal

            # 添加新向量
            new_embeddings_f32 = new_embeddings.astype(np.float32)
            self.index.add(new_embeddings_f32)

            # 更新ID映射
            for i, term_id in enumerate(new_term_ids):
                index_pos = current_size + i
                self.term_id_to_index[term_id] = index_pos
                self.index_to_term_id[index_pos] = term_id

            logger.info(f"Added {len(new_term_ids)} new terms to index")

        except Exception as e:
            logger.error(f"Error adding terms to index: {e}")
            raise e

    def remove_terms(self, term_ids_to_remove: List[int]) -> None:
        """
        从索引中移除术语（注意：这会重建整个索引）

        Args:
            term_ids_to_remove: 要移除的术语ID列表
        """
        if self.index is None:
            raise ValueError("No index available.")

        # 找出要保留的术语
        remaining_term_ids = []
        remaining_indices = []

        for term_id, index_pos in self.term_id_to_index.items():
            if term_id not in term_ids_to_remove:
                remaining_term_ids.append(term_id)
                remaining_indices.append(index_pos)

        if not remaining_term_ids:
            # 清空索引
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.term_id_to_index = {}
            self.index_to_term_id = {}
            logger.info("All terms removed, index cleared")
            return

        try:
            # 获取要保留的向量
            remaining_vectors = []
            for idx in remaining_indices:
                vector = self.index.reconstruct(idx)
                remaining_vectors.append(vector)

            remaining_embeddings = np.array(remaining_vectors)

            # 重建索引
            self.build_index(remaining_embeddings, remaining_term_ids)

            logger.info(f"Removed {len(term_ids_to_remove)} terms from index")

        except Exception as e:
            logger.error(f"Error removing terms from index: {e}")
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
            'index_type': 'IndexFlatIP' if self.index else None,
            'is_loaded': self.is_index_loaded()
        }

        return stats

    def is_index_loaded(self) -> bool:
        """
        检查索引是否已加载

        Returns:
            True如果索引已加载，否则False
        """
        return self.index is not None and self.index.ntotal > 0

    def get_term_by_id(self, term_id: int) -> Optional[np.ndarray]:
        """
        根据术语ID获取其嵌入向量

        Args:
            term_id: 术语ID

        Returns:
            嵌入向量，如果不存在返回None
        """
        if term_id not in self.term_id_to_index:
            return None

        try:
            index_pos = self.term_id_to_index[term_id]
            vector = self.index.reconstruct(index_pos)
            return vector
        except Exception as e:
            logger.error(f"Error retrieving term {term_id}: {e}")
            return None

    def get_similar_terms(self, term_id: int, top_k: int = 5,
                          threshold: float = 0.7) -> List[Tuple[int, float]]:
        """
        获取与指定术语相似的其他术语

        Args:
            term_id: 目标术语ID
            top_k: 返回的相似术语数量
            threshold: 相似度阈值

        Returns:
            相似术语列表: [(term_id, similarity), ...]
        """
        vector = self.get_term_by_id(term_id)
        if vector is None:
            return []

        # 搜索相似向量
        results = self.search_embeddings(
            vector.reshape(1, -1),
            top_k + 1,  # +1 因为结果会包含自己
            threshold
        )

        if not results or not results[0]:
            return []

        # 过滤掉自己
        similar_terms = [(tid, sim)
                         for tid, sim in results[0] if tid != term_id]
        return similar_terms[:top_k]
