"""
主匹配算法类

整合所有模块，提供统一的术语匹配接口：
- 文本预处理和N-gram生成
- FAISS向量搜索
- 重叠去重处理
- 批量查询支持
"""

import logging
from typing import List, Dict, Optional, Tuple
from text_preprocessor import TextPreprocessor
from faiss_manager import FAISSManager
from overlap_handler import OverlapHandler

logger = logging.getLogger(__name__)


class TermMatcher:
    """术语匹配器主类"""

    def __init__(self, model_path: str = "../models/bge-large-en-v1.5"):
        """
        初始化术语匹配器

        Args:
            model_path: 预加载的BGE-Large-EN模型路径
        """
        self.preprocessor = TextPreprocessor()
        self.faiss_manager = FAISSManager(model_path)
        self.overlap_handler = OverlapHandler()

        logger.info("TermMatcher initialized successfully")

    def build_index_from_terms(self, terms_data: List[Dict]) -> None:
        """
        从术语数据构建FAISS索引

        Args:
            terms_data: 术语数据列表，格式为 [{"term_id": int, "en": str}, ...]
        """
        if not terms_data:
            raise ValueError("terms_data cannot be empty")

        try:
            # 提取术语文本和ID
            term_texts = []
            term_ids = []

            for term in terms_data:
                if 'term_id' not in term or 'en' not in term:
                    raise ValueError(
                        "Each term must contain 'term_id' and 'en' fields")

                term_id = term['term_id']
                term_text = term['en'].strip()

                if not term_text:
                    logger.warning(
                        f"Skipping empty term text for term_id: {term_id}")
                    continue

                term_texts.append(term_text)
                term_ids.append(term_id)

            if not term_texts:
                raise ValueError("No valid term texts found")

            # 构建FAISS索引
            self.faiss_manager.build_index(term_texts, term_ids)

            logger.info(
                f"Index built successfully for {len(term_texts)} terms")

        except Exception as e:
            logger.error(f"Error building index from terms: {e}")
            raise e

    def load_index(self, index_path: str, mapping_path: str) -> None:
        """
        加载预构建的索引

        Args:
            index_path: FAISS索引文件路径
            mapping_path: ID映射文件路径
        """
        try:
            self.faiss_manager.load_index(index_path, mapping_path)
            logger.info("Index loaded successfully")
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            raise e

    def save_index(self, index_path: str, mapping_path: str) -> None:
        """
        保存当前索引到文件

        Args:
            index_path: FAISS索引文件路径
            mapping_path: ID映射文件路径
        """
        try:
            self.faiss_manager.save_index(index_path, mapping_path)
            logger.info("Index saved successfully")
        except Exception as e:
            logger.error(f"Error saving index: {e}")
            raise e

    def match_terms(self, input_texts: List[str], similarity_threshold: float = 0.7,
                    top_k: int = 10, max_ngram: int = 3) -> List[List[int]]:
        """
        主匹配函数

        Args:
            input_texts: 输入文本列表
            similarity_threshold: 相似度阈值，默认0.7
            top_k: 每个N-gram返回的最大结果数，默认10
            max_ngram: 最大N-gram长度，默认3

        Returns:
            匹配结果列表，每个输入文本对应一个term_id列表
        """
        if not input_texts:
            return []

        if not self.faiss_manager.is_index_loaded():
            raise ValueError(
                "No index available. Please build or load index first.")

        try:
            results = []

            for input_text in input_texts:
                if not input_text or not input_text.strip():
                    results.append([])
                    continue

                # 1. 文本预处理和N-gram生成
                ngrams = self.preprocessor.process_text(input_text, max_ngram)

                if not ngrams:
                    results.append([])
                    continue

                # 2. 批量编码所有N-gram
                # 这里我们直接使用FAISS搜索，它会自动编码

                # 3. FAISS搜索匹配
                search_results = self.faiss_manager.search(
                    ngrams, top_k=top_k, threshold=similarity_threshold
                )

                # 4. 处理搜索结果，准备重叠去重
                all_matches = []
                for i, ngram in enumerate(ngrams):
                    ngram_results = search_results[i]
                    for term_id, similarity in ngram_results:
                        match_info = {
                            'term_id': term_id,
                            'ngram': ngram,
                            'similarity': similarity,
                            'original_text': input_text
                        }
                        all_matches.append(match_info)

                # 5. 重叠去重处理
                if all_matches:
                    final_term_ids = self.overlap_handler.remove_overlaps(
                        all_matches)
                else:
                    final_term_ids = []

                results.append(final_term_ids)

            logger.info(
                f"Term matching completed for {len(input_texts)} input texts")
            return results

        except Exception as e:
            logger.error(f"Error in term matching: {e}")
            raise e

    def match_terms_detailed(self, input_texts: List[str], similarity_threshold: float = 0.7,
                             top_k: int = 10, max_ngram: int = 3) -> List[List[Dict]]:
        """
        详细匹配函数，返回更多信息

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

        try:
            results = []

            for input_text in input_texts:
                if not input_text or not input_text.strip():
                    results.append([])
                    continue

                # 1. 文本预处理和N-gram生成
                ngrams = self.preprocessor.process_text(input_text, max_ngram)

                if not ngrams:
                    results.append([])
                    continue

                # 2. FAISS搜索匹配
                search_results = self.faiss_manager.search(
                    ngrams, top_k=top_k, threshold=similarity_threshold
                )

                # 3. 处理搜索结果
                all_matches = []
                for i, ngram in enumerate(ngrams):
                    ngram_results = search_results[i]
                    for term_id, similarity in ngram_results:
                        match_info = {
                            'term_id': term_id,
                            'ngram': ngram,
                            'similarity': similarity,
                            'original_text': input_text,
                            'ngram_length': len(ngram.split())
                        }
                        all_matches.append(match_info)

                # 4. 重叠去重处理（带位置信息）
                if all_matches:
                    final_matches = self.overlap_handler.remove_overlaps_with_positions(
                        all_matches)
                else:
                    final_matches = []

                results.append(final_matches)

            logger.info(
                f"Detailed term matching completed for {len(input_texts)} input texts")
            return results

        except Exception as e:
            logger.error(f"Error in detailed term matching: {e}")
            raise e

    def get_stats(self) -> Dict:
        """
        获取匹配器统计信息

        Returns:
            统计信息字典
        """
        faiss_stats = self.faiss_manager.get_stats()

        stats = {
            'faiss_stats': faiss_stats,
            'stop_words_count': len(self.preprocessor.get_stop_words()),
            'index_loaded': self.faiss_manager.is_index_loaded()
        }

        return stats

    def update_stop_words(self, add_words: Optional[List[str]] = None,
                          remove_words: Optional[List[str]] = None) -> None:
        """
        更新停用词列表

        Args:
            add_words: 要添加的停用词列表
            remove_words: 要移除的停用词列表
        """
        if add_words:
            self.preprocessor.add_stop_words(add_words)
            logger.info(f"Added {len(add_words)} stop words")

        if remove_words:
            self.preprocessor.remove_stop_words(remove_words)
            logger.info(f"Removed {len(remove_words)} stop words")

    def test_overlap_detection(self, text: str, ngram1: str, ngram2: str) -> bool:
        """
        测试重叠检测功能

        Args:
            text: 原始文本
            ngram1: 第一个N-gram
            ngram2: 第二个N-gram

        Returns:
            True表示有重叠
        """
        return self.overlap_handler.detect_overlap(ngram1, ngram2, text)
