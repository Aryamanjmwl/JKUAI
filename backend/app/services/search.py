from time import perf_counter
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import UserContext
from ..config import get_settings
from ..models import Chunk, Document
from ..ranking import reciprocal_rank_fusion
from .ml import embed_texts_async, rerank_async
from .opensearch import search_async


def _permission_clause(user: UserContext):
    if not user.groups:
        return Document.visibility == "public"
    return or_(Document.visibility == "public", Document.allowed_groups.overlap(list(user.groups)))


async def hybrid_search(session: AsyncSession, query: str, user: UserContext) -> list[dict]:
    settings = get_settings()
    vector = (await embed_texts_async([query]))[0]
    stmt = (
        select(Chunk, Document, Chunk.embedding.cosine_distance(vector).label("distance"))
        .join(Document)
        .where(_permission_clause(user))
        .order_by("distance")
        .limit(settings.retrieve_k)
    )
    vector_rows = (await session.execute(stmt)).all()
    vector_hits = [
        {
            "chunk_id": str(chunk.id),
            "document_id": str(document.id),
            "title": document.title,
            "file_name": document.file_name,
            "source_url": document.source_url,
            "page_number": chunk.page_number,
            "content": chunk.content,
            "retrieval_score": 1.0 - float(distance),
        }
        for chunk, document, distance in vector_rows
    ]

    permission_filter: list[dict] = [{"term": {"visibility": "public"}}]
    if user.groups:
        permission_filter.append({"terms": {"allowed_groups": list(user.groups)}})
    response = await search_async(
        {
            "size": settings.retrieve_k,
            "query": {
                "bool": {
                    "must": [{"multi_match": {"query": query, "fields": ["title^2", "content"]}}],
                    "filter": [{"bool": {"should": permission_filter, "minimum_should_match": 1}}],
                }
            },
        }
    )
    lexical_ids = [UUID(hit["_source"]["chunk_id"]) for hit in response["hits"]["hits"]]
    lexical_hits: list[dict] = []
    if lexical_ids:
        lexical_stmt = select(Chunk, Document).join(Document).where(Chunk.id.in_(lexical_ids))
        rows = (await session.execute(lexical_stmt)).all()
        by_id = {
            str(chunk.id): {
                "chunk_id": str(chunk.id),
                "document_id": str(document.id),
                "title": document.title,
                "file_name": document.file_name,
                "source_url": document.source_url,
                "page_number": chunk.page_number,
                "content": chunk.content,
            }
            for chunk, document in rows
        }
        lexical_hits = [by_id[str(item)] for item in lexical_ids if str(item) in by_id]
    fused = reciprocal_rank_fusion(vector_hits, lexical_hits)[: settings.retrieve_k]
    return await rerank_async(query, fused, settings.rerank_k)


async def timed_hybrid_search(session: AsyncSession, query: str, user: UserContext):
    start = perf_counter()
    hits = await hybrid_search(session, query, user)
    return hits, (perf_counter() - start) * 1000
