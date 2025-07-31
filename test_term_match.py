#!/usr/bin/env python3
import sys
import os
import importlib

# 检查依赖是否安装
required_modules = ['numpy', 'faiss', 'sentence_transformers']
for module in required_modules:
    try:
        importlib.import_module(module)
        print(f"依赖 {module} 已安装")
    except ImportError:
        print(f"错误: 依赖 {module} 未安装")
        sys.exit(1)

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 尝试导入TermMatcher
try:
    from term_matching.term_matcher import TermMatcher
    print("成功导入 TermMatcher")
except ImportError as e:
    print(f"导入 TermMatcher 失败: {e}")
    sys.exit(1)

def test_term_matching():
    print("开始测试术语匹配...")
    try:
        # 初始化匹配器
        matcher = TermMatcher()
        print("术语匹配器初始化成功")

        # 检查索引是否加载
        if matcher.faiss_manager.is_index_loaded():
            print(f"索引已成功加载，包含 {matcher.faiss_manager.index.ntotal} 个向量")
            print(f"映射术语数量: {len(matcher.faiss_manager.term_id_to_index)}")
            print(f"映射索引到术语: {len(matcher.faiss_manager.index_to_term_id)}")
            # 打印术语ID映射
            print("术语ID映射:")
            for term_id, index in matcher.faiss_manager.term_id_to_index.items():
                print(f"  term_id: {term_id} -> index: {index}")
        else:
            print("警告：索引未加载成功")
            # 尝试手动加载索引
            try:
                matcher.faiss_manager.load_index(matcher.index_path, matcher.mapping_path)
                print("尝试手动加载索引成功")
                print(f"索引已成功加载，包含 {matcher.faiss_manager.index.ntotal} 个向量")
                print(f"映射术语数量: {len(matcher.faiss_manager.term_id_to_index)}")
                print(f"映射索引到术语: {len(matcher.faiss_manager.index_to_term_id)}")
            except Exception as e:
                print(f"手动加载索引失败: {e}")
                return

        # 测试匹配
        input_texts = ["machine learning is important", "artificial intelligence applications"]
        print(f"测试文本: {input_texts}")

        # 使用详细匹配方法
        print("使用match_terms_detailed方法获取详细匹配结果:")
        detailed_results = matcher.match_terms_detailed(input_texts, similarity_threshold=0.5)
        for i, text_matches in enumerate(detailed_results):
            print(f"文本 {i+1} 匹配结果 ({len(text_matches)} 个匹配):")
            for match in text_matches:
                print(f"  - 术语ID: {match['term_id']}, N-gram: '{match['ngram']}', 相似度: {match['similarity']:.4f}")

        # 也测试原始match_terms方法
        print("\n使用match_terms方法获取术语ID列表:")
        results = matcher.match_terms(input_texts, similarity_threshold=0.5)
        for i, term_ids in enumerate(results):
            print(f"文本 {i+1} 匹配的术语ID: {term_ids}")

        # 打印统计信息
        print("\n匹配统计:")
        for key, value in matcher.stats.items():
            print(f"  {key}: {value}")

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_term_matching()