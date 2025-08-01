from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class TermCreate(BaseModel):
    en: str
    cn: Optional[str] = None
    jp: Optional[str] = None


class TermResponse(BaseModel):
    term_id: int
    en: str
    cn: Optional[str] = None
    jp: Optional[str] = None

    class Config:
        from_attributes = True


class UserTermsResponse(BaseModel):
    terms: List[TermResponse]


class DeleteTermResponse(BaseModel):
    message: str
    term_id: int


class DeleteTermsRequest(BaseModel):
    term_ids: List[int]


class DeleteTermsResponse(BaseModel):
    message: str
    deleted_count: int


class TermsStatusResponse(BaseModel):
    total_terms: int


class EmbeddingStatusResponse(BaseModel):
    user_id: int
    embedding_status: str
    last_embedding_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmbeddingUpdateRequest(BaseModel):
    embedding_status: str
    last_embedding_time: Optional[datetime] = None
