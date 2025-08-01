#!/usr/bin/env python3
"""
增量更新FAISS索引脚本
只添加数据库中新增的术语到现有索引，而不重建整个索引
"""

from term_matching.term_matcher import TermMatcher
from app.models.models import Term
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import sys
import os
import pickle
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def get_existing_term_ids(index_path: str, mapping_path: str) -> set:
    """
    从现有索引中获取已存在的term_id集合

    Args:
        index_path: FAISS索引文件路径
        mapping_path: 映射文件路径

    Returns:
        已存在的term_id集合
    """
    try:
        if not os.path.exists(mapping_path):
            print(f"⚠️  映射文件不存在: {mapping_path}")
            return set()

        with open(mapping_path, 'rb') as f:
            mapping_data = pickle.load(f)

        if isinstance(mapping_data, dict) and 'term_id_to_index' in mapping_data:
            existing_ids = set(mapping_data['term_id_to_index'].keys())
            print(f"✅ 从现有索引中找到 {len(existing_ids)} 个术语")
            return existing_ids
        else:
            print(f"⚠️  映射文件格式不正确: {mapping_path}")
            return set()

    except Exception as e:
        print(f"❌ 读取现有索引失败: {e}")
        return set()


def get_new_terms_from_db(db, existing_term_ids: set) -> list:
    """
    从数据库获取新增的术语

    Args:
        db: 数据库会话
        existing_term_ids: 已存在的term_id集合

    Returns:
        新增术语列表
    """
    try:
        # 获取所有术语
        all_terms = db.query(Term).all()
        print(f"📊 数据库中共有 {len(all_terms)} 个术语")

        # 找出新增的术语
        new_terms = []
        for term in all_terms:
            if term.term_id not in existing_term_ids:
                new_terms.append({
                    "term_id": term.term_id,
                    "en": term.en
                })

        print(f"🆕 发现 {len(new_terms)} 个新术语需要添加到索引")
        return new_terms

    except Exception as e:
        print(f"❌ 获取新术语失败: {e}")
        return []


def update_faiss_index_incremental():
    """增量更新FAISS索引"""

    # 数据库连接
    DATABASE_URL = "mysql+pymysql://root:123456@localhost/Extension"
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # 索引文件路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(base_dir, "faiss_indexes", "faiss.index")
    mapping_path = os.path.join(base_dir, "faiss_indexes", "term_mapping.pkl")

    try:
        print("🔍 检查现有索引...")

        # 获取现有索引中的term_id
        existing_term_ids = get_existing_term_ids(index_path, mapping_path)

        # 获取数据库中的新术语
        new_terms = get_new_terms_from_db(db, existing_term_ids)

        if not new_terms:
            print("✅ 没有新术语需要添加，索引已是最新")
            return

        # 初始化TermMatcher
        print(f"\n🔧 初始化TermMatcher...")
        matcher = TermMatcher()

        # 检查索引是否已加载
        if not matcher.faiss_manager.is_index_loaded():
            print("⚠️  现有索引未加载，将重建整个索引...")
            # 获取所有术语重建索引
            all_terms = db.query(Term).all()
            all_terms_data = [{"term_id": term.term_id,
                               "en": term.en} for term in all_terms]
            matcher.build_index_from_terms(all_terms_data)
            print(f"✅ 索引重建完成，包含 {len(all_terms_data)} 个术语")
        else:
            print(f"📈 开始增量更新索引...")

            # 提取新术语的文本和ID
            new_term_texts = [term["en"] for term in new_terms]
            new_term_ids = [term["term_id"] for term in new_terms]

            # 编码新术语
            print(f"🔤 编码 {len(new_terms)} 个新术语...")
            new_embeddings = matcher.embedding_service.encode_dense(
                new_term_texts)

            # 添加到现有索引
            print(f"➕ 将新术语添加到索引...")
            matcher.faiss_manager.add_terms(new_embeddings, new_term_ids)

            # 保存更新后的索引
            print(f"💾 保存更新后的索引...")
            matcher.faiss_manager.save_index(index_path, mapping_path)

            print(f"✅ 增量更新完成！")

        # 显示最终统计
        print(f"\n📊 最终索引统计:")
        print(f"  - 总向量数: {matcher.faiss_manager.index.ntotal}")
        print(f"  - 向量维度: {matcher.faiss_manager.embedding_dim}")
        print(f"  - 索引类型: {type(matcher.faiss_manager.index).__name__}")

        # 测试新添加的术语
        if new_terms:
            print(f"\n🧪 测试新添加的术语...")
            test_term = new_terms[0]["en"]
            test_results = matcher.match_terms(
                [test_term], similarity_threshold=0.3, top_k=3)
            print(f"测试结果 ({test_term}): {test_results}")

    except Exception as e:
        print(f"❌ 增量更新索引失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    update_faiss_index_incremental()
