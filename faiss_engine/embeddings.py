import os
import numpy as np
from typing import List, Union, Optional, Dict
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class BGE_Large_EN_EmbeddingService:
    def __init__(self, model_path: str = "./models/bge-large-en-v1.5"):
        """
        初始化BGE-Large-EN嵌入服务（使用预加载模型）

        Args:
            model_path: 预加载的BGE-Large-EN模型路径
        """
        self.model_path = model_path
        self.model = None
        self.embedding_dim = 1024  # BGE-Large-EN的嵌入维度

        # 确保模型路径存在
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path not found: {model_path}")

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

    def encode_dense(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        使用BGE-Large-EN生成密集向量嵌入

        Args:
            texts: 单个文本或文本列表

        Returns:
            numpy数组形式的嵌入向量
        """
        if isinstance(texts, str):
            texts = [texts]

        try:
            # 使用SentenceTransformer生成embedding
            embeddings = self.model.encode(
                texts,
                batch_size=32,
                normalize_embeddings=True  # 自动归一化
            )

            return np.array(embeddings).astype(np.float32)

        except Exception as e:
            logger.error(f"Error encoding texts: {e}")
            raise e

    def get_embedding_dimension(self) -> int:
        """获取嵌入维度"""
        return self.embedding_dim

    def create_term_embedding(self, en: str, cn: Optional[str] = None, jp: Optional[str] = None) -> np.ndarray:
        """
        为术语创建嵌入向量（仅英文）

        Args:
            en: 英文术语
            cn: 中文翻译（保留参数但不使用）
            jp: 日文翻译（保留参数但不使用）

        Returns:
            英文术语的嵌入向量
        """
        # 只对英文术语生成embedding
        embedding = self.encode_dense(en)

        return embedding[0].astype(np.float32)  # 返回单个文本的embedding


# 为了保持向后兼容，保留原来的类名作为别名
BGE_M3EmbeddingService = BGE_Large_EN_EmbeddingService
