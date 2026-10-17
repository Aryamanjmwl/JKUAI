from unittest.mock import Mock, patch

import pytest
from app.services.generation import InvalidOpenAICredentialsError, _generate_answer_sync

HITS = [
    {
        "title": "Computer Science Curriculum",
        "page_number": 12,
        "content": "Advanced Machine Learning requires prior machine learning knowledge.",
    }
]


def test_generation_does_not_require_a_key_when_retrieval_is_empty():
    answer = _generate_answer_sync("Unknown question", [], None)

    assert answer == "I could not find an accessible source that answers this question."


def test_generation_requires_a_request_scoped_key():
    with pytest.raises(InvalidOpenAICredentialsError):
        _generate_answer_sync("What is required?", HITS, None)


def test_generation_passes_the_request_key_to_openai():
    response = Mock(output_text="Machine learning knowledge is required. [S1]")
    with patch("app.services.generation.OpenAI") as client_class:
        client_class.return_value.__enter__.return_value.responses.create.return_value = response

        answer = _generate_answer_sync("What is required?", HITS, "  sk-test  ")

    client_class.assert_called_once_with(api_key="sk-test", timeout=30.0, max_retries=1)
    assert answer == response.output_text


@pytest.mark.parametrize("answer", ["", "Unsupported answer", "Invented. [S99]", "Mixed. [S1][S2]"])
def test_missing_or_invented_citations_fail_closed(answer):
    from app.services.generation import INSUFFICIENT_EVIDENCE, validate_answer

    assert validate_answer(answer, 1) == INSUFFICIENT_EVIDENCE


def test_valid_citation_ids_are_preserved():
    from app.services.generation import validate_answer

    assert validate_answer("Required. [S1]", 1) == "Required. [S1]"


def test_generation_uses_real_sdk_request_and_response_contract():
    import json

    import httpx
    from openai import OpenAI as SDKClient

    requests = []

    def provider(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 1,
                "model": "gpt-4.1-mini",
                "output": [
                    {
                        "type": "message",
                        "id": "msg_test",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "Machine learning knowledge. [S1]",
                                "annotations": [],
                            }
                        ],
                    }
                ],
            },
        )

    def make_client(**kwargs):
        return SDKClient(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(provider))
        )

    with patch("app.services.generation.OpenAI", side_effect=make_client):
        answer = _generate_answer_sync("What is required?", HITS, "sk-test")
    assert answer == "Machine learning knowledge. [S1]"
    assert requests[0]["store"] is False
    assert requests[0]["max_output_tokens"] == 700
    assert HITS[0]["content"] in requests[0]["input"]


@pytest.mark.parametrize(
    "code,error_type,expected",
    [
        ("insufficient_quota", "insufficient_quota", "OpenAIQuotaError"),
        ("credit_balance_exhausted", "insufficient_quota", "OpenAIQuotaError"),
        ("organization_spend_limit_exceeded", None, "OpenAIQuotaError"),
        ("project_spend_limit_exceeded", None, "OpenAIQuotaError"),
        ("rate_limit_exceeded", "tokens", "OpenAIRateLimitError"),
        ("slow_down", "rate_limit_error", "OpenAIRateLimitError"),
    ],
)
def test_real_sdk_provider_errors_are_classified_without_leaking_secrets(
    code, error_type, expected
):
    import httpx
    from app.services import generation
    from openai import OpenAI as SDKClient

    def provider(request):
        assert request.headers["authorization"] == "Bearer sk-secret"
        return httpx.Response(
            429,
            json={
                "error": {
                    "message": "provider detail sk-secret",
                    "type": error_type,
                    "code": code,
                }
            },
        )

    def make_client(**kwargs):
        kwargs["max_retries"] = 0
        return SDKClient(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(provider))
        )

    with (
        patch("app.services.generation.OpenAI", side_effect=make_client),
        pytest.raises(getattr(generation, expected)) as caught,
    ):
        _generate_answer_sync("What is required?", HITS, "sk-secret")
    assert "sk-secret" not in str(caught.value)
