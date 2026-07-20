"""
轻量术语匹配器（字符串 / 近似匹配）

替代原来的 BGE-Large + FAISS 语义方案：
- 不加载任何模型，不依赖 FAISS 索引文件
- 直接对输入文本做归一化后的整词匹配
- 归一化天然吸收「大小写 / 多余空格 / 标点」差异
- 匹配采用「最长优先、不重叠」，与原 OverlapHandler 的语义一致

适用前提：术语是明确的词/短语（产品名词等），只需字面 / 近似匹配，
不需要语义泛化。术语量小、直接实时构建匹配器，无需预建索引。
"""

import re
import logging
from typing import List, Iterable, Tuple

logger = logging.getLogger(__name__)

# 归一化：非字母数字（含下划线）统一视为分隔
_NON_WORD = re.compile(r"[^0-9a-z]+")


def normalize(text: str) -> str:
    """小写化 + 非字母数字折叠为单个空格 + 去首尾空格"""
    if not text:
        return ""
    return _NON_WORD.sub(" ", text.lower()).strip()


class _NoIndexManager:
    """兼容旧 faiss_manager 接口的空壳（已无 FAISS 索引）"""
    term_id_to_index = {}

    def is_index_loaded(self) -> bool:
        return False


class StringTermMatcher:
    """基于正则整词匹配的术语匹配器（无模型、无 FAISS）"""

    def __init__(self):
        # 缓存：term 集合签名 -> (编译后的正则, 归一化词 -> term_id 列表)
        self._cache_key = None
        self._pattern = None
        self._norm_to_ids = {}
        # 兼容旧路由中对 matcher.faiss_manager 的属性访问
        self.faiss_manager = _NoIndexManager()
        logger.info("StringTermMatcher initialized (no model, no FAISS)")

    # ---- 兼容旧接口的空操作（匹配已实时读 DB，无需维护索引） ----
    def remove_terms_from_index(self, *args, **kwargs) -> None:
        """兼容旧调用：实时匹配无需维护索引，空操作。"""
        return None

    def add_terms_to_index(self, *args, **kwargs) -> None:
        """兼容旧调用：实时匹配无需维护索引，空操作。"""
        return None

    def build_index_from_terms(self, *args, **kwargs) -> None:
        """兼容旧调用：实时匹配无需预建索引，空操作。"""
        return None

    def get_stats(self, *args, **kwargs) -> dict:
        """兼容旧接口：返回匹配器说明信息。"""
        return {"engine": "string-match", "model": None, "faiss": False}

    def get_index_stats(self, *args, **kwargs) -> dict:
        """兼容旧接口：无 FAISS 索引。"""
        return {"engine": "string-match", "total_vectors": 0, "faiss": False}

    def _build(self, terms: List[Tuple[int, str]]) -> None:
        """根据术语列表构建正则匹配器（按签名缓存，避免重复编译）"""
        # 签名：术语 (id, 归一化文本) 的有序元组
        norm_terms = []
        norm_to_ids = {}
        for term_id, en in terms:
            n = normalize(en)
            if not n:
                continue
            norm_terms.append((n, term_id))
            norm_to_ids.setdefault(n, []).append(term_id)

        key = tuple(sorted((n, tid) for n, tid in norm_terms))
        if key == self._cache_key:
            return  # 术语未变化，复用已编译的正则

        if not norm_to_ids:
            self._cache_key = key
            self._pattern = None
            self._norm_to_ids = {}
            return

        # 最长优先：更长的短语排在前面，保证整体最长匹配（如
        # "budget scheduler" 优先于 "scheduler"）
        uniq_norms = sorted(norm_to_ids.keys(), key=len, reverse=True)
        # \b 词边界，避免 "agent" 命中 "agentic" 之类
        pattern = re.compile(
            r"\b(?:" + "|".join(re.escape(n) for n in uniq_norms) + r")\b")

        self._cache_key = key
        self._pattern = pattern
        self._norm_to_ids = norm_to_ids
        logger.info(f"StringTermMatcher built for {len(uniq_norms)} unique terms")

    def match_terms(self, texts: List[str], terms: Iterable,
                    top_k: int = None, **kwargs) -> List[List[int]]:
        """
        对每条文本返回命中的 term_id 列表。

        Args:
            texts: 待匹配文本列表
            terms: 术语集合，元素需可取到 term_id 与 en
                   （支持 ORM 对象或 (term_id, en) 元组）
            top_k: 每条文本最多返回多少个 term_id（None 表示不限）
            **kwargs: 兼容旧参数（similarity_threshold / max_ngram 等），忽略

        Returns:
            List[List[int]]：与 texts 等长，每项为命中的 term_id 列表
        """
        # 统一成 (term_id, en)
        norm_terms = []
        for t in terms:
            if isinstance(t, (tuple, list)):
                norm_terms.append((t[0], t[1]))
            else:
                norm_terms.append((t.term_id, t.en))

        self._build(norm_terms)

        results = []
        if self._pattern is None:
            return [[] for _ in texts]

        for text in texts:
            n = normalize(text)
            if not n:
                results.append([])
                continue

            seen = set()
            matched_ids = []
            # finditer 返回不重叠的、最长优先的匹配
            for m in self._pattern.finditer(n):
                for term_id in self._norm_to_ids.get(m.group(), []):
                    if term_id not in seen:
                        seen.add(term_id)
                        matched_ids.append(term_id)
                        if top_k and len(matched_ids) >= top_k:
                            break
                if top_k and len(matched_ids) >= top_k:
                    break
            results.append(matched_ids)

        return results
