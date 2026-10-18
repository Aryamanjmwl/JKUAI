import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import UserContext, can_access
from ..chunking import chunk_pages
from ..models import Chunk, Document
from .ml import embed_texts_async
from .opensearch import index_chunks_async, remove_obsolete_chunks_async
from .pdf import parse_pdf  # re-export for existing callers


class DocumentConflictError(Exception):
    """A checksum collision must not disclose or change an existing document's ACL."""


async def _index_document(document: Document, rows: list[Chunk]) -> None:
    await index_chunks_async(
        [
            {
                "chunk_id": str(row.id),
                "document_id": str(document.id),
                "title": document.title,
                "content": row.content,
                "visibility": document.visibility,
                "allowed_groups": document.allowed_groups,
            }
            for row in rows
        ]
    )


async def ingest_pdf(
    session: AsyncSession,
    *,
    content: bytes,
    file_name: str,
    title: str,
    source_url: str | None,
    visibility: str,
    allowed_groups: list[str],
    user: UserContext,
) -> tuple[Document, int, bool]:
    checksum = hashlib.sha256(content).hexdigest()
    existing = await session.scalar(select(Document).where(Document.checksum == checksum))
    if existing:
        if (
            not can_access(existing.visibility, existing.allowed_groups, user)
            or existing.visibility != visibility
            or set(existing.allowed_groups) != set(allowed_groups)
        ):
            raise DocumentConflictError("This upload conflicts with an existing document")
        rows = list(
            (
                await session.scalars(
                    select(Chunk)
                    .where(Chunk.document_id == existing.id)
                    .order_by(Chunk.chunk_index)
                )
            ).all()
        )
        chunks = chunk_pages(parse_pdf(content))
        if not chunks:
            raise ValueError("No extractable text found in PDF")
        previous = [(row.page_number, row.content) for row in rows]
        current = [(chunk.page_number, chunk.content) for chunk in chunks]
        if previous != current:
            # Re-uploading the same bytes upgrades extraction without changing metadata or ACLs.
            vectors = await embed_texts_async([chunk.content for chunk in chunks])
            refreshed = []
            for i, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
                row = rows[i] if i < len(rows) else Chunk(document_id=existing.id)
                row.chunk_index = chunk.chunk_index
                row.page_number = chunk.page_number
                row.content = chunk.content
                row.embedding = vector
                if i >= len(rows):
                    session.add(row)
                refreshed.append(row)
            for row in rows[len(chunks) :]:
                await session.delete(row)
            rows = refreshed
            await session.flush()
            await session.commit()
        # Retry writes after partial failures too. SQL remains authoritative during repair.
        await _index_document(existing, rows)
        await remove_obsolete_chunks_async(str(existing.id), [str(row.id) for row in rows])
        return existing, len(rows), True

    chunks = chunk_pages(parse_pdf(content))
    if not chunks:
        raise ValueError("No extractable text found in PDF")
    vectors = await embed_texts_async([chunk.content for chunk in chunks])
    document = Document(
        title=title,
        file_name=file_name,
        source_url=source_url,
        checksum=checksum,
        visibility=visibility,
        allowed_groups=allowed_groups,
    )
    session.add(document)
    await session.flush()
    rows: list[Chunk] = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        row = Chunk(
            document_id=document.id,
            chunk_index=chunk.chunk_index,
            page_number=chunk.page_number,
            content=chunk.content,
            embedding=vector,
        )
        session.add(row)
        rows.append(row)
    await session.flush()
    await _index_document(document, rows)
    await session.commit()
    return document, len(rows), False
