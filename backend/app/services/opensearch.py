import asyncio

from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk

from ..config import get_settings


def client() -> OpenSearch:
    settings = get_settings()
    return OpenSearch(settings.opensearch_url, use_ssl=False, verify_certs=False)


def ensure_index() -> None:
    settings = get_settings()
    search = client()
    if search.indices.exists(index=settings.opensearch_index):
        return
    search.indices.create(
        index=settings.opensearch_index,
        body={
            "mappings": {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "document_id": {"type": "keyword"},
                    "title": {"type": "text"},
                    "content": {"type": "text"},
                    "visibility": {"type": "keyword"},
                    "allowed_groups": {"type": "keyword"},
                }
            }
        },
    )


def index_chunks(payloads: list[dict]) -> None:
    settings = get_settings()
    actions = [
        {
            "_index": settings.opensearch_index,
            "_id": payload["chunk_id"],
            "_source": payload,
        }
        for payload in payloads
    ]
    bulk(client(), actions, refresh="wait_for")


async def ensure_index_async() -> None:
    await asyncio.to_thread(ensure_index)


async def index_chunks_async(payloads: list[dict]) -> None:
    await asyncio.to_thread(index_chunks, payloads)


async def search_async(body: dict) -> dict:
    settings = get_settings()
    return await asyncio.to_thread(client().search, index=settings.opensearch_index, body=body)
