from dataclasses import dataclass


@dataclass(frozen=True)
class TextPage:
    page_number: int | None
    text: str


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    page_number: int | None
    content: str


def chunk_pages(
    pages: list[TextPage], chunk_size: int = 900, overlap: int = 150
) -> list[TextChunk]:
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    chunks: list[TextChunk] = []
    index = 0
    for page in pages:
        text = " ".join(page.text.split())
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            if end < len(text):
                boundary = text.rfind(" ", start, end)
                if boundary > start + chunk_size // 2:
                    end = boundary
            content = text[start:end].strip()
            if content:
                chunks.append(TextChunk(index, page.page_number, content))
                index += 1
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks
