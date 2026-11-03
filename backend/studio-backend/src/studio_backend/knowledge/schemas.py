from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from studio_backend.database import UtcDateTime


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


class KnowledgeBaseRead(KnowledgeBaseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: UtcDateTime
    document_count: int = 0
    chunk_count: int = 0


class DocumentFromUrl(BaseModel):
    url: HttpUrl


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_base_id: str
    name: str
    source: str
    content_type: str
    size_bytes: int
    source_url: str | None
    status: str
    error: str | None
    chunk_count: int
    created_at: UtcDateTime
    updated_at: UtcDateTime


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class SearchHit(BaseModel):
    document_id: str
    document_name: str
    text: str
    score: float
    similarity: float
    keyword_overlap: float
