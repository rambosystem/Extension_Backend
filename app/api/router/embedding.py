from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.services.embedding_service import EmbeddingService
from app.models.schemas import EmbeddingResponse, EmbeddingUpdateRequest
from typing import List, Tuple

router = APIRouter(prefix="/embedding", tags=["embedding"])

# 创建embedding服务实例
embedding_service = EmbeddingService()


@router.post("/build/user/{user_id}")
async def build_embeddings_for_user(user_id: int, background_tasks: BackgroundTasks):
    """为用户构建embedding向量（后台任务）"""
    try:
        # 在后台执行embedding构建
        background_tasks.add_task(
            embedding_service.build_embeddings_for_user, user_id)

        return {
            "message": "Embedding build task started",
            "user_id": user_id,
            "status": "building"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start embedding build: {str(e)}")


@router.post("/build/all")
async def build_embeddings_for_all_users(background_tasks: BackgroundTasks):
    """为所有用户构建embedding向量（后台任务）"""
    try:
        # 在后台执行embedding构建
        background_tasks.add_task(
            embedding_service.build_embeddings_for_all_users)

        return {
            "message": "Embedding build task started for all users",
            "status": "building"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start embedding build: {str(e)}")


@router.get("/search")
async def search_similar_terms(
    query: str,
    top_k: int = 5,
    threshold: float = 0.7
):
    """搜索相似术语"""
    try:
        results = embedding_service.search_similar_terms(
            query, top_k, threshold)

        return {
            "query": query,
            "results": [
                {
                    "term_id": term_id,
                    "similarity_score": float(score)
                }
                for term_id, score in results
            ],
            "total_results": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/stats")
async def get_embedding_stats():
    """获取embedding统计信息"""
    try:
        stats = embedding_service.get_embedding_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/status", response_model=EmbeddingResponse)
async def get_embedding_status():
    """获取embedding状态"""
    try:
        from app.db.database import SessionLocal
        from app.models.models import Embedding

        db = SessionLocal()
        try:
            embedding_record = db.query(Embedding).first()

            if not embedding_record:
                # 如果没有记录，创建一个默认记录
                embedding_record = Embedding(embedding_status="pending")
                db.add(embedding_record)
                db.commit()
                db.refresh(embedding_record)

            return EmbeddingResponse(
                id=embedding_record.id,
                embedding_status=embedding_record.embedding_status,
                last_embedding_time=embedding_record.last_embedding_time
            )
        finally:
            db.close()

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get status: {str(e)}")


@router.put("/status", response_model=EmbeddingResponse)
async def update_embedding_status(request: EmbeddingUpdateRequest):
    """更新embedding状态"""
    try:
        embedding_service.update_embedding_status(request.embedding_status)

        # 返回更新后的状态
        from app.db.database import SessionLocal
        from app.models.models import Embedding

        db = SessionLocal()
        try:
            embedding_record = db.query(Embedding).first()
            return EmbeddingResponse(
                id=embedding_record.id,
                embedding_status=embedding_record.embedding_status,
                last_embedding_time=embedding_record.last_embedding_time
            )
        finally:
            db.close()

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update status: {str(e)}")
