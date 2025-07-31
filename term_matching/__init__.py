"""
FAISS术语匹配算法包

提供基于FAISS + bge-large-en-v1.5模型的英文术语匹配功能，
支持多粒度匹配（1-3个词）和重叠去重处理。
"""

from .term_matcher import TermMatcher
from .text_preprocessor import TextPreprocessor
from .faiss_manager import FAISSManager
from .overlap_handler import OverlapHandler

__version__ = "1.0.0"
__all__ = [
    "TermMatcher",
    "TextPreprocessor",
    "FAISSManager",
    "OverlapHandler"
]
