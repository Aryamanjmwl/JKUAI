from contextlib import asynccontextmanager
from pathlib import PurePosixPath
from time import perf_counter
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import HttpUrl, TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import UserContext
from .config import get_settings
from .database import get_session
from .schemas import IngestResponse, RetrievalResponse, SearchRequest, SearchResponse, Source
from .security import get_user_context
from .services.generation import (
    InvalidOpenAICredentialsError,
    OpenAIQuotaError,
    OpenAIServiceError,
    cited_source_ids,
    generate_answer,
)
from .services.ingestion import DocumentConflictError, ingest_pdf
from .services.opensearch import ensure_index_async
from .services.search import hybrid_search


@asynccontextmanager
async def lifespan(_: FastAPI):
    await ensure_index_async()
    yield


app = FastAPI(title="JKU Knowledge Search", version="0.1.0", lifespan=lifespan)
allowed_headers = ["Content-Type", "X-OpenAI-API-Key"]
if get_settings().enable_demo_roles:
    allowed_headers.extend(["X-User-Id", "X-User-Groups"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=allowed_headers,
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/documents", response_model=IngestResponse)
async def upload_document(
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[UserContext, Depends(get_user_context)],
    source_url: Annotated[str | None, Form()] = None,
    visibility: Annotated[str, Form()] = "public",
    allowed_groups: Annotated[str, Form()] = "",
) -> IngestResponse:
    if file.content_type != "application/pdf" and not (file.filename or "").lower().endswith(
        ".pdf"
    ):
        raise HTTPException(400, "Only PDF files are supported in this version")
    if visibility not in {"public", "restricted"}:
        raise HTTPException(400, "visibility must be public or restricted")
    title = title.strip()
    if not title or len(title) > 500:
        raise HTTPException(422, "title must contain between 1 and 500 characters")
    if source_url:
        try:
            source_url = str(TypeAdapter(HttpUrl).validate_python(source_url))
        except ValidationError as exc:
            raise HTTPException(422, "source_url must be an HTTP or HTTPS URL") from exc
        if len(source_url) > 2000:
            raise HTTPException(422, "source_url must not exceed 2000 characters")
    groups = sorted({item.strip() for item in allowed_groups.split(",") if item.strip()})
    if visibility == "restricted" and not groups:
        raise HTTPException(400, "Restricted documents require at least one allowed group")
    content = await file.read(get_settings().max_upload_bytes + 1)
    if len(content) > get_settings().max_upload_bytes:
        raise HTTPException(413, "PDF exceeds the configured upload limit")
    file_name = PurePosixPath((file.filename or "document.pdf").replace("\\", "/")).name
    if len(file_name) > 500:
        raise HTTPException(422, "filename must not exceed 500 characters")
    try:
        document, count, duplicate = await ingest_pdf(
            session,
            content=content,
            file_name=file_name,
            title=title,
            source_url=source_url,
            visibility=visibility,
            allowed_groups=groups,
            user=user,
        )
    except DocumentConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return IngestResponse(
        document_id=document.id, title=document.title, chunks_created=count, duplicate=duplicate
    )


@app.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[UserContext, Depends(get_user_context)],
    openai_api_key: Annotated[str | None, Header(alias="X-OpenAI-API-Key")] = None,
) -> SearchResponse:
    start = perf_counter()
    hits = await hybrid_search(session, request.query, user)
    try:
        answer = await generate_answer(request.query, hits, openai_api_key)
    except InvalidOpenAICredentialsError as exc:
        raise HTTPException(401, "The OpenAI API key was not accepted") from exc
    except OpenAIQuotaError as exc:
        raise HTTPException(429, "The OpenAI account has no available quota") from exc
    except OpenAIServiceError as exc:
        raise HTTPException(502, "OpenAI is temporarily unavailable") from exc
    sources = _build_sources(hits)
    return SearchResponse(
        answer=answer,
        sources=sources,
        exact_documents_used=_document_names(
            [source for source in sources if source.citation_id in cited_source_ids(answer)]
        ),
        latency_ms=round((perf_counter() - start) * 1000, 2),
    )


@app.post("/search/retrieval", response_model=RetrievalResponse)
async def retrieve(
    request: SearchRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[UserContext, Depends(get_user_context)],
) -> RetrievalResponse:
    start = perf_counter()
    hits = await hybrid_search(session, request.query, user)
    sources = _build_sources(hits)
    return RetrievalResponse(
        sources=sources,
        exact_documents_used=_document_names(sources),
        latency_ms=round((perf_counter() - start) * 1000, 2),
    )


def _build_sources(hits: list[dict]) -> list[Source]:
    return [
        Source(
            citation_id=f"S{i}",
            document_id=hit["document_id"],
            chunk_id=hit["chunk_id"],
            title=hit["title"],
            file_name=hit["file_name"],
            source_url=hit["source_url"],
            page_number=hit["page_number"],
            excerpt=hit["content"][:500],
            score=hit["rerank_score"],
        )
        for i, hit in enumerate(hits, start=1)
    ]


def _document_names(sources: list[Source]) -> list[str]:
    return list(dict.fromkeys(source.file_name for source in sources))
