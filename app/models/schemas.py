from pydantic import BaseModel
from typing import List, Optional


class TermResponse(BaseModel):
    en: str
    cn: Optional[str] = None
    jp: Optional[str] = None

    class Config:
        from_attributes = True


class UserTermsResponse(BaseModel):
    terms: List[TermResponse]
    total_terms: int
