#!/usr/bin/env python3
"""
FAISS术语匹配算法使用示例

演示如何使用TermMatcher进行术语匹配，包括：
- 索引构建
- 术语匹配
- 重叠去重
- 性能测试
"""

from term_matching import TermMatcher
import sys
import os
import time
import logging
from typing import List, Dict

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def create_sample_terms() -> List[Dict]:
    """创建示例术语数据"""
    return [
        {"term_id": 1, "en": "machine learning"},
        {"term_id": 2, "en": "artificial intelligence"},
        {"term_id": 3, "en": "deep learning"},
        {"term_id": 4, "en": "neural network"},
        {"term_id": 5, "en": "data science"},
        {"term_id": 6, "en": "natural language processing"},
        {"term_id": 7, "en": "computer vision"},
        {"term_id": 8, "en": "reinforcement learning"},
        {"term_id": 9, "en": "supervised learning"},
        {"term_id": 10, "en": "unsupervised learning"},
        {"term_id": 11, "en": "semi-supervised learning"},
        {"term_id": 12, "en": "transfer learning"},
        {"term_id": 13, "en": "ensemble learning"},
        {"term_id": 14, "en": "feature engineering"},
        {"term_id": 15, "en": "model validation"},
        {"term_id": 16, "en": "hyperparameter tuning"},
        {"term_id": 17, "en": "cross validation"},
        {"term_id": 18, "en": "overfitting"},
        {"term_id": 19, "en": "underfitting"},
        {"term_id": 20, "en": "bias variance tradeoff"}
    ]


def create_sample_texts() -> List[str]:
    """创建示例输入文本"""
    return [
        "We use machine learning algorithms for data analysis and prediction.",
        "Artificial intelligence is transforming various industries worldwide.",
        "Deep neural networks require large datasets for training.",
        "Natural language processing helps computers understand human language.",
        "Computer vision enables machines to interpret visual information.",
        "The bias-variance tradeoff is crucial in model selection.",
        "Feature engineering plays a key role in machine learning success.",
        "Cross validation helps assess model performance reliably.",
        "Transfer learning allows models to leverage knowledge from related tasks.",
        "Ensemble learning combines multiple models for better predictions."
    ]


def test_basic_functionality():
    """测试基本功能"""
    print("🔧 测试基本功能...")

    try:
        # 1. 初始化匹配器
        matcher = TermMatcher()
        print("✅ TermMatcher初始化成功")

        # 2. 构建索引
        terms_data = create_sample_terms()
        matcher.build_index_from_terms(terms_data)
        print(f"✅ 索引构建成功，包含 {len(terms_data)} 个术语")

        # 3. 测试匹配
        input_texts = create_sample_texts()[:3]  # 只测试前3个文本
        results = matcher.match_terms(input_texts, similarity_threshold=0.7)

        print(f"✅ 匹配测试完成，处理了 {len(input_texts)} 个文本")

        # 4. 显示结果
        for i, (text, term_ids) in enumerate(zip(input_texts, results)):
            print(f"\n📝 文本 {i+1}: {text}")
            print(f"🎯 匹配到的术语ID: {term_ids}")

        return True

    except Exception as e:
        print(f"❌ 基本功能测试失败: {e}")
        return False


def test_overlap_detection():
    """测试重叠检测功能"""
    print("\n🔍 测试重叠检测功能...")

    try:
        matcher = TermMatcher()

        # 测试用例
        test_cases = [
            {
                "text": "machine learning algorithms",
                "ngram1": "machine learning",
                "ngram2": "learning algorithms",
                "expected": True
            },
            {
                "text": "deep neural networks",
                "ngram1": "deep neural",
                "ngram2": "neural networks",
                "expected": True
            },
            {
                "text": "artificial intelligence and machine learning",
                "ngram1": "artificial intelligence",
                "ngram2": "machine learning",
                "expected": False
            }
        ]

        for i, case in enumerate(test_cases):
            result = matcher.test_overlap_detection(
                case["text"], case["ngram1"], case["ngram2"]
            )
            expected = case["expected"]

            if result == expected:
                print(f"✅ 测试用例 {i+1} 通过")
            else:
                print(f"❌ 测试用例 {i+1} 失败: 期望 {expected}, 实际 {result}")

        return True

    except Exception as e:
        print(f"❌ 重叠检测测试失败: {e}")
        return False


def test_detailed_matching():
    """测试详细匹配功能"""
    print("\n📊 测试详细匹配功能...")

    try:
        matcher = TermMatcher()

        # 构建索引
        terms_data = create_sample_terms()
        matcher.build_index_from_terms(terms_data)

        # 测试详细匹配
        input_texts = ["machine learning algorithms for data analysis"]
        detailed_results = matcher.match_terms_detailed(
            input_texts, similarity_threshold=0.7
        )

        print("📝 详细匹配结果:")
        for i, matches in enumerate(detailed_results):
            print(f"\n文本 {i+1}: {input_texts[i]}")
            for match in matches:
                print(f"  - 术语ID: {match['term_id']}")
                print(f"    N-gram: '{match['ngram']}'")
                print(f"    相似度: {match['similarity']:.4f}")
                print(f"    N-gram长度: {match['ngram_length']}")

        return True

    except Exception as e:
        print(f"❌ 详细匹配测试失败: {e}")
        return False


def test_performance():
    """测试性能"""
    print("\n⚡ 测试性能...")

    try:
        matcher = TermMatcher()

        # 构建索引
        terms_data = create_sample_terms()
        start_time = time.time()
        matcher.build_index_from_terms(terms_data)
        build_time = time.time() - start_time

        print(f"✅ 索引构建时间: {build_time:.2f} 秒")

        # 测试匹配性能
        input_texts = create_sample_texts()
        start_time = time.time()
        results = matcher.match_terms(input_texts, similarity_threshold=0.7)
        match_time = time.time() - start_time

        print(f"✅ 匹配时间: {match_time:.2f} 秒")
        print(f"✅ 平均每文本匹配时间: {match_time/len(input_texts):.4f} 秒")

        # 获取统计信息
        stats = matcher.get_stats()
        print(f"✅ 索引统计: {stats['faiss_stats']}")

        return True

    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        return False


def test_index_persistence():
    """测试索引持久化"""
    print("\n💾 测试索引持久化...")

    try:
        matcher = TermMatcher()

        # 构建索引
        terms_data = create_sample_terms()
        matcher.build_index_from_terms(terms_data)

        # 保存索引
        index_path = "./temp_index.faiss"
        mapping_path = "./temp_mapping.pkl"

        matcher.save_index(index_path, mapping_path)
        print("✅ 索引保存成功")

        # 创建新的匹配器并加载索引
        new_matcher = TermMatcher()
        new_matcher.load_index(index_path, mapping_path)
        print("✅ 索引加载成功")

        # 测试加载的索引是否正常工作
        input_texts = ["machine learning"]
        results = new_matcher.match_terms(input_texts)

        if results and results[0]:
            print("✅ 加载的索引工作正常")
        else:
            print("❌ 加载的索引工作异常")

        # 清理临时文件
        if os.path.exists(index_path):
            os.remove(index_path)
        if os.path.exists(mapping_path):
            os.remove(mapping_path)

        return True

    except Exception as e:
        print(f"❌ 索引持久化测试失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 FAISS术语匹配算法测试开始")
    print("=" * 50)

    tests = [
        ("基本功能", test_basic_functionality),
        ("重叠检测", test_overlap_detection),
        ("详细匹配", test_detailed_matching),
        ("性能测试", test_performance),
        ("索引持久化", test_index_persistence)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🧪 运行测试: {test_name}")
        print("-" * 30)

        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")

    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查错误信息")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
