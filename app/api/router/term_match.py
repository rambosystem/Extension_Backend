from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.models.models import Term, Embedding
from app.models.schemas import TermResponse
from datetime import datetime

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
                    term_id=term.term_id,
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


@router.get("/search")
async def search_similar_terms(
    query: str,
    top_k: int = Query(5, ge=1, le=50, description="返回结果数量"),
    threshold: float = Query(0.7, ge=0.0, le=1.0, description="相似度阈值")
):
    """
    搜索相似术语（简化版匹配接口）

    Args:
        query: 搜索查询文本
        top_k: 返回结果数量
        threshold: 相似度阈值

    Returns:
        相似术语列表
    """
    try:
        matcher = get_term_matcher()

        # 执行匹配
        matched_term_ids = matcher.match_terms(
            [query],
            similarity_threshold=threshold,
            top_k=top_k,
            max_ngram=3
        )

        if not matched_term_ids or not matched_term_ids[0]:
            return {
                "query": query,
                "results": [],
                "total_results": 0
            }

        # 查询数据库获取术语详情
        db = next(get_db())
        try:
            terms = db.query(Term).filter(
                Term.term_id.in_(matched_term_ids[0])
            ).all()
        finally:
            db.close()

        # 构建结果
        results = []
        for term in terms:
            results.append({
                "term_id": term.term_id,
                "en": term.en,
                "cn": term.cn,
                "jp": term.jp
            })

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


@router.post("/build/user/{user_id}")
async def build_index_for_user(user_id: int, background_tasks: BackgroundTasks):
    """为用户构建索引（后台任务）"""
    try:
        # 检查当前索引构建状态
        db = next(get_db())
        try:
            embedding_record = db.query(Embedding).filter(
                Embedding.user_id == user_id).first()

            if embedding_record and embedding_record.embedding_status in ["pending", "building"]:
                raise HTTPException(
                    status_code=409,
                    detail=f"Index building is already in progress. Current status: {embedding_record.embedding_status}"
                )
        finally:
            db.close()

        # 在后台执行索引构建
        background_tasks.add_task(build_index_for_user_task, user_id)

        return {
            "message": "Index build task started",
            "user_id": user_id,
            "status": "building"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start index build: {str(e)}")


@router.post("/build/all")
async def build_index_for_all_users(background_tasks: BackgroundTasks):
    """为所有用户构建索引（后台任务）"""
    try:
        # 检查当前索引构建状态
        db = next(get_db())
        try:
            # 检查是否有任何用户正在构建
            building_records = db.query(Embedding).filter(
                Embedding.embedding_status.in_(["pending", "building"])
            ).all()

            if building_records:
                user_ids = [record.user_id for record in building_records]
                raise HTTPException(
                    status_code=409,
                    detail=f"Index building is already in progress for users: {user_ids}. Please wait for completion."
                )
        finally:
            db.close()

        # 在后台执行索引构建
        background_tasks.add_task(build_index_for_all_users_task)

        return {
            "message": "Index build task started for all users",
            "status": "building"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start index build: {str(e)}")


@router.get("/status/{user_id}")
async def get_index_status(user_id: int):
    """获取指定用户的索引构建状态"""
    try:
        db = next(get_db())
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

            return {
                "user_id": embedding_record.user_id,
                "index_status": embedding_record.embedding_status,
                "last_build_time": embedding_record.last_embedding_time
            }
        finally:
            db.close()

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get status: {str(e)}")


@router.put("/status/{user_id}")
async def update_index_status(user_id: int, status: str):
    """更新指定用户的索引构建状态"""
    try:
        db = next(get_db())
        try:
            embedding_record = db.query(Embedding).filter(
                Embedding.user_id == user_id).first()

            if not embedding_record:
                embedding_record = Embedding(user_id=user_id)
                db.add(embedding_record)

            embedding_record.embedding_status = status

            if status == "completed":
                embedding_record.last_embedding_time = datetime.now()

            db.commit()
            db.refresh(embedding_record)

            return {
                "user_id": embedding_record.user_id,
                "index_status": embedding_record.embedding_status,
                "last_build_time": embedding_record.last_embedding_time
            }
        finally:
            db.close()

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update status: {str(e)}")


@router.post("/update-index")
async def update_index_incremental():
    """增量更新FAISS索引（添加新术语）"""
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
        db = next(get_db())
        try:
            all_terms = db.query(Term).all()
        finally:
            db.close()

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

        # 更新所有用户的索引状态为已完成，并更新last_embedding_time
        # 获取所有用户ID
        db = next(get_db())
        try:
            user_ids = db.query(Term.user_id).distinct().all()
            user_ids = [user_id[0] for user_id in user_ids]
        finally:
            db.close()

        # 为每个用户更新状态
        for user_id in user_ids:
            await update_index_status(user_id, "completed")

        return {
            "message": f"Successfully added {len(new_terms)} new terms to index",
            "status": "updated",
            "new_terms_count": len(new_terms),
            "total_terms": len(all_terms),
            "indexed_terms": len(existing_ids) + len(new_terms),
            "new_terms": [term["en"] for term in new_terms],
            "updated_users": user_ids
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update index: {str(e)}"
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


@router.delete("/index")
async def delete_index():
    """删除整个FAISS索引"""
    try:
        matcher = get_term_matcher()

        # 检查索引是否已加载
        if not matcher.faiss_manager.is_index_loaded():
            return {
                "message": "No index to delete",
                "status": "no_index"
            }

        # 获取删除前的统计信息
        stats_before = matcher.get_index_stats()
        total_terms = stats_before.get('total_vectors', 0)

        # 删除索引文件
        import os
        base_dir = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        index_path = os.path.join(base_dir, "faiss_indexes", "faiss.index")
        mapping_path = os.path.join(
            base_dir, "faiss_indexes", "term_mapping.pkl")

        deleted_files = []
        if os.path.exists(index_path):
            os.remove(index_path)
            deleted_files.append("faiss.index")

        if os.path.exists(mapping_path):
            os.remove(mapping_path)
            deleted_files.append("term_mapping.pkl")

        # 重新初始化TermMatcher（这会创建一个空的索引）
        global term_matcher
        term_matcher = None
        matcher = get_term_matcher()

        return {
            "message": f"Successfully deleted index with {total_terms} terms",
            "status": "deleted",
            "deleted_files": deleted_files,
            "terms_deleted": total_terms
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete index: {str(e)}"
        )


@router.delete("/terms")
async def delete_terms_from_index(term_ids: List[int]):
    """从索引中删除指定的术语"""
    try:
        matcher = get_term_matcher()

        # 检查索引是否已加载
        if not matcher.faiss_manager.is_index_loaded():
            raise HTTPException(
                status_code=400,
                detail="No index available. Please build index first."
            )

        if not term_ids:
            return {
                "message": "No terms to delete",
                "status": "no_terms"
            }

        # 检查哪些term_id存在于索引中
        existing_ids = set(matcher.faiss_manager.term_id_to_index.keys())
        valid_ids = [tid for tid in term_ids if tid in existing_ids]
        invalid_ids = [tid for tid in term_ids if tid not in existing_ids]

        if not valid_ids:
            return {
                "message": "None of the specified term IDs exist in the index",
                "status": "no_valid_terms",
                "invalid_ids": invalid_ids
            }

        # 删除术语
        matcher.remove_terms_from_index(valid_ids)

        return {
            "message": f"Successfully deleted {len(valid_ids)} terms from index",
            "status": "deleted",
            "deleted_count": len(valid_ids),
            "deleted_ids": valid_ids,
            "invalid_ids": invalid_ids
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete terms: {str(e)}"
        )


@router.delete("/user/{user_id}")
async def delete_user_terms_from_index(user_id: int):
    """删除指定用户的所有术语"""
    try:
        matcher = get_term_matcher()

        # 检查索引是否已加载
        if not matcher.faiss_manager.is_index_loaded():
            raise HTTPException(
                status_code=400,
                detail="No index available. Please build index first."
            )

        # 获取用户的所有术语ID
        db = next(get_db())
        try:
            user_terms = db.query(Term).filter(Term.user_id == user_id).all()
            user_term_ids = [term.term_id for term in user_terms]
        finally:
            db.close()

        if not user_term_ids:
            return {
                "message": f"No terms found for user {user_id}",
                "status": "no_terms"
            }

        # 检查哪些term_id存在于索引中
        existing_ids = set(matcher.faiss_manager.term_id_to_index.keys())
        valid_ids = [tid for tid in user_term_ids if tid in existing_ids]

        if not valid_ids:
            return {
                "message": f"No terms from user {user_id} exist in the index",
                "status": "no_valid_terms"
            }

        # 删除术语
        matcher.remove_terms_from_index(valid_ids)

        return {
            "message": f"Successfully deleted {len(valid_ids)} terms for user {user_id}",
            "status": "deleted",
            "user_id": user_id,
            "deleted_count": len(valid_ids),
            "deleted_ids": valid_ids
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete user terms: {str(e)}"
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


# 后台任务函数
async def build_index_for_user_task(user_id: int):
    """为用户构建索引的后台任务"""
    try:
        # 更新状态为构建中
        await update_index_status(user_id, "building")

        # 获取用户的所有术语
        db = next(get_db())
        try:
            terms = db.query(Term).filter(Term.user_id == user_id).all()
        finally:
            db.close()

        if not terms:
            await update_index_status(user_id, "completed")
            return {"message": "No terms to process", "processed_count": 0}

        # 准备术语数据
        terms_data = [
            {
                "term_id": term.term_id,
                "en": term.en
            }
            for term in terms
        ]

        # 使用TermMatcher重建索引
        matcher = get_term_matcher()
        matcher.build_index_from_terms(terms_data)

        # 更新状态为成功
        await update_index_status(user_id, "completed")

        return {
            "message": "Index built successfully",
            "processed_count": len(terms),
            "user_id": user_id
        }

    except Exception as e:
        await update_index_status(user_id, "failed")
        raise e


async def build_index_for_all_users_task():
    """为所有用户构建索引的后台任务"""
    try:
        # 更新状态为构建中
        await update_index_status(None, "building")

        # 获取所有术语
        db = next(get_db())
        try:
            terms = db.query(Term).all()
        finally:
            db.close()

        if not terms:
            await update_index_status(None, "completed")
            return {"message": "No terms to process", "processed_count": 0}

        # 准备术语数据
        terms_data = [
            {
                "term_id": term.term_id,
                "en": term.en
            }
            for term in terms
        ]

        # 使用TermMatcher重建索引
        matcher = get_term_matcher()
        matcher.build_index_from_terms(terms_data)

        # 更新状态为成功
        await update_index_status(None, "completed")

        return {
            "message": "Index built successfully",
            "processed_count": len(terms)
        }

    except Exception as e:
        await update_index_status(None, "failed")
        raise e
