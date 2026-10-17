from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.auth import UserContext
from app.database import get_session
from app.main import app
from app.security import get_user_context
from app.services.generation import (
    InvalidOpenAICredentialsError,
    OpenAIQuotaError,
    OpenAIServiceError,
)
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    async def session():
        mock = AsyncMock()
        mock.scalar.return_value = None
        yield mock

    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_user_context] = lambda: UserContext("guest", ())
    with patch("app.main.ensure_index_async", AsyncMock()), TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def hits():
    return [
        {
            "document_id": str(uuid4()),
            "chunk_id": str(uuid4()),
            "title": "Fixture guide",
            "file_name": "guide.pdf",
            "source_url": None,
            "page_number": 2,
            "content": "Prerequisites: introductory machine learning.",
            "rerank_score": 1.5,
        }
    ]


def test_retrieval_does_not_call_generation_or_require_credentials(client, hits):
    with (
        patch("app.main.hybrid_search", AsyncMock(return_value=hits)),
        patch("app.main.generate_answer", AsyncMock()) as generate,
    ):
        response = client.post("/search/retrieval", json={"query": "course requirements"})
    assert response.status_code == 200
    assert response.json()["sources"][0]["citation_id"] == "S1"
    assert response.json()["exact_documents_used"] == ["guide.pdf"]
    generate.assert_not_called()


def test_answer_lists_only_documents_actually_cited(client, hits):
    unused = dict(hits[0], file_name="unused.pdf", chunk_id=str(uuid4()), document_id=str(uuid4()))
    with (
        patch("app.main.hybrid_search", AsyncMock(return_value=hits + [unused])),
        patch("app.main.generate_answer", AsyncMock(return_value="Introductory ML. [S1]")),
    ):
        response = client.post("/search", json={"query": "course requirements"})
    assert response.status_code == 200
    assert len(response.json()["sources"]) == 2
    assert response.json()["exact_documents_used"] == ["guide.pdf"]


@pytest.mark.parametrize(
    "error,status",
    [
        (InvalidOpenAICredentialsError, 401),
        (OpenAIQuotaError, 429),
        (OpenAIServiceError, 502),
    ],
)
def test_provider_errors_have_stable_http_responses(client, hits, error, status):
    with (
        patch("app.main.hybrid_search", AsyncMock(return_value=hits)),
        patch("app.main.generate_answer", AsyncMock(side_effect=error)),
    ):
        response = client.post("/search", json={"query": "course requirements"})
    assert response.status_code == status
    assert "detail" in response.json()


@pytest.mark.parametrize("query", ["   ", " x ", "x" * 1001])
def test_invalid_queries_are_rejected_before_retrieval(client, query):
    with patch("app.main.hybrid_search", AsyncMock()) as search:
        assert client.post("/search/retrieval", json={"query": query}).status_code == 422
    search.assert_not_called()


@pytest.mark.parametrize(
    "data,status",
    [
        ({"title": " ", "visibility": "public"}, 422),
        ({"title": "Guide", "visibility": "restricted"}, 400),
        ({"title": "Guide", "source_url": "javascript:alert(1)"}, 422),
    ],
)
def test_invalid_upload_metadata(client, data, status):
    response = client.post(
        "/documents", data=data, files={"file": ("x.pdf", b"bad", "application/pdf")}
    )
    assert response.status_code == status


def test_corrupt_pdf_returns_validation_error(client):
    response = client.post(
        "/documents",
        data={"title": "Guide"},
        files={"file": ("x.pdf", b"not a PDF", "application/pdf")},
    )
    assert response.status_code == 422


def test_upload_limit_is_enforced(client):
    from app.config import Settings

    with patch("app.main.get_settings", return_value=Settings(max_upload_bytes=3)):
        response = client.post(
            "/documents",
            data={"title": "Guide"},
            files={"file": ("x.pdf", b"1234", "application/pdf")},
        )
    assert response.status_code == 413


def test_readiness_checks_schema_and_lexical_index(client):
    with patch("app.main.index_available_async", AsyncMock(return_value=True)):
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["demo_roles_enabled"] is False


def test_readiness_is_unavailable_without_lexical_index(client):
    with patch("app.main.index_available_async", AsyncMock(return_value=False)):
        assert client.get("/ready").status_code == 503


def test_readiness_is_unavailable_when_schema_query_fails(client):
    from sqlalchemy.exc import OperationalError

    async def failing_session():
        session = AsyncMock()
        session.execute.side_effect = OperationalError("query", {}, Exception("database down"))
        yield session

    app.dependency_overrides[get_session] = failing_session
    with patch("app.main.index_available_async", AsyncMock(return_value=True)):
        assert client.get("/ready").status_code == 503


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_supported_local_browser_origins(client, origin):
    response = client.options(
        "/search/retrieval",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_source_excerpts_include_the_entire_passage_supplied_to_generation(client, hits):
    hits[0]["content"] = "Context. " * 70 + "The supporting statement appears at the end."
    with patch("app.main.hybrid_search", AsyncMock(return_value=hits)):
        response = client.post("/search/retrieval", json={"query": "supporting statement"})
    assert response.status_code == 200
    assert response.json()["sources"][0]["excerpt"] == hits[0]["content"]
