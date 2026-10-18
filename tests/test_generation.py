from unittest.mock import Mock, patch

import pytest
from app.services.generation import InvalidProviderCredentialsError, _generate_answer_sync

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
    with pytest.raises(InvalidProviderCredentialsError):
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
        ("insufficient_quota", "insufficient_quota", "ProviderQuotaError"),
        ("credit_balance_exhausted", "insufficient_quota", "ProviderQuotaError"),
        ("organization_spend_limit_exceeded", None, "ProviderQuotaError"),
        ("project_spend_limit_exceeded", None, "ProviderQuotaError"),
        ("rate_limit_exceeded", "tokens", "ProviderRateLimitError"),
        ("slow_down", "rate_limit_error", "ProviderRateLimitError"),
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


@pytest.mark.parametrize(
    "text,finish_reason,expected",
    [
        ("Prior ML knowledge. [S1]", "stop", "Prior ML knowledge. [S1]"),
        (
            "Invented source. [S99]",
            "stop",
            "I could not establish an answer from the accessible sources.",
        ),
        ("Uncited answer", "stop", "I could not establish an answer from the accessible sources."),
        (None, "stop", "I could not establish an answer from the accessible sources."),
        (
            "Partial answer. [S1]",
            "length",
            "I could not establish an answer from the accessible sources.",
        ),
    ],
)
def test_gemini_uses_google_endpoint_and_validates_real_sdk_response(text, finish_reason, expected):
    import json

    import httpx
    from app.services.generation import GEMINI_BASE_URL
    from openai import OpenAI as SDKClient

    requests = []

    def provider(request):
        assert str(request.url) == GEMINI_BASE_URL + "chat/completions"
        assert request.headers["authorization"] == "Bearer google-test-key"
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "chat_test",
                "object": "chat.completion",
                "created": 1,
                "model": "gemini-3.1-flash-lite",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": text},
                        "finish_reason": finish_reason,
                    }
                ],
            },
        )

    def make_client(**kwargs):
        return SDKClient(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(provider))
        )

    with patch("app.services.generation.OpenAI", side_effect=make_client):
        assert (
            _generate_answer_sync("What is required?", HITS, " google-test-key ", "gemini")
            == expected
        )
    assert requests[0]["model"] == "gemini-3.1-flash-lite"
    assert requests[0]["max_tokens"] == 2048
    assert requests[0]["reasoning_effort"] == "minimal"
    assert HITS[0]["content"] in requests[0]["messages"][1]["content"]
    assert "[S1]" in requests[0]["messages"][1]["content"]
    assert "store" not in requests[0]  # Responses-only arguments are not sent to Google.


@pytest.mark.parametrize(
    "status,body,expected",
    [
        (
            400,
            {"message": "API key not valid. secret", "status": "INVALID_ARGUMENT"},
            "InvalidProviderCredentialsError",
        ),
        (401, {"message": "secret"}, "InvalidProviderCredentialsError"),
        (403, {"message": "secret", "status": "PERMISSION_DENIED"}, "ProviderAccessError"),
        (404, {"message": "model unavailable secret"}, "ProviderConfigurationError"),
        (400, {"message": "unsupported parameter secret"}, "ProviderConfigurationError"),
        (
            429,
            {"message": "free quota secret", "status": "RESOURCE_EXHAUSTED"},
            "ProviderRateLimitError",
        ),
        (503, {"message": "overloaded secret"}, "ProviderServiceError"),
    ],
)
def test_gemini_errors_are_safe_and_do_not_fall_back_to_openai(status, body, expected):
    import httpx
    from app.services import generation
    from openai import OpenAI as SDKClient

    calls = []

    def provider(request):
        calls.append(request.url.host)
        return httpx.Response(status, json={"error": body})

    def make_client(**kwargs):
        kwargs["max_retries"] = 0
        return SDKClient(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(provider))
        )

    with (
        patch("app.services.generation.OpenAI", side_effect=make_client),
        pytest.raises(getattr(generation, expected)) as caught,
    ):
        _generate_answer_sync("Question", HITS, "secret", "gemini")
    assert calls == ["generativelanguage.googleapis.com"]
    assert "secret" not in str(caught.value)
