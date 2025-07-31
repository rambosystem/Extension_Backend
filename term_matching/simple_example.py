#!/usr/bin/env python3
"""
FAISS术语匹配算法简单使用示例

展示如何使用TermMatcher进行基本的术语匹配
"""

from term_matcher import TermMatcher
import sys
import os

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def main():
    """简单使用示例"""
    print("🚀 FAISS术语匹配算法简单示例")
    print("=" * 40)

    # 1. 初始化匹配器
    print("1. 初始化TermMatcher...")
    matcher = TermMatcher()
    print("✅ 初始化完成")

    # 2. 准备术语数据
    print("\n2. 准备术语数据...")
    terms_data = [
        {"term_id": 1, "en": "machine learning"},
        {"term_id": 2, "en": "artificial intelligence"},
        {"term_id": 3, "en": "deep learning"},
        {"term_id": 4, "en": "neural network"},
        {"term_id": 5, "en": "data science"},
        {"term_id": 6, "en": "natural language processing"},
        {"term_id": 7, "en": "computer vision"},
        {"term_id": 8, "en": "reinforcement learning"}
    ]
    print(f"✅ 准备了 {len(terms_data)} 个术语")

    # 3. 构建索引
    print("\n3. 构建FAISS索引...")
    matcher.build_index_from_terms(terms_data)
    print("✅ 索引构建完成")

    # 4. 准备输入文本
    print("\n4. 准备输入文本...")
    input_texts = [
        "We use machine learning algorithms for data analysis.",
        "Artificial intelligence is transforming industries.",
        "Deep neural networks require large datasets.",
        "Natural language processing helps computers understand text."
    ]
    print(f"✅ 准备了 {len(input_texts)} 个输入文本")

    # 5. 进行术语匹配
    print("\n5. 进行术语匹配...")
    results = matcher.match_terms(
        input_texts,
        similarity_threshold=0.7,
        top_k=5,
        max_ngram=3
    )
    print("✅ 匹配完成")

    # 6. 显示结果
    print("\n6. 匹配结果:")
    print("-" * 40)

    for i, (text, term_ids) in enumerate(zip(input_texts, results)):
        print(f"\n📝 文本 {i+1}: {text}")
        if term_ids:
            print(f"🎯 匹配到的术语ID: {term_ids}")

            # 显示匹配到的术语内容
            matched_terms = []
            for term_id in term_ids:
                for term in terms_data:
                    if term["term_id"] == term_id:
                        matched_terms.append(term["en"])
                        break

            print(f"📖 匹配到的术语: {matched_terms}")
        else:
            print("❌ 未匹配到任何术语")

    # 7. 获取统计信息
    print("\n7. 系统统计信息:")
    print("-" * 40)
    stats = matcher.get_stats()
    print(f"📊 FAISS索引统计: {stats['faiss_stats']}")
    print(f"🛑 停用词数量: {stats['stop_words_count']}")
    print(f"✅ 索引已加载: {stats['index_loaded']}")

    print("\n🎉 示例运行完成！")


if __name__ == "__main__":
    main()
