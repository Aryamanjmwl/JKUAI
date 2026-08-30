import asyncio
from functools import lru_cache

from sentence_transformers import CrossEncoder, SentenceTransformer

from ..config import get_settings


@lru_cache
def embedding_model() -> SentenceTransformer:
    return SentenceTransformer(get_settings().embedding_model)


@lru_cache
def reranker_model() -> CrossEncoder:
    return CrossEncoder(get_settings().reranker_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    vectors = embedding_model().encode(texts, normalize_embeddings=True)
    return vectors.tolist()


def rerank(query: str, candidates: list[dict], limit: int) -> list[dict]:
    if not candidates:
        return []
    scores = reranker_model().predict([(query, item["content"]) for item in candidates])
    enriched = [dict(item, rerank_score=float(score)) for item, score in zip(candidates, scores)]
    return sorted(enriched, key=lambda item: item["rerank_score"], reverse=True)[:limit]


async def embed_texts_async(texts: list[str]) -> list[list[float]]:
    return await asyncio.to_thread(embed_texts, texts)


async def rerank_async(query: str, candidates: list[dict], limit: int) -> list[dict]:
    return await asyncio.to_thread(rerank, query, candidates, limit)
