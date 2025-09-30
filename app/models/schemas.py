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


# Lokalise相关模型
class LokaliseKeyCreate(BaseModel):
    """创建 Lokalise Key 模型"""
    id: int
    key_name: str
    tags: Optional[List[str]] = None
    project_id: str
    project_name: str


class LokaliseKeyUpdate(BaseModel):
    """更新 Lokalise Key 模型"""
    id: int
    key_name: str
    tags: Optional[List[str]] = None
    project_id: str
    project_name: str


class LokaliseKeyResponse(BaseModel):
    """Lokalise Key 响应模型"""
    id: int
    key_name: str
    tags: Optional[List[str]] = None
    project_id: str
    project_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LokaliseWebhookResponse(BaseModel):
    """Lokalise Webhook 响应模型"""
    success: bool
    message: str
    event_type: str
    key_id: Optional[int] = None
    project_id: Optional[str] = None


class LokaliseKeysResponse(BaseModel):
    """Lokalise Keys 列表响应模型"""
    project_id: str
    total_keys: int
    keys: List[LokaliseKeyResponse]


class KeyNameSearchRequest(BaseModel):
    """根据 key_name 列表搜索的请求模型"""
    project_id: str  # 项目ID
    key_names: List[str]


class KeySearchResult(BaseModel):
    """单个 key 搜索结果模型"""
    key_id: int
    key_name: str
    tags: Optional[List[str]] = None


class KeyNameSearchResponse(BaseModel):
    """根据 key_name 列表搜索的响应模型"""
    success: bool
    message: str
    total_found: int
    results: List[KeySearchResult]


class KeyAutocompleteRequest(BaseModel):
    """Key自动完成查询请求模型"""
    project_id: str
    query: str  # 搜索关键词
    limit: Optional[int] = 5  # 返回结果数量限制，默认5个


class TagAutocompleteRequest(BaseModel):
    """Tag自动完成查询请求模型"""
    project_id: str
    query: str  # 搜索关键词
    limit: Optional[int] = 5  # 返回结果数量限制，默认5个


class KeyAutocompleteResult(BaseModel):
    """Key自动完成单个结果模型"""
    key_id: int
    key_name: str
    tags: Optional[List[str]] = None


class TagAutocompleteResult(BaseModel):
    """Tag自动完成单个结果模型"""
    tag: str
    count: int  # 使用该tag的key数量


class KeyAutocompleteResponse(BaseModel):
    """Key自动完成查询响应模型"""
    success: bool
    message: str
    total_found: int
    results: List[KeyAutocompleteResult]


class TagAutocompleteResponse(BaseModel):
    """Tag自动完成查询响应模型"""
    success: bool
    message: str
    total_found: int
    results: List[TagAutocompleteResult]
