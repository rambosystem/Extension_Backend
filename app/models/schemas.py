from pydantic import BaseModel
from typing import List, Optional


class TermCreate(BaseModel):
    en: str
    cn: Optional[str] = None
    jp: Optional[str] = None


class TermResponse(BaseModel):
    en: str
    cn: Optional[str] = None
    jp: Optional[str] = None

    class Config:
        from_attributes = True


class UserTermsResponse(BaseModel):
    terms: List[TermResponse]
    total_terms: int


class DeleteTermResponse(BaseModel):
    message: str
    term_id: int


class DeleteTermsRequest(BaseModel):
    en_terms: List[str]


class DeleteTermsResponse(BaseModel):
    message: str
    deleted_count: int
