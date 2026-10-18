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


def test_semester_aliases_preserve_question_and_add_shared_search_terms():
    from app.services.query import semester_query

    original = "Welche Lehrveranstaltungen sind im ersten Wintersemester Informatik empfohlen?"
    expanded = semester_query(original)
    assert expanded.startswith(original)
    assert "winter semester" in expanded
    assert "first semester 1. Semester" in expanded
    assert "courses" in expanded
    assert "recommended" in expanded
    assert "Sommersemester" not in expanded
    assert "summer semester" in semester_query("Which courses are in the second summer semester?")
    assert "2. Semester" in semester_query("Which courses are in the second summer semester?")
    assert semester_query("course prerequisites") == "course prerequisites"


def test_english_keyword_aliases_do_not_change_semantic_query_or_permissions():
    query = "How can I find an exam when I am not a participant in the course?"
    session = AsyncMock()
    session.execute.return_value = Mock(all=Mock(return_value=[]))
    with (
        patch(
            "app.services.search.embed_texts_async", AsyncMock(return_value=[[0.1] * 384])
        ) as embed,
        patch(
            "app.services.search.search_async",
            AsyncMock(return_value={"hits": {"hits": []}}),
        ) as lexical,
        patch("app.services.search.rerank_async", AsyncMock(return_value=[])) as rerank,
    ):
        asyncio.run(hybrid_search(session, query, UserContext("guest", ())))
    assert embed.call_args.args[0] == [query]
    assert rerank.call_args.args[0] == query
    assert lexical.call_count == 2
    original_body, body = [call.args[0] for call in lexical.call_args_list]
    assert original_body["query"]["bool"]["must"][0]["multi_match"]["query"] == query
    expanded = body["query"]["bool"]["must"][0]["multi_match"]["query"]
    assert expanded.startswith(query)
    assert all(
        term in expanded for term in ("Prüfungen", "Teilnehmer", "Lehrveranstaltung", "Suche")
    )
    assert body["query"]["bool"]["filter"] == [
        {"bool": {"should": [{"term": {"visibility": "public"}}], "minimum_should_match": 1}}
    ]


def test_keyword_aliases_leave_german_and_unrelated_questions_unchanged():
    from app.services.query import lexical_query

    for query in (
        "Wie finde ich eine Prüfung ohne Teilnehmerstatus?",
        "What is the robotics laboratory address?",
        "Where is the courseware for the research project?",
    ):
        assert lexical_query(query) == query


def test_unique_lexical_candidate_survives_until_reranking():
    from app.config import Settings

    document = SimpleNamespace(
        id=uuid4(), title="Curriculum", file_name="guide.pdf", source_url=None
    )
    vector_chunk = SimpleNamespace(id=uuid4(), page_number=1, content="Cover")
    original_chunk = SimpleNamespace(id=uuid4(), page_number=5, content="StEOP credit limit")
    lexical_chunk = SimpleNamespace(
        id=uuid4(), page_number=10, content="First winter semester courses"
    )
    vector_rows, lexical_rows = Mock(), Mock()
    vector_rows.all.return_value = [(vector_chunk, document, 0.2)]
    lexical_rows.all.return_value = [(original_chunk, document), (lexical_chunk, document)]
    session = AsyncMock()
    session.execute.side_effect = [vector_rows, lexical_rows]
    with (
        patch("app.services.search.get_settings", return_value=Settings(retrieve_k=1, rerank_k=1)),
        patch("app.services.search.embed_texts_async", AsyncMock(return_value=[[0.1] * 384])),
        patch(
            "app.services.search.search_async",
            AsyncMock(
                side_effect=[
                    {"hits": {"hits": [{"_source": {"chunk_id": str(original_chunk.id)}}]}},
                    {"hits": {"hits": [{"_source": {"chunk_id": str(lexical_chunk.id)}}]}},
                ]
            ),
        ),
        patch("app.services.search.rerank_async", AsyncMock(return_value=[])) as rerank,
    ):
        asyncio.run(hybrid_search(session, "winter semester courses", UserContext("guest", ())))
    assert {hit["chunk_id"] for hit in rerank.call_args.args[1]} == {
        str(vector_chunk.id),
        str(original_chunk.id),
        str(lexical_chunk.id),
    }
