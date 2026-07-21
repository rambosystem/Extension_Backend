from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.models.models import Term
from app.models.schemas import TermResponse

# 轻量字符串匹配器（无模型、无 FAISS）
from term_matching.string_matcher import StringTermMatcher

router = APIRouter(prefix="/term-match", tags=["term-match"])

# 全局匹配器实例（单例）
term_matcher = None


def get_term_matcher():
    """获取术语匹配器实例（单例模式）"""
    global term_matcher
    if term_matcher is None:
        try:
            term_matcher = StringTermMatcher()
            print("✅ StringTermMatcher initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize StringTermMatcher: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Term matching service unavailable: {str(e)}"
            )
    return term_matcher


@router.post("/match", response_model=List[TermResponse])
async def match_terms(
    texts: List[str],
    top_k: int = Query(10, ge=1, le=50, description="每个文本返回的最大匹配数"),
    user_id: Optional[int] = Query(None, description="限制搜索特定用户的术语"),
    db: Session = Depends(get_db)
):
    """
    术语匹配接口

    使用轻量字符串匹配（归一化整词、最长优先、不重叠），实时从数据库
    读取候选术语进行匹配。

    Args:
        texts: 待匹配的文本列表
        top_k: 每个文本返回的最大匹配数
        user_id: 限制搜索特定用户的术语（可选）

    Returns:
        匹配结果列表，所有匹配的术语合并为一个去重的列表
    """
    try:
        matcher = get_term_matcher()

        # 从数据库加载候选术语（指定用户则只取该用户的）
        query_builder = db.query(Term)
        if user_id is not None:
            query_builder = query_builder.filter(Term.user_id == user_id)
        candidate_terms = query_builder.all()

        if not candidate_terms:
            return []

        # 字符串匹配（毫秒级，无需线程池）
        matched_term_ids = matcher.match_terms(
            texts, candidate_terms, top_k=top_k)

        # 收集去重
        unique_term_ids = set()
        for term_id_list in matched_term_ids:
            unique_term_ids.update(term_id_list)

        if not unique_term_ids:
            return []

        term_map = {term.term_id: term for term in candidate_terms}
        return [
            TermResponse(
                term_id=term.term_id, en=term.en, cn=term.cn, jp=term.jp)
            for tid in unique_term_ids
            if (term := term_map.get(tid)) is not None
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Term matching failed: {str(e)}"
        )


@router.get("/search")
async def search_similar_terms(
    query: str,
    top_k: int = Query(5, ge=1, le=50, description="返回结果数量"),
    db: Session = Depends(get_db)
):
    """
    搜索匹配的术语（简化版匹配接口）

    Args:
        query: 搜索查询文本
        top_k: 返回结果数量

    Returns:
        匹配术语列表
    """
    try:
        matcher = get_term_matcher()

        candidate_terms = db.query(Term).all()

        matched_term_ids = matcher.match_terms(
            [query], candidate_terms, top_k=top_k)

        if not matched_term_ids or not matched_term_ids[0]:
            return {"query": query, "results": [], "total_results": 0}

        term_map = {term.term_id: term for term in candidate_terms}
        results = [
            {"term_id": t.term_id, "en": t.en, "cn": t.cn, "jp": t.jp}
            for tid in matched_term_ids[0]
            if (t := term_map.get(tid)) is not None
        ]

        return {
            "query": query,
            "results": results,
            "total_results": len(results)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/test")
async def test_term_match(
    text: str = "machine learning algorithms",
    top_k: int = 5,
    db: Session = Depends(get_db)
):
    """
    测试术语匹配功能

    Args:
        text: 测试文本
        top_k: 返回的最大匹配数

    Returns:
        测试结果
    """
    try:
        matcher = get_term_matcher()

        candidate_terms = db.query(Term).all()

        results = matcher.match_terms([text], candidate_terms, top_k=top_k)

        return {
            "test_text": text,
            "matched_term_ids": results[0] if results else [],
            "total_matches": len(results[0]) if results else 0,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Test failed: {str(e)}"
        )
