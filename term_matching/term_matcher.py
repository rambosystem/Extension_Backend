"""
FAISS术语匹配器

基于FAISS + bge-large-en-v1.5模型的英文术语匹配算法，
支持多粒度匹配（1-3个词）和重叠去重处理。
集成智能批处理优化，使用最优批处理大小64。
"""

# 直接导入embeddings文件
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
import numpy as np
import time
import logging
from term_matching.text_preprocessor import TextPreprocessor
from term_matching.faiss_manager import FAISSManager
from term_matching.overlap_handler import OverlapHandler
from term_matching.embeddings_service import BGE_Large_EN_EmbeddingService
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'faiss_engine'))

# 添加父目录到路径以导入faiss_engine
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


logger = logging.getLogger(__name__)


class TermMatcher:
    """FAISS术语匹配器 - 集成智能批处理优化"""

    def __init__(self, model_path: str = None,
                 batch_size: int = 64, enable_stats: bool = True):
        """
        初始化术语匹配器（强制使用本地FAISS索引）

        Args:
            model_path: 预加载的BGE-Large-EN模型路径（可选，如果不提供则使用默认路径）
            batch_size: 批处理大小，默认64（经过优化的最优值）
            enable_stats: 是否启用性能统计，默认True
        """
        # 使用绝对路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if model_path is None:
            self.model_path = os.path.join(
                base_dir, "models", "bge-large-en-v1.5")
        else:
            self.model_path = model_path

        self.batch_size = batch_size
        self.enable_stats = enable_stats

        # 强制使用本地FAISS索引路径（绝对路径）
        self.index_path = os.path.join(
            base_dir, "faiss_indexes", "faiss.index")
        self.mapping_path = os.path.join(
            base_dir, "faiss_indexes", "term_mapping.pkl")

        # 初始化组件
        self.preprocessor = TextPreprocessor()
        self.faiss_manager = FAISSManager()  # 不需要model_path
        self.embedding_service = BGE_Large_EN_EmbeddingService(model_path)
        self.overlap_handler = OverlapHandler()

        # 强制加载本地FAISS索引
        self._load_local_index()

        # 性能统计
        self.stats = {
            'total_batches': 0,
            'total_embeddings': 0,
            'total_processing_time': 0.0,
            'total_encoding_time': 0.0,
            'total_search_time': 0.0,
            'total_overlap_time': 0.0
        }

        logger.info(f"TermMatcher initialized with batch_size={batch_size}")
        logger.info(f"Using local FAISS index: {self.index_path}")

    def _load_local_index(self):
        """
        强制加载本地FAISS索引
        """
        try:
            # 检查索引文件是否存在
            if not os.path.exists(self.index_path):
                logger.warning(
                    f"Local FAISS index not found: {self.index_path}. "
                    "TermMatcher will work without pre-built index."
                )
                return

            if not os.path.exists(self.mapping_path):
                logger.warning(
                    f"Local FAISS mapping not found: {self.mapping_path}. "
                    "TermMatcher will work without pre-built index."
                )
                return

            # 加载本地索引
            self.faiss_manager.load_index(self.index_path, self.mapping_path)

            logger.info(
                f"Successfully loaded local FAISS index with {self.faiss_manager.index.ntotal} vectors")

        except Exception as e:
            logger.warning(
                f"Failed to load local FAISS index: {e}. TermMatcher will work without pre-built index.")
            # 不抛出异常，允许服务启动

    def _collect_all_ngrams(self, input_texts: List[str], max_ngram: int = 3) -> Tuple[List[str], Dict[str, List[Tuple[str, int]]]]:
        """
        收集所有文本的n-grams，建立映射关系

        Args:
            input_texts: 输入文本列表
            max_ngram: 最大N-gram长度

        Returns:
            (all_ngrams, ngram_to_texts): 所有n-grams列表和n-gram到(原文本, 文本索引)的映射
        """
        all_ngrams = []
        ngram_to_texts = defaultdict(list)

        for text_idx, original_text in enumerate(input_texts):
            if not original_text or not original_text.strip():
                continue

            # 预处理文本
            ngrams = self.preprocessor.process_text(original_text, max_ngram)

            # 记录n-gram与原文本的关系
            for ngram in ngrams:
                all_ngrams.append(ngram)
                ngram_to_texts[ngram].append((original_text, text_idx))

        return all_ngrams, ngram_to_texts

    def _batch_encode_ngrams(self, all_ngrams: List[str]) -> List[np.ndarray]:
        """
        批量编码所有n-grams

        Args:
            all_ngrams: 所有n-grams列表

        Returns:
            编码后的向量列表
        """
        if not all_ngrams:
            return []

        start_time = time.time()

        # 分批编码
        embeddings = []
        for i in range(0, len(all_ngrams), self.batch_size):
            batch_ngrams = all_ngrams[i:i + self.batch_size]
            batch_embeddings = self.embedding_service.encode_dense(
                batch_ngrams)
            embeddings.extend(batch_embeddings)

            self.stats['total_batches'] += 1
            self.stats['total_embeddings'] += len(batch_ngrams)

            logger.debug(
                f"Encoded batch {self.stats['total_batches']}: {len(batch_ngrams)} n-grams")

        encoding_time = time.time() - start_time
        self.stats['total_encoding_time'] += encoding_time

        logger.info(
            f"Batch encoding completed: {len(all_ngrams)} n-grams in {encoding_time:.3f}s")
        return embeddings

    def _batch_search_embeddings(self, embeddings: List[np.ndarray], top_k: int) -> List[List[Tuple[float, int]]]:
        """
        批量搜索所有嵌入向量

        Args:
            embeddings: 嵌入向量列表
            top_k: 每个查询返回的最大结果数

        Returns:
            搜索结果列表，每个元素为(相似度, term_id)的列表
        """
        if not embeddings:
            return []

        start_time = time.time()

        # 将embeddings列表转换为numpy数组
        embeddings_array = np.array(embeddings)

        # 使用新的search_embeddings方法进行批量搜索
        search_results = self.faiss_manager.search_embeddings(
            embeddings_array, top_k, threshold=0.0  # 不在这里过滤阈值，在后续步骤中过滤
        )

        search_time = time.time() - start_time
        self.stats['total_search_time'] += search_time

        logger.debug(
            f"Batch search completed: {len(embeddings)} vectors in {search_time:.3f}s")
        return search_results

    def _build_matches_by_text(self, all_ngrams: List[str], search_results: List[List[Tuple[float, int]]],
                               ngram_to_texts: Dict[str, List[Tuple[str, int]]],
                               similarity_threshold: float) -> Dict[int, List[Dict]]:
        """
        按原文本构建匹配结果

        Args:
            all_ngrams: 所有n-grams列表
            search_results: 搜索结果列表
            ngram_to_texts: n-gram到原文本的映射
            similarity_threshold: 相似度阈值

        Returns:
            按文本索引分组的匹配结果
        """
        matches_by_text = defaultdict(list)

        for i, (ngram, results) in enumerate(zip(all_ngrams, search_results)):
            # 过滤相似度阈值
            filtered_results = [
                (term_id, sim) for term_id, sim in results if sim >= similarity_threshold]

            if not filtered_results:
                continue

            # 为每个匹配结果创建记录
            for term_id, similarity in filtered_results:
                # 获取所有包含此n-gram的原文本
                for original_text, text_idx in ngram_to_texts[ngram]:
                    match_info = {
                        'term_id': term_id,
                        'ngram': ngram,
                        'similarity': similarity,
                        'original_text': original_text,
                        'ngram_length': len(ngram.split())
                    }
                    matches_by_text[text_idx].append(match_info)

        return matches_by_text

    def build_index_from_terms(self, terms_data: List[Dict]) -> None:
        """
        从术语数据构建FAISS索引并保存到本地路径

        Args:
            terms_data: 术语数据列表，格式为[{"term_id": int, "en": str}, ...]
        """
        if not terms_data:
            raise ValueError("terms_data cannot be empty")

        try:
            # 提取术语文本和ID
            term_texts = []
            term_ids = []

            for term in terms_data:
                if "term_id" not in term or "en" not in term:
                    raise ValueError(
                        "Each term must contain 'term_id' and 'en' fields")

                term_texts.append(term["en"])
                term_ids.append(term["term_id"])

            # 使用embedding_service编码术语文本
            term_embeddings = self.embedding_service.encode_dense(term_texts)

            # 构建FAISS索引
            self.faiss_manager.build_index(term_embeddings, term_ids)

            # 自动保存到本地索引路径
            self.faiss_manager.save_index(self.index_path, self.mapping_path)

            logger.info(
                f"Index built and saved to local path for {len(terms_data)} terms")

        except Exception as e:
            logger.error(f"Error building index: {e}")
            raise e

    def load_index(self, index_path: str = None, mapping_path: str = None) -> None:
        """
        加载预构建的FAISS索引（默认使用本地路径）

        Args:
            index_path: FAISS索引文件路径，默认使用本地路径
            mapping_path: ID映射文件路径，默认使用本地路径
        """
        if index_path is None:
            index_path = self.index_path
        if mapping_path is None:
            mapping_path = self.mapping_path

        try:
            self.faiss_manager.load_index(index_path, mapping_path)
            logger.info(f"Index loaded from {index_path}")
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            raise e

    def save_index(self, index_path: str = None, mapping_path: str = None) -> None:
        """
        保存FAISS索引到文件（默认使用本地路径）

        Args:
            index_path: FAISS索引文件保存路径，默认使用本地路径
            mapping_path: ID映射文件保存路径，默认使用本地路径
        """
        if index_path is None:
            index_path = self.index_path
        if mapping_path is None:
            mapping_path = self.mapping_path

        try:
            self.faiss_manager.save_index(index_path, mapping_path)
            logger.info(f"Index saved to {index_path}")
        except Exception as e:
            logger.error(f"Error saving index: {e}")
            raise e

    def add_terms_to_index(self, new_terms_data: List[Dict]) -> None:
        """
        向现有索引添加新的术语（增量更新）

        Args:
            new_terms_data: 新术语数据列表，格式为[{"term_id": int, "en": str}, ...]
        """
        if not new_terms_data:
            logger.warning("No new terms to add")
            return

        if not self.faiss_manager.is_index_loaded():
            raise ValueError(
                "No index available. Please build or load index first.")

        try:
            # 提取新术语的文本和ID
            new_term_texts = []
            new_term_ids = []

            for term in new_terms_data:
                if "term_id" not in term or "en" not in term:
                    raise ValueError(
                        "Each term must contain 'term_id' and 'en' fields")

                new_term_texts.append(term["en"])
                new_term_ids.append(term["term_id"])

            # 检查ID冲突
            existing_ids = set(self.faiss_manager.term_id_to_index.keys())
            conflicting_ids = [
                tid for tid in new_term_ids if tid in existing_ids]
            if conflicting_ids:
                raise ValueError(
                    f"Term IDs already exist in index: {conflicting_ids}")

            # 编码新术语
            logger.info(f"Encoding {len(new_terms_data)} new terms...")
            new_embeddings = self.embedding_service.encode_dense(
                new_term_texts)

            # 添加到现有索引
            logger.info(f"Adding {len(new_terms_data)} new terms to index...")
            self.faiss_manager.add_terms(new_embeddings, new_term_ids)

            # 自动保存更新后的索引
            self.faiss_manager.save_index(self.index_path, self.mapping_path)

            logger.info(
                f"Successfully added {len(new_terms_data)} new terms to index")

        except Exception as e:
            logger.error(f"Error adding terms to index: {e}")
            raise e

    def get_index_stats(self) -> Dict:
        """
        获取索引统计信息

        Returns:
            索引统计信息字典
        """
        if not self.faiss_manager.is_index_loaded():
            return {"error": "No index loaded"}

        return self.faiss_manager.get_stats()

    def match_terms(self, input_texts: List[str], similarity_threshold: float = 0.7,
                    top_k: int = 10, max_ngram: int = 3) -> List[List[int]]:
        """
        智能批处理匹配术语的主函数

        Args:
            input_texts: 输入文本列表
            similarity_threshold: 相似度阈值
            top_k: 每个查询返回的最大结果数
            max_ngram: 最大N-gram长度

        Returns:
            匹配结果列表，每个输入文本对应一个term_id列表
        """
        if not input_texts:
            return []

        if not self.faiss_manager.is_index_loaded():
            raise ValueError(
                "No index available. Please build or load index first.")

        start_time = time.time()

        try:
            # 1. 收集所有n-grams
            logger.info(f"Collecting n-grams from {len(input_texts)} texts...")
            all_ngrams, ngram_to_texts = self._collect_all_ngrams(
                input_texts, max_ngram)

            if not all_ngrams:
                logger.warning("No n-grams found in input texts")
                return [[] for _ in input_texts]

            logger.info(f"Collected {len(all_ngrams)} unique n-grams")

            # 2. 批量编码所有n-grams
            embeddings = self._batch_encode_ngrams(all_ngrams)

            # 3. 批量搜索所有嵌入向量
            search_results = self._batch_search_embeddings(embeddings, top_k)

            # 4. 按原文本构建匹配结果
            matches_by_text = self._build_matches_by_text(
                all_ngrams, search_results, ngram_to_texts, similarity_threshold
            )

            # 5. 对每个文本进行重叠去重处理
            overlap_start = time.time()
            final_results = []

            for text_idx in range(len(input_texts)):
                if text_idx in matches_by_text:
                    text_matches = matches_by_text[text_idx]
                    # 重叠去重
                    deduplicated_matches = self.overlap_handler.remove_overlaps_with_positions(
                        text_matches)
                    # 提取term_id
                    term_ids = [match['term_id']
                                for match in deduplicated_matches]
                    final_results.append(term_ids)
                else:
                    final_results.append([])

            overlap_time = time.time() - overlap_start
            self.stats['total_overlap_time'] += overlap_time

            # 6. 更新统计信息
            processing_time = time.time() - start_time
            self.stats['total_processing_time'] += processing_time

            logger.info(
                f"Batch processing completed: {len(input_texts)} texts → {sum(len(r) for r in final_results)} matched terms in {processing_time:.3f}s")

            return final_results

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise e

    def match_terms_detailed(self, input_texts: List[str], similarity_threshold: float = 0.7,
                             top_k: int = 10, max_ngram: int = 3) -> List[List[Dict]]:
        """
        智能批处理详细匹配函数

        Args:
            input_texts: 输入文本列表
            similarity_threshold: 相似度阈值
            top_k: 每个N-gram返回的最大结果数
            max_ngram: 最大N-gram长度

        Returns:
            详细匹配结果列表，包含N-gram、相似度等信息
        """
        if not input_texts:
            return []

        if not self.faiss_manager.is_index_loaded():
            raise ValueError(
                "No index available. Please build or load index first.")

        start_time = time.time()

        try:
            # 1. 收集所有n-grams
            all_ngrams, ngram_to_texts = self._collect_all_ngrams(
                input_texts, max_ngram)

            if not all_ngrams:
                return [[] for _ in input_texts]

            # 2. 批量编码所有n-grams
            embeddings = self._batch_encode_ngrams(all_ngrams)

            # 3. 批量搜索所有嵌入向量
            search_results = self._batch_search_embeddings(embeddings, top_k)

            # 4. 按原文本构建匹配结果
            matches_by_text = self._build_matches_by_text(
                all_ngrams, search_results, ngram_to_texts, similarity_threshold
            )

            # 5. 对每个文本进行重叠去重处理
            final_results = []

            for text_idx in range(len(input_texts)):
                if text_idx in matches_by_text:
                    text_matches = matches_by_text[text_idx]
                    # 重叠去重
                    deduplicated_matches = self.overlap_handler.remove_overlaps_with_positions(
                        text_matches)
                    final_results.append(deduplicated_matches)
                else:
                    final_results.append([])

            processing_time = time.time() - start_time
            self.stats['total_processing_time'] += processing_time

            logger.info(
                f"Detailed batch processing completed: {len(input_texts)} texts in {processing_time:.3f}s")

            return final_results

        except Exception as e:
            logger.error(f"Detailed batch processing failed: {e}")
            raise e

    def get_stats(self) -> Dict:
        """
        获取系统统计信息

        Returns:
            统计信息字典
        """
        stats = {
            'faiss_stats': self.faiss_manager.get_stats(),
            'stop_words_count': len(self.preprocessor.stop_words),
            'batch_size': self.batch_size,
            'batch_processing_enabled': True
        }

        # 添加性能统计
        if self.enable_stats:
            stats['performance_stats'] = self.stats.copy()

            # 计算平均性能指标
            if self.stats['total_batches'] > 0:
                stats['performance_stats'].update({
                    'avg_embeddings_per_batch': self.stats['total_embeddings'] / self.stats['total_batches'],
                    'avg_encoding_time_per_batch': self.stats['total_encoding_time'] / self.stats['total_batches'],
                    'avg_processing_time_per_text': self.stats['total_processing_time'] / max(1, self.stats['total_embeddings'])
                })

        return stats

    def reset_stats(self) -> None:
        """重置性能统计信息"""
        self.stats = {
            'total_batches': 0,
            'total_embeddings': 0,
            'total_processing_time': 0.0,
            'total_encoding_time': 0.0,
            'total_search_time': 0.0,
            'total_overlap_time': 0.0
        }
        logger.info("Performance stats reset")

    def optimize_batch_size(self, sample_texts: List[str], max_tests: int = 5) -> int:
        """
        优化批处理大小

        Args:
            sample_texts: 样本文本列表
            max_tests: 最大测试次数

        Returns:
            最优批处理大小
        """
        logger.info("Optimizing batch size...")

        # 测试不同的批处理大小
        batch_sizes = [16, 32, 64, 128, 256]
        results = []

        for batch_size in batch_sizes[:max_tests]:
            original_batch_size = self.batch_size
            self.batch_size = batch_size
            self.reset_stats()

            try:
                start_time = time.time()
                self.match_terms(sample_texts, similarity_threshold=0.7)
                processing_time = time.time() - start_time

                results.append({
                    'batch_size': batch_size,
                    'processing_time': processing_time,
                    'total_embeddings': self.stats['total_embeddings'],
                    'total_batches': self.stats['total_batches']
                })

                logger.info(
                    f"Batch size {batch_size}: {processing_time:.3f}s, {self.stats['total_batches']} batches")

            except Exception as e:
                logger.warning(f"Batch size {batch_size} failed: {e}")
                continue
            finally:
                self.batch_size = original_batch_size

        if not results:
            logger.warning("No valid results for batch size optimization")
            return 64  # 默认值

        # 选择处理时间最短的批处理大小
        best_result = min(results, key=lambda x: x['processing_time'])
        optimal_batch_size = best_result['batch_size']

        logger.info(f"Optimal batch size: {optimal_batch_size}")
        self.batch_size = optimal_batch_size

        return optimal_batch_size
