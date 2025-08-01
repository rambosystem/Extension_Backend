#!/usr/bin/env python3
"""
重建FAISS索引脚本
从数据库获取所有术语并重新构建FAISS索引
"""

from term_matching.term_matcher import TermMatcher
from app.models.models import Term
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def rebuild_faiss_index():
    """重建FAISS索引"""

    # 数据库连接
    DATABASE_URL = "mysql+pymysql://root:123456@localhost/Extension"
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        print("🔍 从数据库获取所有术语...")

        # 获取所有术语
        terms = db.query(Term).all()
        print(f"✅ 找到 {len(terms)} 个术语")

        if not terms:
            print("❌ 数据库中没有术语数据")
            return

        # 准备术语数据
        terms_data = []
        for term in terms:
            terms_data.append({
                "term_id": term.term_id,
                "en": term.en
            })
            print(f"  - {term.term_id}: {term.en}")

        print(f"\n🔧 初始化TermMatcher...")
        matcher = TermMatcher()

        print(f"🏗️  构建FAISS索引...")
        matcher.build_index_from_terms(terms_data)

        print(f"✅ FAISS索引构建完成！")
        print(f"📊 索引统计:")
        print(f"  - 总向量数: {matcher.faiss_manager.index.ntotal}")
        print(f"  - 向量维度: {matcher.faiss_manager.embedding_dim}")
        print(f"  - 索引类型: {type(matcher.faiss_manager.index).__name__}")

        # 测试索引
        print(f"\n🧪 测试索引...")
        test_results = matcher.match_terms(
            ["Brian"], similarity_threshold=0.3, top_k=5)
        print(f"测试结果: {test_results}")

    except Exception as e:
        print(f"❌ 重建索引失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    rebuild_faiss_index()
