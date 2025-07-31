"""
文本预处理模块

提供英文文本的预处理功能，包括：
- 停用词过滤
- 文本分词
- N-gram生成
- 标点符号和特殊字符清理
"""

import re
import string
from typing import List, Set
import nltk
from nltk.corpus import stopwords

# 下载NLTK数据（如果未下载）
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')


class TextPreprocessor:
    """文本预处理器"""

    def __init__(self):
        """初始化文本预处理器"""
        # 加载英文停用词
        self.stop_words = set(stopwords.words('english'))

        # 添加一些常见的停用词
        additional_stop_words = {
            'would', 'could', 'should', 'might', 'may', 'can', 'will',
            'shall', 'must', 'ought', 'need', 'dare', 'used'
        }
        self.stop_words.update(additional_stop_words)

        # 编译正则表达式用于清理文本
        self.clean_pattern = re.compile(r'[^\w\s]')
        self.space_pattern = re.compile(r'\s+')

    def clean_text(self, text: str) -> str:
        """
        清理文本，去除标点符号，转换为小写

        Args:
            text: 输入文本

        Returns:
            清理后的文本
        """
        if not text:
            return ""

        # 转换为小写
        text = text.lower()

        # 去除标点符号和特殊字符
        text = self.clean_pattern.sub(' ', text)

        # 去除多余空格
        text = self.space_pattern.sub(' ', text)

        # 去除首尾空格
        text = text.strip()

        return text

    def tokenize(self, text: str) -> List[str]:
        """
        分词并过滤停用词

        Args:
            text: 输入文本

        Returns:
            分词后的词列表
        """
        if not text:
            return []

        # 清理文本
        cleaned_text = self.clean_text(text)

        # 分词
        tokens = cleaned_text.split()

        # 过滤停用词和空字符串
        filtered_tokens = [
            token for token in tokens
            if token and token not in self.stop_words and len(token) > 1
        ]

        return filtered_tokens

    def generate_ngrams(self, tokens: List[str], max_n: int = 3) -> List[str]:
        """
        生成1-gram到max_n-gram的所有组合

        Args:
            tokens: 分词后的词列表
            max_n: 最大N-gram长度，默认为3

        Returns:
            N-gram列表，格式: ["word1", "word1 word2", "word1 word2 word3", ...]
        """
        if not tokens:
            return []

        ngrams = []

        # 生成1-gram到max_n-gram
        for n in range(1, min(max_n + 1, len(tokens) + 1)):
            for i in range(len(tokens) - n + 1):
                ngram = ' '.join(tokens[i:i + n])
                ngrams.append(ngram)

        return ngrams

    def process_text(self, text: str, max_n: int = 3) -> List[str]:
        """
        完整的文本处理流程：清理 -> 分词 -> 生成N-gram

        Args:
            text: 输入文本
            max_n: 最大N-gram长度

        Returns:
            处理后的N-gram列表
        """
        tokens = self.tokenize(text)
        ngrams = self.generate_ngrams(tokens, max_n)
        return ngrams

    def get_stop_words(self) -> Set[str]:
        """
        获取停用词列表

        Returns:
            停用词集合
        """
        return self.stop_words.copy()

    def add_stop_words(self, words: List[str]) -> None:
        """
        添加自定义停用词

        Args:
            words: 要添加的停用词列表
        """
        self.stop_words.update(words)

    def remove_stop_words(self, words: List[str]) -> None:
        """
        移除停用词

        Args:
            words: 要移除的停用词列表
        """
        self.stop_words.difference_update(words)
