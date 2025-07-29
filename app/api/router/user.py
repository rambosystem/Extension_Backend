from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import User, Term
from app.models.schemas import UserTermsResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/terms", response_model=UserTermsResponse)
async def get_user_terms(user_id: int, db: Session = Depends(get_db)):
    """根据User ID返回该用户的所有术语（en, cn, jp）"""

    # 查询用户是否存在
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 查询用户的所有术语，按更新时间倒序排列
    terms = db.query(Term).filter(Term.user_id == user_id).order_by(
        Term.updated_at.desc()).all()

    return UserTermsResponse(
        user_id=user.user_id,
        username=user.username,
        terms=terms,
        total_terms=len(terms)
    )
