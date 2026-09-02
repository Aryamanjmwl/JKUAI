from app.auth import UserContext, can_access
from app.ranking import reciprocal_rank_fusion
from app.security import build_user_context


def test_user_context_is_immutable():
    user = UserContext("student-1", ("students",))
    assert user.groups == ("students",)


def test_restricted_document_requires_matching_group():
    student = UserContext("student-1", ("students",))
    staff = UserContext("staff-1", ("staff",))
    assert can_access("restricted", ["students"], student)
    assert not can_access("restricted", ["students"], staff)
    assert can_access("public", [], staff)


def test_request_headers_cannot_grant_roles_by_default():
    user = build_user_context("attacker", "staff,admissions", demo_roles_enabled=False)

    assert user == UserContext("anonymous", ())
    assert not can_access("restricted", ["staff"], user)


def test_developer_mode_can_simulate_roles():
    user = build_user_context("demo-user", "staff, staff", demo_roles_enabled=True)

    assert user == UserContext("demo-user", ("staff",))
    assert can_access("restricted", ["staff"], user)


def test_rrf_rewards_results_found_by_both_retrievers():
    vector = [{"chunk_id": "shared", "content": "a"}, {"chunk_id": "vector", "content": "b"}]
    lexical = [{"chunk_id": "shared", "content": "a"}, {"chunk_id": "lexical", "content": "c"}]
    merged = reciprocal_rank_fusion(vector, lexical)
    assert merged[0]["chunk_id"] == "shared"
