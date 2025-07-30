import os
import numpy as np
from typing import List, Union, Optional
from FlagEmbedding import BGEM3FlagModel
from dotenv import load_dotenv
import logging

load_dotenv()

# 设置离线模式环境变量
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

logger = logging.getLogger(__name__)


class BGE_M3EmbeddingService:
    def __init__(self, model_name: str = "BAAI/bge-m3", cache_dir: str = "./model_cache"):
        """
        初始化BGE-M3嵌入服务（离线模式）

        Args:
            model_name: BGE-M3模型名称，默认使用 BAAI/bge-m3
            cache_dir: 模型缓存目录
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.model = None
        self.embedding_dim = 1024  # BGE-M3的嵌入维度

        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)

        self._load_model()

    def _load_model(self):
        """加载BGE-M3模型（离线模式）"""
        try:
            logger.info(
                f"Loading BGE-M3 model in OFFLINE mode: {self.model_name}")
            logger.info(f"Model cache directory: {self.cache_dir}")

            self.model = BGEM3FlagModel(
                self.model_name,
                use_fp16=True,  # 使用半精度浮点数节省内存
                device='cpu',   # 可以改为 'cuda' 如果有GPU
                cache_folder=self.cache_dir  # 指定缓存目录
            )
            logger.info("BGE-M3 model loaded successfully in offline mode")
        except Exception as e:
            logger.error(f"Error loading BGE-M3 model: {e}")
            raise e

    def encode_dense(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        使用BGE-M3生成密集向量嵌入

        Args:
            texts: 单个文本或文本列表

        Returns:
            numpy数组形式的嵌入向量
        """
        if isinstance(texts, str):
            texts = [texts]

        try:
            # BGE-M3支持多种嵌入类型，这里使用dense embedding
            embeddings = self.model.encode(
                texts,
                batch_size=32,
                max_length=512,  # BGE-M3支持最大512长度
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False
            )['dense_vecs']

            return np.array(embeddings).astype(np.float32)

        except Exception as e:
            logger.error(f"Error encoding texts: {e}")
            raise e

    def encode_sparse(self, texts: Union[str, List[str]]) -> dict:
        """
        使用BGE-M3生成稀疏向量嵌入（用于关键词匹配）

        Args:
            texts: 单个文本或文本列表

        Returns:
            稀疏向量字典
        """
        if isinstance(texts, str):
            texts = [texts]

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=32,
                max_length=512,
                return_dense=False,
                return_sparse=True,
                return_colbert_vecs=False
            )['lexical_weights']

            return embeddings

        except Exception as e:
            logger.error(f"Error encoding sparse texts: {e}")
            raise e

    def encode_multi_vector(self, texts: Union[str, List[str]]) -> dict:
        """
        使用BGE-M3生成多向量嵌入（ColBERT风格，用于精细匹配）

        Args:
            texts: 单个文本或文本列表

        Returns:
            多向量嵌入字典
        """
        if isinstance(texts, str):
            texts = [texts]

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=32,
                max_length=512,
                return_dense=False,
                return_sparse=False,
                return_colbert_vecs=True
            )['colbert_vecs']

            return embeddings

        except Exception as e:
            logger.error(f"Error encoding multi-vector texts: {e}")
            raise e

    def encode_all(self, texts: Union[str, List[str]]) -> dict:
        """
        使用BGE-M3生成所有类型的嵌入

        Args:
            texts: 单个文本或文本列表

        Returns:
            包含所有嵌入类型的字典
        """
        if isinstance(texts, str):
            texts = [texts]

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=32,
                max_length=512,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=True
            )

            return {
                'dense': np.array(embeddings['dense_vecs']).astype(np.float32),
                'sparse': embeddings['lexical_weights'],
                'colbert': embeddings['colbert_vecs']
            }

        except Exception as e:
            logger.error(f"Error encoding all embedding types: {e}")
            raise e

    def get_embedding_dimension(self) -> int:
        """获取嵌入维度"""
        return self.embedding_dim

    def create_term_embedding(self, en: str, cn: Optional[str] = None, jp: Optional[str] = None) -> np.ndarray:
        """
        为术语创建嵌入向量（多语言融合）

        Args:
            en: 英文术语
            cn: 中文翻译
            jp: 日文翻译

        Returns:
            融合后的嵌入向量
        """
        # 构建多语言文本
        texts = [en]
        if cn:
            texts.append(cn)
        if jp:
            texts.append(jp)

        # 为每种语言生成嵌入
        embeddings = []
        for text in texts:
            emb = self.encode_dense(text)
            embeddings.append(emb[0])  # 取第一个（单个文本的结果）

        # 计算平均嵌入（简单融合策略）
        if len(embeddings) > 1:
            fused_embedding = np.mean(embeddings, axis=0)
        else:
            fused_embedding = embeddings[0]

        return fused_embedding.astype(np.float32)
