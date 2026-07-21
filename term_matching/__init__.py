"""
术语匹配算法包

使用轻量字符串匹配器 StringTermMatcher（无模型、无 FAISS）：
归一化整词匹配、最长优先、不重叠，实时从数据库读取术语，无需预建索引。
"""

from term_matching.string_matcher import StringTermMatcher

__version__ = "2.0.0"

__all__ = ["StringTermMatcher"]
