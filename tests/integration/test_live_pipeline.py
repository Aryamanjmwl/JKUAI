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


@pytest.mark.skipif(
    not os.getenv("OFFICIAL_PDF"), reason="Set OFFICIAL_PDF to a downloaded JKU curriculum PDF"
)
def test_official_curriculum_pdf_returns_page_link_and_supporting_passage():
    from pathlib import Path

    source_url = "https://studienhandbuch.jku.at/texte/1170_7_MS_ComputerScience.pdf"
    with httpx.Client(
        base_url=os.getenv("TEST_API_URL", "http://localhost:8000"), timeout=180
    ) as api:
        response = api.post(
            "/documents",
            data={"title": "JKU Master's Curriculum in Computer Science", "source_url": source_url},
            files={
                "file": (
                    "jku-ms-computer-science-curriculum.pdf",
                    Path(os.environ["OFFICIAL_PDF"]).read_bytes(),
                    "application/pdf",
                )
            },
        )
        response.raise_for_status()
        document_id = response.json()["document_id"]
        response = api.post(
            "/search/retrieval",
            json={
                "query": "How many ECTS points is the written Master's thesis in Computer Science worth?"
            },
        )
        response.raise_for_status()
        sources = response.json()["sources"]
        matches = [
            s for s in sources if s["document_id"] == document_id and "25 ECTS" in s["excerpt"]
        ]
        assert matches, (
            "Expected a passage supporting the thesis-credit answer from the official PDF"
        )
        assert matches[0]["page_number"] == 7
        assert matches[0]["source_url"] == source_url
        assert matches[0]["citation_id"].startswith("S")
