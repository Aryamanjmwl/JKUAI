"""Opt-in checks against real pgvector, OpenSearch, and sentence-transformer models."""

import asyncio
import os

import asyncpg
import httpx
import pytest
from app.config import get_settings
from app.services.opensearch import client as opensearch_client

from scripts.demo import FIXTURES, build_pdf, check, seed

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1", reason="Set RUN_INTEGRATION=1 with the live stack running"
)


def test_live_ingestion_retrieval_duplicates_and_acl_revocation(tmp_path):
    settings = get_settings()
    with httpx.Client(
        base_url=os.getenv("TEST_API_URL", "http://localhost:8000"), timeout=180
    ) as api:
        manifest = seed(api, tmp_path)
        assert check(api, manifest)["status"] == "passed"
        # Repeat uploads exercise checksum deduplication and lexical reindexing.
        assert seed(api, tmp_path) == manifest
        restricted_id = manifest["documents"]["demo-staff-operations.pdf"]
        fixture = FIXTURES[2]
        conflict = api.post(
            "/documents",
            data={"title": "Public copy", "visibility": "public"},
            files={"file": ("copy.pdf", build_pdf(fixture["text"]), "application/pdf")},
        )
        assert conflict.status_code == 409
        assert "document_id" not in conflict.json()
        assert fixture["title"] not in conflict.text

        async def set_groups(groups):
            connection = await asyncpg.connect(
                settings.database_url.replace("postgresql+asyncpg:", "postgresql:")
            )
            try:
                await connection.execute(
                    "UPDATE documents SET allowed_groups=$1 WHERE id=$2::uuid",
                    groups,
                    restricted_id,
                )
            finally:
                await connection.close()

        asyncio.run(set_groups(["admissions"]))
        try:
            # Deliberately leave the lexical ACL stale: OpenSearch still permits staff.
            with opensearch_client() as search:
                stale = search.search(
                    index=settings.opensearch_index,
                    body={"query": {"term": {"document_id": restricted_id}}},
                )
            assert stale["hits"]["hits"][0]["_source"]["allowed_groups"] == ["staff"]
            response = api.post(
                "/search/retrieval",
                json={"query": "EXAM-OPS-42 ORCHID-742"},
                headers={"X-User-Groups": "staff"},
            )
            response.raise_for_status()
            assert restricted_id not in {
                source["document_id"] for source in response.json()["sources"]
            }
            assert "ORCHID-742" not in response.text
        finally:
            asyncio.run(set_groups(["staff"]))
