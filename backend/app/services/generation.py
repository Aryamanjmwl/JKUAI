import asyncio

from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from ..config import get_settings

SYSTEM_PROMPT = """You answer questions using only the supplied university sources.
Every factual claim must end with one or more source markers such as [S1] or [S1][S2].
If the sources do not establish the answer, say that clearly. Never invent a requirement,
course prerequisite, deadline, or regulation. Keep the answer concise and practical."""


class InvalidOpenAICredentialsError(Exception):
    """Raised when OpenAI rejects a request-scoped credential."""


class OpenAIQuotaError(Exception):
    """Raised when the credential has no available rate or billing quota."""


class OpenAIServiceError(Exception):
    """Raised when OpenAI cannot complete a valid request."""


def _generate_answer_sync(query: str, hits: list[dict], api_key: str | None) -> str:
    settings = get_settings()
    if not hits:
        return "I could not find an accessible source that answers this question."
    effective_api_key = (api_key or "").strip()
    if not effective_api_key:
        raise InvalidOpenAICredentialsError
    context = "\n\n".join(
        f"[S{i}] {hit['title']} (page {hit['page_number'] or 'unknown'})\n{hit['content']}"
        for i, hit in enumerate(hits, start=1)
    )
    try:
        response = OpenAI(api_key=effective_api_key).responses.create(
            model=settings.openai_model,
            instructions=SYSTEM_PROMPT,
            input=f"Question: {query}\n\nSources:\n{context}",
        )
    except (AuthenticationError, PermissionDeniedError) as exc:
        raise InvalidOpenAICredentialsError from exc
    except RateLimitError as exc:
        raise OpenAIQuotaError from exc
    except (APIConnectionError, APIStatusError) as exc:
        raise OpenAIServiceError from exc
    return response.output_text


async def generate_answer(query: str, hits: list[dict], api_key: str | None) -> str:
    return await asyncio.to_thread(_generate_answer_sync, query, hits, api_key)
