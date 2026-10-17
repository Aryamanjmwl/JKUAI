import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from app.auth import UserContext
from app.services.search import _permission_clause, hybrid_search
from sqlalchemy.dialects import postgresql


def sql(statement):
    return str(
        statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


def test_public_filter_does_not_accept_group_membership():
    assert sql(_permission_clause(UserContext("guest", ()))) == "documents.visibility = 'public'"


def test_group_filter_requires_restricted_visibility():
    clause = sql(_permission_clause(UserContext("demo", ("staff",))))
    assert "documents.visibility = 'restricted'" in clause
    assert "documents.allowed_groups && ARRAY['staff']" in clause


def test_lexical_results_are_reauthorized_before_fusion_and_reranking():
    chunk_id, document_id = uuid4(), uuid4()
    chunk = SimpleNamespace(id=chunk_id, page_number=2, content="Permitted source")
    document = SimpleNamespace(
        id=document_id, title="Guide", file_name="guide.pdf", source_url=None
    )
    vector_rows = Mock()
    vector_rows.all.return_value = [(chunk, document, 0.2)]
    lexical_rows = Mock()
    # Simulate a stale OpenSearch hit removed by the authoritative SQL ACL filter.
    lexical_rows.all.return_value = []
    session = AsyncMock()
    session.execute.side_effect = [vector_rows, lexical_rows]
    stale_id = str(uuid4())
    reranker = AsyncMock(return_value=[])
    with (
        patch("app.services.search.embed_texts_async", AsyncMock(return_value=[[0.1] * 384])),
        patch(
            "app.services.search.search_async",
            AsyncMock(return_value={"hits": {"hits": [{"_source": {"chunk_id": stale_id}}]}}),
        ) as lexical,
        patch("app.services.search.rerank_async", reranker),
    ):
        asyncio.run(hybrid_search(session, "course prerequisites", UserContext("guest", ())))

    hydration = sql(session.execute.call_args_list[1].args[0])
    assert "documents.visibility = 'public'" in hydration
    assert stale_id.replace("-", "") in hydration.replace("-", "")
    assert [hit["chunk_id"] for hit in reranker.call_args.args[1]] == [str(chunk_id)]
    filters = lexical.call_args.args[0]["query"]["bool"]["filter"]
    assert filters == [
        {"bool": {"should": [{"term": {"visibility": "public"}}], "minimum_should_match": 1}}
    ]
