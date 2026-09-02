import pytest

from evaluation.evaluate import score_retrieval


def test_recall_at_five_counts_all_relevant_documents():
    recall, reciprocal_rank = score_retrieval(
        ["document-a", "irrelevant", "document-b", "document-c"],
        {"document-a", "document-b", "document-missing"},
    )

    assert recall == pytest.approx(2 / 3)
    assert reciprocal_rank == 1.0


def test_duplicate_chunks_do_not_inflate_document_recall():
    recall, reciprocal_rank = score_retrieval(
        ["irrelevant", "document-a", "document-a", "document-b", "document-c"],
        {"document-a", "document-b"},
    )

    assert recall == 1.0
    assert reciprocal_rank == 0.5


def test_retrieval_score_requires_a_relevant_document():
    with pytest.raises(ValueError, match="at least one document"):
        score_retrieval(["document-a"], set())
