import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from app.auth import UserContext
from app.services.ingestion import DocumentConflictError, ingest_pdf, parse_pdf


@pytest.mark.parametrize(
    "visibility,groups,user",
    [
        ("public", [], UserContext("guest", ())),
        ("restricted", ["other"], UserContext("staff", ("staff",))),
        ("restricted", ["staff"], UserContext("guest", ())),
    ],
)
def test_duplicate_upload_cannot_disclose_or_reclassify_restricted_document(
    visibility, groups, user
):
    session = AsyncMock()
    session.scalar.return_value = SimpleNamespace(
        id=uuid4(), title="Hidden title", visibility="restricted", allowed_groups=["staff"]
    )
    with (
        patch("app.services.ingestion.index_chunks_async", AsyncMock()) as index,
        pytest.raises(DocumentConflictError, match="conflicts with an existing document"),
    ):
        asyncio.run(
            ingest_pdf(
                session,
                content=b"same bytes",
                file_name="test.pdf",
                title="Different title",
                source_url=None,
                visibility=visibility,
                allowed_groups=groups,
                user=user,
            )
        )
    index.assert_not_called()


def test_duplicate_retry_repairs_lexical_index_from_stored_permissions():
    document = SimpleNamespace(
        id=uuid4(), title="Stored title", visibility="restricted", allowed_groups=["staff"]
    )
    chunk = SimpleNamespace(id=uuid4(), content="Stored text")
    session = AsyncMock()
    session.scalar.side_effect = [document, 1]
    session.scalars.return_value = Mock()
    session.scalars.return_value.all.return_value = [chunk]
    with patch("app.services.ingestion.index_chunks_async", AsyncMock()) as index:
        result = asyncio.run(
            ingest_pdf(
                session,
                content=b"same bytes",
                file_name="test.pdf",
                title="Different title",
                source_url=None,
                visibility="restricted",
                allowed_groups=["staff"],
                user=UserContext("staff", ("staff",)),
            )
        )
    assert result == (document, 1, True)
    assert index.call_args.args[0][0]["allowed_groups"] == ["staff"]
    assert index.call_args.args[0][0]["title"] == "Stored title"


def test_invalid_pdf_is_a_domain_validation_error():
    with pytest.raises(ValueError, match="could not be read"):
        parse_pdf(b"not a PDF")
