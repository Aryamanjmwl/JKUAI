import asyncio

from openai import OpenAI

from ..config import get_settings

SYSTEM_PROMPT = """You answer questions using only the supplied university sources.
Every factual claim must end with one or more source markers such as [S1] or [S1][S2].
If the sources do not establish the answer, say that clearly. Never invent a requirement,
course prerequisite, deadline, or regulation. Keep the answer concise and practical."""


def _generate_answer_sync(query: str, hits: list[dict]) -> str:
    settings = get_settings()
    if not hits:
        return "I could not find an accessible source that answers this question."
    if not settings.openai_api_key:
        return "Retrieval succeeded, but OPENAI_API_KEY is not configured. See the sources below."
    context = "\n\n".join(
        f"[S{i}] {hit['title']} (page {hit['page_number'] or 'unknown'})\n{hit['content']}"
        for i, hit in enumerate(hits, start=1)
    )
    response = OpenAI(api_key=settings.openai_api_key).responses.create(
        model=settings.openai_model,
        instructions=SYSTEM_PROMPT,
        input=f"Question: {query}\n\nSources:\n{context}",
    )
    return response.output_text


async def generate_answer(query: str, hits: list[dict]) -> str:
    return await asyncio.to_thread(_generate_answer_sync, query, hits)
