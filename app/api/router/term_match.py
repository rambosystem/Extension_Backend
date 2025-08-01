from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.models.models import Term
from app.models.schemas import TermResponse

# 在设置路径后导入term_matcher
from term_matching.term_matcher import TermMatcher

router = APIRouter(prefix="/term-match", tags=["term-match"])

# 全局TermMatcher实例
term_matcher = None


def get_term_matcher():
    """获取TermMatcher实例（单例模式）"""
    global term_matcher
    if term_matcher is None:
        try:
            term_matcher = TermMatcher()
            print("✅ TermMatcher initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize TermMatcher: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Term matching service unavailable: {str(e)}"
            )
    return term_matcher


@router.post("/match", response_model=List[TermResponse])
async def match_terms(
    texts: List[str],
    similarity_threshold: float = Query(
        0.7, ge=0.0, le=1.0, description="相似度阈值"),
    top_k: int = Query(10, ge=1, le=50, description="每个文本返回的最大匹配数"),
    max_ngram: int = Query(3, ge=1, le=5, description="最大N-gram长度"),
    user_id: Optional[int] = Query(None, description="限制搜索特定用户的术语"),
    db: Session = Depends(get_db)
):
    """
    术语匹配接口

    使用FAISS + BGE-Large-EN-v1.5模型进行英文术语匹配
    支持多粒度匹配（1-3个词）和重叠去重处理

    Args:
        texts: 待匹配的文本列表
        similarity_threshold: 相似度阈值（0.0-1.0）
        top_k: 每个文本返回的最大匹配数
        max_ngram: 最大N-gram长度
        user_id: 限制搜索特定用户的术语（可选）

    Returns:
        匹配结果列表，所有匹配的术语合并为一个去重的列表
    """
    try:
        # 获取TermMatcher实例
        matcher = get_term_matcher()

        # 执行术语匹配
        matched_term_ids = matcher.match_terms(
            texts,
            similarity_threshold=similarity_threshold,
            top_k=top_k,
            max_ngram=max_ngram
        )

        # 收集所有匹配的term_id并进行去重
        all_term_ids = set()
        for term_id_list in matched_term_ids:
            all_term_ids.update(term_id_list)

        if not all_term_ids:
            # 没有匹配结果，返回空列表
            return []

        # 查询数据库获取术语详情
        query_builder = db.query(Term).filter(
            Term.term_id.in_(list(all_term_ids)))

        # 如果指定了用户ID，添加用户过滤
        if user_id is not None:
            query_builder = query_builder.filter(Term.user_id == user_id)

        terms = query_builder.all()

        # 创建term_id到Term对象的映射
        term_map = {term.term_id: term for term in terms}

        # 构建返回结果（使用set集合记录term_id，然后转换为术语列表）
        unique_term_ids = set()

        # 收集所有匹配的term_id到set中（自动去重）
        for term_id_list in matched_term_ids:
            unique_term_ids.update(term_id_list)

        # 根据去重后的term_id构建术语列表
        all_unique_terms = []
        for term_id in unique_term_ids:
            if term_id in term_map:
                term = term_map[term_id]
                all_unique_terms.append(TermResponse(
                    en=term.en,
                    cn=term.cn,
                    jp=term.jp
                ))

        return all_unique_terms

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Term matching failed: {str(e)}"
        )


@router.get("/stats")
async def get_term_match_stats():
    """获取术语匹配服务统计信息"""
    try:
        matcher = get_term_matcher()
        stats = matcher.get_stats()
        index_stats = matcher.get_index_stats()

        return {
            "status": "success",
            "performance_stats": stats,
            "index_stats": index_stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.post("/update-index")
async def update_index_incremental():
    """增量更新FAISS索引（添加新术语）"""
    try:
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import create_engine

        # 数据库连接
        DATABASE_URL = "mysql+pymysql://root:123456@localhost/Extension"
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        try:
            # 获取TermMatcher实例
            matcher = get_term_matcher()

            # 检查索引是否已加载
            if not matcher.faiss_manager.is_index_loaded():
                return {
                    "message": "Index not loaded, please rebuild index first",
                    "status": "no_index"
                }

            # 获取现有索引中的term_id
            existing_ids = set(matcher.faiss_manager.term_id_to_index.keys())

            # 获取数据库中的所有术语
            all_terms = db.query(Term).all()

            # 找出新增的术语
            new_terms = []
            for term in all_terms:
                if term.term_id not in existing_ids:
                    new_terms.append({
                        "term_id": term.term_id,
                        "en": term.en
                    })

            if not new_terms:
                return {
                    "message": "No new terms to add",
                    "status": "up_to_date",
                    "total_terms": len(all_terms),
                    "indexed_terms": len(existing_ids)
                }

            # 增量更新索引
            matcher.add_terms_to_index(new_terms)

            return {
                "message": f"Successfully added {len(new_terms)} new terms to index",
                "status": "updated",
                "new_terms_count": len(new_terms),
                "total_terms": len(all_terms),
                "indexed_terms": len(existing_ids) + len(new_terms),
                "new_terms": [term["en"] for term in new_terms]
            }

        finally:
            db.close()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update index: {str(e)}"
        )


@router.post("/test")
async def test_term_match(
    text: str = "machine learning algorithms",
    similarity_threshold: float = 0.6,
    top_k: int = 5
):
    """
    测试术语匹配功能

    Args:
        text: 测试文本
        similarity_threshold: 相似度阈值
        top_k: 返回的最大匹配数

    Returns:
        测试结果
    """
    try:
        matcher = get_term_matcher()

        # 执行匹配
        results = matcher.match_terms(
            [text],
            similarity_threshold=similarity_threshold,
            top_k=top_k,
            max_ngram=3
        )

        return {
            "test_text": text,
            "matched_term_ids": results[0] if results else [],
            "total_matches": len(results[0]) if results else 0,
            "performance_stats": matcher.get_stats()['performance_stats']
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Test failed: {str(e)}"
        )
