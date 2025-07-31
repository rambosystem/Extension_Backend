"""
重叠去重处理器

处理N-gram之间的重叠，实现最大长度优先策略：
- 检测N-gram在原文中的重叠
- 实现最大长度优先去重
- 位置重叠检测
"""

import re
from typing import List, Dict, Tuple, Set


class OverlapHandler:
    """重叠去重处理器"""

    def __init__(self):
        """初始化重叠处理器"""
        pass

    def detect_overlap(self, ngram1: str, ngram2: str, original_text: str) -> bool:
        """
        检测两个N-gram在原文中是否有重叠

        Args:
            ngram1: 第一个N-gram
            ngram2: 第二个N-gram
            original_text: 原始文本

        Returns:
            True表示有重叠，False表示无重叠
        """
        if not ngram1 or not ngram2 or not original_text:
            return False

        # 转换为小写进行匹配
        text_lower = original_text.lower()
        ngram1_lower = ngram1.lower()
        ngram2_lower = ngram2.lower()

        # 找到两个N-gram在原文中的所有位置
        positions1 = self._find_all_positions(text_lower, ngram1_lower)
        positions2 = self._find_all_positions(text_lower, ngram2_lower)

        # 检查是否有重叠
        for pos1 in positions1:
            start1, end1 = pos1
            for pos2 in positions2:
                start2, end2 = pos2

                # 检查是否有重叠
                if self._has_overlap(start1, end1, start2, end2):
                    return True

        return False

    def _find_all_positions(self, text: str, pattern: str) -> List[Tuple[int, int]]:
        """
        找到模式在文本中的所有位置

        Args:
            text: 文本
            pattern: 要查找的模式

        Returns:
            位置列表，每个位置为(start, end)元组
        """
        positions = []
        start = 0

        while True:
            pos = text.find(pattern, start)
            if pos == -1:
                break

            end = pos + len(pattern)
            positions.append((pos, end))
            start = pos + 1

        return positions

    def _has_overlap(self, start1: int, end1: int, start2: int, end2: int) -> bool:
        """
        检查两个区间是否有重叠

        Args:
            start1, end1: 第一个区间的起始和结束位置
            start2, end2: 第二个区间的起始和结束位置

        Returns:
            True表示有重叠
        """
        return not (end1 <= start2 or end2 <= start1)

    def remove_overlaps(self, matches: List[Dict]) -> List[int]:
        """
        实现最大长度优先去重

        Args:
            matches: 匹配结果列表，格式为：
                    [{"term_id": int, "ngram": str, "similarity": float, "original_text": str}, ...]

        Returns:
            去重后的term_id列表
        """
        if not matches:
            return []

        # 按N-gram长度降序排列，相同长度按相似度降序排列
        sorted_matches = sorted(
            matches,
            key=lambda x: (len(x['ngram'].split()), x['similarity']),
            reverse=True
        )

        selected_terms = []
        selected_ngrams = []

        for match in sorted_matches:
            term_id = match['term_id']
            ngram = match['ngram']
            original_text = match['original_text']

            # 检查是否与已选择的N-gram重叠
            has_overlap = False
            for selected_ngram in selected_ngrams:
                if self.detect_overlap(ngram, selected_ngram, original_text):
                    has_overlap = True
                    break

            # 如果没有重叠，加入结果集
            if not has_overlap:
                selected_terms.append(term_id)
                selected_ngrams.append(ngram)

        return selected_terms

    def remove_overlaps_with_positions(self, matches: List[Dict]) -> List[Dict]:
        """
        带位置信息的重叠去重（返回详细信息）

        Args:
            matches: 匹配结果列表

        Returns:
            去重后的匹配结果列表，包含位置信息
        """
        if not matches:
            return []

        # 为每个匹配添加位置信息
        matches_with_positions = []
        for match in matches:
            positions = self._find_all_positions(
                match['original_text'].lower(),
                match['ngram'].lower()
            )
            match_with_pos = {
                **match,
                'positions': positions
            }
            matches_with_positions.append(match_with_pos)

        # 按长度和相似度排序
        sorted_matches = sorted(
            matches_with_positions,
            key=lambda x: (len(x['ngram'].split()), x['similarity']),
            reverse=True
        )

        selected_matches = []
        selected_positions = []

        for match in sorted_matches:
            term_id = match['term_id']
            ngram = match['ngram']
            positions = match['positions']

            # 检查是否与已选择的位置重叠
            has_overlap = False
            for pos in positions:
                for selected_pos in selected_positions:
                    if self._has_overlap(pos[0], pos[1], selected_pos[0], selected_pos[1]):
                        has_overlap = True
                        break
                if has_overlap:
                    break

            # 如果没有重叠，加入结果集
            if not has_overlap:
                selected_matches.append(match)
                selected_positions.extend(positions)

        return selected_matches

    def get_overlap_info(self, matches: List[Dict]) -> Dict:
        """
        获取重叠信息统计

        Args:
            matches: 匹配结果列表

        Returns:
            重叠信息统计字典
        """
        if not matches:
            return {
                'total_matches': 0,
                'overlap_groups': 0,
                'overlap_pairs': 0
            }

        overlap_pairs = 0
        overlap_groups = set()

        for i, match1 in enumerate(matches):
            for j, match2 in enumerate(matches[i+1:], i+1):
                if self.detect_overlap(
                    match1['ngram'],
                    match2['ngram'],
                    match1['original_text']
                ):
                    overlap_pairs += 1
                    overlap_groups.add(i)
                    overlap_groups.add(j)

        return {
            'total_matches': len(matches),
            'overlap_groups': len(overlap_groups),
            'overlap_pairs': overlap_pairs
        }
