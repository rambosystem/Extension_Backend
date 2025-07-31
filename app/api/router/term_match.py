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


@router.post("/match", response_model=List[List[TermResponse]])
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
        匹配结果列表，每个输入文本对应一个术语列表
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

        # 从数据库获取完整的术语信息
        all_term_ids = []
        for term_id_list in matched_term_ids:
            all_term_ids.extend(term_id_list)

        if not all_term_ids:
            # 没有匹配结果，返回空列表
            return [[] for _ in texts]

        # 查询数据库获取术语详情
        query_builder = db.query(Term).filter(Term.term_id.in_(all_term_ids))

        # 如果指定了用户ID，添加用户过滤
        if user_id is not None:
            query_builder = query_builder.filter(Term.user_id == user_id)

        terms = query_builder.all()

        # 创建term_id到Term对象的映射
        term_map = {term.term_id: term for term in terms}

        # 构建返回结果
        results = []
        for term_id_list in matched_term_ids:
            text_terms = []
            for term_id in term_id_list:
                if term_id in term_map:
                    term = term_map[term_id]
                    text_terms.append(TermResponse(
                        en=term.en,
                        cn=term.cn,
                        jp=term.jp
                    ))
            results.append(text_terms)

        return results

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

        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
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
