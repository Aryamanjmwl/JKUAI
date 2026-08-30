from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "JKU Knowledge Search"
    database_url: str = "postgresql+asyncpg://jku:jku@localhost:5432/jku_search"
    opensearch_url: str = "http://localhost:9200"
    opensearch_index: str = "jku_chunks"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6-mini"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    vector_dimension: int = 384
    retrieve_k: int = 20
    rerank_k: int = 5
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
