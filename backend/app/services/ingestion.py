import hashlib
import io

from pypdf import PdfReader
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..chunking import TextPage, chunk_pages
from ..models import Chunk, Document
from .ml import embed_texts_async
from .opensearch import index_chunks_async


def parse_pdf(content: bytes) -> list[TextPage]:
    reader = PdfReader(io.BytesIO(content))
    return [TextPage(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]


async def ingest_pdf(
    session: AsyncSession,
    *,
    content: bytes,
    file_name: str,
    title: str,
    source_url: str | None,
    visibility: str,
    allowed_groups: list[str],
) -> tuple[Document, int, bool]:
    checksum = hashlib.sha256(content).hexdigest()
    existing = await session.scalar(select(Document).where(Document.checksum == checksum))
    if existing:
        count = await session.scalar(
            select(func.count(Chunk.id)).where(Chunk.document_id == existing.id)
        )
        return existing, int(count or 0), True

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
    for chunk, vector in zip(chunks, vectors):
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
    await session.commit()
    return document, len(rows), False
