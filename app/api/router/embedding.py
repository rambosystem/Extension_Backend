from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.services.embedding_service import EmbeddingService
from app.models.schemas import EmbeddingStatusResponse, EmbeddingUpdateRequest
from typing import List, Tuple

router = APIRouter(prefix="/embedding", tags=["embedding"])

# 创建embedding服务实例
embedding_service = EmbeddingService()


@router.post("/build/user/{user_id}")
async def build_embeddings_for_user(user_id: int, background_tasks: BackgroundTasks):
    """为用户构建embedding向量（后台任务）"""
    try:
        # 检查当前embedding状态
        from app.db.database import SessionLocal
        from app.models.models import Embedding

        db = SessionLocal()
        try:
            embedding_record = db.query(Embedding).filter(
                Embedding.user_id == user_id).first()

            if embedding_record and embedding_record.embedding_status in ["pending", "building"]:
                raise HTTPException(
                    status_code=409,
                    detail=f"Embedding is already in progress. Current status: {embedding_record.embedding_status}"
                )
        finally:
            db.close()

        # 在后台执行embedding构建
        background_tasks.add_task(
            embedding_service.build_embeddings_for_user, user_id)

        return {
            "message": "Embedding build task started",
            "user_id": user_id,
            "status": "building"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start embedding build: {str(e)}")


@router.post("/build/all")
async def build_embeddings_for_all_users(background_tasks: BackgroundTasks):
    """为所有用户构建embedding向量（后台任务）"""
    try:
        # 检查当前embedding状态
        from app.db.database import SessionLocal
        from app.models.models import Embedding

        db = SessionLocal()
        try:
            # 检查是否有任何用户正在构建
            building_records = db.query(Embedding).filter(
                Embedding.embedding_status.in_(["pending", "building"])
            ).all()

            if building_records:
                user_ids = [record.user_id for record in building_records]
                raise HTTPException(
                    status_code=409,
                    detail=f"Embedding is already in progress for users: {user_ids}. Please wait for completion."
                )
        finally:
            db.close()

        # 在后台执行embedding构建
        background_tasks.add_task(
            embedding_service.build_embeddings_for_all_users)

        return {
            "message": "Embedding build task started for all users",
            "status": "building"
        }
    except HTTPException:
        raise
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


@router.get("/status/{user_id}", response_model=EmbeddingStatusResponse)
async def get_embedding_status(user_id: int):
    """获取指定用户的embedding状态"""
    try:
        from app.db.database import SessionLocal
        from app.models.models import Embedding

        db = SessionLocal()
        try:
            embedding_record = db.query(Embedding).filter(
                Embedding.user_id == user_id).first()

            if not embedding_record:
                # 如果没有记录，创建一个默认记录
                embedding_record = Embedding(
                    user_id=user_id,
                    embedding_status="pending"
                )
                db.add(embedding_record)
                db.commit()
                db.refresh(embedding_record)

            return EmbeddingStatusResponse(
                user_id=embedding_record.user_id,
                embedding_status=embedding_record.embedding_status,
                last_embedding_time=embedding_record.last_embedding_time
            )
        finally:
            db.close()

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get status: {str(e)}")


@router.put("/status/{user_id}", response_model=EmbeddingStatusResponse)
async def update_embedding_status(user_id: int, request: EmbeddingUpdateRequest):
    """更新指定用户的embedding状态"""
    try:
        embedding_service.update_embedding_status(
            request.embedding_status, user_id)

        # 返回更新后的状态
        from app.db.database import SessionLocal
        from app.models.models import Embedding

        db = SessionLocal()
        try:
            embedding_record = db.query(Embedding).filter(
                Embedding.user_id == user_id).first()
            return EmbeddingStatusResponse(
                user_id=embedding_record.user_id,
                embedding_status=embedding_record.embedding_status,
                last_embedding_time=embedding_record.last_embedding_time
            )
        finally:
            db.close()

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update status: {str(e)}")
