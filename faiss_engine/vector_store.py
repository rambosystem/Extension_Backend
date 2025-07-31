import os
import numpy as np
import faiss
import pickle
import logging
from typing import List, Tuple, Optional, Dict
from pathlib import Path
from .embeddings import BGE_EmbeddingService

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    def __init__(self, index_path: str = "./faiss_indexes", embedding_dim: int = 1024,
                 auto_save_interval: int = 100):
        """
        初始化FAISS向量存储（增强持久化）

        Args:
            index_path: FAISS索引文件存储路径
            embedding_dim: 嵌入向量维度（BGE-M3默认1024）
            auto_save_interval: 自动保存间隔
        """
        self.index_path = Path(index_path)
        self.embedding_dim = embedding_dim
        self.auto_save_interval = auto_save_interval
        self.operation_count = 0  # 操作计数器

        self.index = None
        self.term_id_map = {}  # term_id -> index_position 映射
        self.index_term_map = {}  # index_position -> term_id 映射
        self.embedding_service = BGE_EmbeddingService()

        # 创建索引目录
        self.index_path.mkdir(parents=True, exist_ok=True)

        # 初始化或加载索引
        self._initialize_index()

        logger.info(f"FAISS Vector Store initialized with persistence enabled")
        logger.info(f"Index path: {self.index_path}")
        logger.info(f"Auto-save interval: {self.auto_save_interval}")

    def _initialize_index(self):
        """初始化或加载FAISS索引"""
        index_file = self.index_path / "faiss.index"
        mapping_file = self.index_path / "term_mapping.pkl"

        if index_file.exists() and mapping_file.exists():
            # 加载已存在的索引
            self._load_index()
        else:
            # 创建新的索引
            self._create_new_index()

    def _create_new_index(self):
        """创建新的FAISS索引"""
        logger.info("Creating new FAISS index")

        # 使用内积索引，适合归一化向量
        self.index = faiss.IndexFlatIP(self.embedding_dim)

        # 初始化映射
        self.term_id_map = {}
        self.index_term_map = {}

        logger.info(f"Created FAISS index with dimension {self.embedding_dim}")

    def _load_index(self):
        """加载已存在的FAISS索引"""
        try:
            index_file = self.index_path / "faiss.index"
            mapping_file = self.index_path / "term_mapping.pkl"

            # 加载FAISS索引
            self.index = faiss.read_index(str(index_file))

            # 加载ID映射
            with open(mapping_file, 'rb') as f:
                self.term_id_map = pickle.load(f)

            # 重建反向映射
            self.index_term_map = {v: k for k, v in self.term_id_map.items()}

            logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")

        except Exception as e:
            logger.error(f"Error loading index: {e}")
            logger.info("Creating new index as fallback")
            self._create_new_index()

    def _save_index(self):
        """保存FAISS索引到文件"""
        try:
            index_file = self.index_path / "faiss.index"
            mapping_file = self.index_path / "term_mapping.pkl"

            # 保存FAISS索引
            faiss.write_index(self.index, str(index_file))

            # 保存ID映射
            with open(mapping_file, 'wb') as f:
                pickle.dump(self.term_id_map, f)

            logger.info("FAISS index saved successfully")

        except Exception as e:
            logger.error(f"Error saving index: {e}")
            raise e

    def _check_auto_save(self):
        """检查是否需要自动保存"""
        self.operation_count += 1
        if self.operation_count % self.auto_save_interval == 0:
            logger.info(
                f"Auto-saving index after {self.operation_count} operations")
            self._save_index()

    def add_term(self, term_id: int, en: str, cn: Optional[str] = None, jp: Optional[str] = None) -> bool:
        """
        添加术语到向量索引

        Args:
            term_id: 术语ID
            en: 英文术语
            cn: 中文翻译
            jp: 日文翻译

        Returns:
            bool: 是否成功添加
        """
        try:
            # 检查是否已存在
            if term_id in self.term_id_map:
                logger.warning(f"Term {term_id} already exists in index")
                return False

            # 生成英文术语嵌入
            embedding = self.embedding_service.create_term_embedding(
                en, cn, jp)

            # 添加到FAISS索引
            embedding = embedding.reshape(1, -1)  # 确保是2D数组
            self.index.add(embedding)

            # 更新映射
            index_position = self.index.ntotal - 1
            self.term_id_map[term_id] = index_position
            self.index_term_map[index_position] = term_id

            # 检查自动保存
            self._check_auto_save()

            logger.info(
                f"Added term {term_id} to index at position {index_position}")
            return True

        except Exception as e:
            logger.error(f"Error adding term {term_id}: {e}")
            return False

    def remove_term(self, term_id: int) -> bool:
        """
        从向量索引中移除术语（标记删除）

        Args:
            term_id: 术语ID

        Returns:
            bool: 是否成功移除
        """
        try:
            if term_id not in self.term_id_map:
                logger.warning(f"Term {term_id} not found in index")
                return False

            # FAISS不支持直接删除，这里只移除映射
            # 实际删除需要重建索引
            index_position = self.term_id_map[term_id]
            del self.term_id_map[term_id]
            del self.index_term_map[index_position]

            logger.info(f"Removed term {term_id} from mappings")
            return True

        except Exception as e:
            logger.error(f"Error removing term {term_id}: {e}")
            return False

    def search_similar_terms(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Tuple[int, float]]:
        """
        搜索相似术语

        Args:
            query: 查询文本
            top_k: 返回最相似的k个结果
            threshold: 相似度阈值

        Returns:
            List[Tuple[int, float]]: [(term_id, similarity_score), ...]
        """
        try:
            if self.index.ntotal == 0:
                logger.warning("Index is empty")
                return []

            # 生成查询向量
            query_embedding = self.embedding_service.encode_dense(query)
            query_embedding = query_embedding.reshape(1, -1)

            # 搜索相似向量
            similarities, indices = self.index.search(
                query_embedding, min(top_k, self.index.ntotal))

            # 处理结果
            results = []
            for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
                if idx in self.index_term_map and similarity >= threshold:
                    term_id = self.index_term_map[idx]
                    results.append((term_id, float(similarity)))

            # 按相似度降序排序
            results.sort(key=lambda x: x[1], reverse=True)

            logger.info(
                f"Found {len(results)} similar terms for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Error searching for query '{query}': {e}")
            return []

    def rebuild_index(self, terms_data: List[Dict]) -> bool:
        """
        重建整个索引

        Args:
            terms_data: [{"term_id": int, "en": str, "cn": str, "jp": str}, ...]

        Returns:
            bool: 是否成功重建
        """
        try:
            logger.info(f"Rebuilding index with {len(terms_data)} terms")

            # 创建新索引
            self._create_new_index()

            # 批量添加术语（不自动保存，最后统一保存）
            success_count = 0
            for term_data in terms_data:
                try:
                    # 临时禁用自动保存，最后统一保存
                    term_id = term_data["term_id"]
                    en = term_data["en"]
                    cn = term_data.get("cn")
                    jp = term_data.get("jp")

                    # 检查是否已存在
                    if term_id in self.term_id_map:
                        continue

                    # 生成英文术语嵌入
                    embedding = self.embedding_service.create_term_embedding(
                        en, cn, jp)
                    embedding = embedding.reshape(1, -1)

                    # 添加到索引
                    self.index.add(embedding)

                    # 更新映射
                    index_position = self.index.ntotal - 1
                    self.term_id_map[term_id] = index_position
                    self.index_term_map[index_position] = term_id

                    success_count += 1

                except Exception as e:
                    logger.error(f"Error processing term {term_data}: {e}")
                    continue

            # 统一保存索引到持久化存储
            self._save_index()

            logger.info(
                f"Index rebuilt and saved successfully: {success_count}/{len(terms_data)} terms added")
            return True

        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
            return False

    def get_stats(self) -> Dict:
        """获取索引统计信息"""
        return {
            "total_vectors": self.index.ntotal if self.index else 0,
            "embedding_dimension": self.embedding_dim,
            "mapped_terms": len(self.term_id_map),
            "index_file_exists": (self.index_path / "faiss.index").exists(),
            "mapping_file_exists": (self.index_path / "term_mapping.pkl").exists()
        }

    def save(self):
        """手动保存索引"""
        self._save_index()
