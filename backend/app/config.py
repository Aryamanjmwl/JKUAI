from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "JKU Knowledge Search"
    database_url: str = "postgresql+asyncpg://jku:jku@localhost:5432/jku_search"
    opensearch_url: str = "http://localhost:9200"
    opensearch_index: str = "jku_chunks"
    gemini_model: str = "gemini-3.1-flash-lite"
    openai_model: str = "gpt-4.1-mini"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    # The initial database migration creates a vector(384) column.
    vector_dimension: int = Field(default=384, ge=384, le=384)
    retrieve_k: int = Field(default=20, ge=1, le=200)
    rerank_k: int = Field(default=5, ge=1, le=200)
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    enable_demo_roles: bool = False
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_ranking_limits(self):
        if self.rerank_k > self.retrieve_k:
            raise ValueError("rerank_k must not exceed retrieve_k")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
