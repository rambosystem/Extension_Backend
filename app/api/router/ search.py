from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from db.database import get_db
from db.models import User, Term
from models.schemas import TermResponse
from faiss_engine.vector_store import FAISSVectorStore
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/search", tags=["search"])

# 全局向量存储实例
vector_store = None


def get_vector_store():
    """获取向量存储实例（使用持久化路径）"""
    global vector_store
    if vector_store is None:
        # 使用环境变量配置的持久化路径
        index_path = os.getenv("FAISS_INDEX_PATH", "./faiss_indexes")
        print(
            f"🔧 Initializing vector store with persistent path: {index_path}")
        vector_store = FAISSVectorStore(index_path=index_path)

        # 自动保存索引（确保持久化）
        vector_store._auto_save = True

    return vector_store


@router.get("/similar-terms", response_model=List[TermResponse])
async def search_similar_terms(
    query: str = Query(..., description="搜索查询文本"),
    user_id: Optional[int] = Query(None, description="限制搜索特定用户的术语"),
    top_k: int = Query(5, ge=1, le=20, description="返回最相似的k个结果"),
    threshold: float = Query(0.7, ge=0.0, le=1.0, description="相似度阈值"),
    db: Session = Depends(get_db)
):
    """
    基于语义相似度搜索术语

    注意：当前系统仅支持英文查询和英文术语匹配
    - 英文查询：machine learning
    """
    try:
        # 获取向量存储
        vs = get_vector_store()

        # 向量搜索
        similar_term_ids = vs.search_similar_terms(
            query, top_k=top_k, threshold=threshold)

        if not similar_term_ids:
            return []

        # 提取term_id列表
        term_ids = [term_id for term_id, _ in similar_term_ids]

        # 从数据库获取完整的术语信息
        query_builder = db.query(Term).filter(Term.term_id.in_(term_ids))

        # 如果指定了用户ID，添加用户过滤
        if user_id is not None:
            # 验证用户存在
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            query_builder = query_builder.filter(Term.user_id == user_id)

        terms = query_builder.all()

        # 按相似度排序结果
        similarity_map = {term_id: similarity for term_id,
                          similarity in similar_term_ids}
        terms.sort(key=lambda t: similarity_map.get(
            t.term_id, 0), reverse=True)

        return terms

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/index-stats")
async def get_index_stats():
    """获取向量索引统计信息"""
    try:
        vs = get_vector_store()
        stats = vs.get_stats()
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.post("/rebuild-index")
async def rebuild_index(
    user_id: Optional[int] = Query(None, description="重建特定用户的索引，不指定则重建全部"),
    db: Session = Depends(get_db)
):
    """
    重建向量索引

    注意：这是一个耗时操作，建议在低峰期执行
    """
    try:
        # 查询需要重建索引的术语
        query_builder = db.query(Term)
        if user_id is not None:
            # 验证用户存在
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            query_builder = query_builder.filter(Term.user_id == user_id)

        terms = query_builder.all()

        # 准备重建数据
        terms_data = []
        for term in terms:
            terms_data.append({
                "term_id": term.term_id,
                "en": term.en,
                "cn": term.cn,
                "jp": term.jp
            })

        # 重建索引
        vs = get_vector_store()
        success = vs.rebuild_index(terms_data)

        if success:
            # 更新数据库中的向量索引状态
            db.query(Term).filter(Term.term_id.in_([t["term_id"] for t in terms_data])).update(
                {Term.vector_indexed: True}, synchronize_session=False
            )
            db.commit()

            return {
                "status": "success",
                "message": f"Successfully rebuilt index for {len(terms_data)} terms",
                "terms_count": len(terms_data)
            }
        else:
            raise HTTPException(status_code=500, detail="Index rebuild failed")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Rebuild failed: {str(e)}")
