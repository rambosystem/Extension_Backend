from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import User, Term, Embedding
from app.models.schemas import UserTermsResponse, TermCreate, DeleteTermResponse, DeleteTermsResponse, DeleteTermsRequest, TermsStatusResponse, EmbeddingStatusResponse, EmbeddingUpdateRequest
from typing import List
from datetime import datetime

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/terms", response_model=UserTermsResponse)
async def get_user_terms(user_id: int, db: Session = Depends(get_db)):
    """根据User ID返回该用户的所有术语（en, cn, jp）"""

    # 查询用户是否存在
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 查询用户的所有术语，按term_id倒序排列，确保新增加的在最前面
    terms = db.query(Term).filter(Term.user_id == user_id).order_by(
        Term.term_id.desc()).all()

    return UserTermsResponse(
        terms=terms,
        total_terms=len(terms)
    )


@router.post("/{user_id}/terms", response_model=UserTermsResponse)
async def create_user_terms(user_id: int, terms: List[TermCreate], db: Session = Depends(get_db)):
    """批量创建用户术语"""

    # 查询用户是否存在
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 创建术语列表
    created_terms = []
    new_terms_added = False  # 标记是否有新术语被添加

    for term_data in terms:
        # 检查术语是否已存在
        existing_term = db.query(Term).filter(
            Term.user_id == user_id,
            Term.en == term_data.en
        ).first()

        if existing_term:
            # 如果术语已存在，直接更新
            existing_term.cn = term_data.cn
            existing_term.jp = term_data.jp
            created_terms.append(existing_term)
        else:
            # 创建新术语
            new_term = Term(
                user_id=user_id,
                en=term_data.en,
                cn=term_data.cn,
                jp=term_data.jp
            )
            db.add(new_term)
            created_terms.append(new_term)
            new_terms_added = True  # 标记有新术语添加

    # 提交到数据库
    db.commit()

    # 刷新对象以获取数据库生成的字段（如term_id）
    for term in created_terms:
        db.refresh(term)

    # 如果有新术语添加，自动触发索引更新
    if new_terms_added:
        try:
            from app.services.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()

            # 在后台异步更新索引
            import asyncio
            asyncio.create_task(update_index_for_user(
                user_id, embedding_service))

        except Exception as e:
            # 索引更新失败不影响术语创建，只记录日志
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to update index for user {user_id}: {e}")

    return UserTermsResponse(
        terms=created_terms,
        total_terms=len(created_terms)
    )


async def update_index_for_user(user_id: int, embedding_service):
    """异步更新用户的索引"""
    try:
        # 更新embedding状态为building
        embedding_service.update_embedding_status("building", user_id)

        # 重建用户的embedding索引
        result = embedding_service.build_embeddings_for_user(user_id)

        # 更新embedding状态为completed
        embedding_service.update_embedding_status("completed", user_id)

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Index updated successfully for user {user_id}: {result}")

    except Exception as e:
        # 更新失败，设置状态为failed
        embedding_service.update_embedding_status("failed", user_id)

        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to update index for user {user_id}: {e}")


@router.delete("/{user_id}/terms/{en}", response_model=DeleteTermResponse)
async def delete_user_term(user_id: int, en: str, db: Session = Depends(get_db)):
    """根据英文术语删除用户的单个术语"""

    # 查询用户是否存在
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 查询术语是否存在且属于该用户
    term = db.query(Term).filter(
        Term.en == en,
        Term.user_id == user_id
    ).first()

    if not term:
        raise HTTPException(status_code=404, detail="Term not found")

    # 删除术语
    db.delete(term)
    db.commit()

    return DeleteTermResponse(message="Term deleted successfully", term_id=term.term_id)


@router.delete("/{user_id}/terms", response_model=DeleteTermsResponse)
async def delete_user_terms(user_id: int, request: DeleteTermsRequest, db: Session = Depends(get_db)):
    """根据英文术语批量删除用户的术语"""

    # 查询用户是否存在
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 查询所有要删除的术语
    terms = db.query(Term).filter(
        Term.en.in_(request.en_terms),
        Term.user_id == user_id
    ).all()

    if not terms:
        raise HTTPException(status_code=404, detail="No terms found to delete")

    # 检查是否所有请求的术语都存在
    found_en_terms = [term.en for term in terms]
    missing_en_terms = set(request.en_terms) - set(found_en_terms)

    if missing_en_terms:
        raise HTTPException(
            status_code=404,
            detail=f"Terms not found: {list(missing_en_terms)}"
        )

    # 删除术语
    for term in terms:
        db.delete(term)

    db.commit()

    return DeleteTermsResponse(
        message="Terms deleted successfully",
        deleted_count=len(terms)
    )


@router.get("/{user_id}/terms/status", response_model=TermsStatusResponse)
async def get_user_terms_status(user_id: int, db: Session = Depends(get_db)):
    """获取用户术语状态信息"""

    # 查询用户是否存在
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 查询用户的所有术语
    terms = db.query(Term).filter(Term.user_id == user_id).all()
    total_terms = len(terms)

    return TermsStatusResponse(
        total_terms=total_terms
    )
