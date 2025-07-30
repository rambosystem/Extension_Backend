from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import User, Term
from app.models.schemas import UserTermsResponse, TermCreate, DeleteTermResponse, DeleteTermsResponse, DeleteTermsRequest, TermsStatusResponse
from typing import List

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
        user_id=user.user_id,
        username=user.username,
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

    # 提交到数据库
    db.commit()

    # 刷新对象以获取数据库生成的字段（如term_id）
    for term in created_terms:
        db.refresh(term)

    return UserTermsResponse(
        user_id=user.user_id,
        username=user.username,
        terms=created_terms,
        total_terms=len(created_terms)
    )


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

    # 计算embedding状态（暂时留空）
    embedding_status = True
    last_embedding_time = "2025-07-30 10:00:00"

    # TODO: 后续实现embedding状态计算逻辑
    # 可以基于vector_indexed和last_indexed_at字段来计算

    return TermsStatusResponse(
        total_terms=total_terms,
        embedding_status=embedding_status,
        last_embedding_time=last_embedding_time
    )
