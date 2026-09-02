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
        client_class.return_value.responses.create.return_value = response

        answer = _generate_answer_sync("What is required?", HITS, "  sk-test  ")

    client_class.assert_called_once_with(api_key="sk-test")
    assert answer == response.output_text
