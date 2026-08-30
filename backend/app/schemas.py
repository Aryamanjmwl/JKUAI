from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)


class Source(BaseModel):
    citation_id: str
    document_id: UUID
    chunk_id: UUID
    title: str
    file_name: str
    source_url: str | None
    page_number: int | None
    excerpt: str
    score: float


class SearchResponse(BaseModel):
    answer: str
    sources: list[Source]
    exact_documents_used: list[str]
    latency_ms: float


class IngestResponse(BaseModel):
    document_id: UUID
    title: str
    chunks_created: int
    duplicate: bool = False
