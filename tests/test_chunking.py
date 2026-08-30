import pytest
from app.chunking import TextPage, chunk_pages


def test_chunking_preserves_page_number_and_overlap():
    text = " ".join(f"word{i}" for i in range(200))
    chunks = chunk_pages([TextPage(3, text)], chunk_size=180, overlap=30)
    assert len(chunks) > 1
    assert all(chunk.page_number == 3 for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_pages([TextPage(1, "content")], chunk_size=100, overlap=100)
