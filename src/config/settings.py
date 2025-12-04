"""集中管理项目配置，确保各模块一致读取环境变量。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv

# 提前加载 .env，避免各模块重复调用
load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _coerce_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _normalize_conn_string(conn_str: str) -> str:
    """Ensure connection string query params are well-formed."""
    parts = urlsplit(conn_str)
    if not parts.query:
        return conn_str

    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    modified = False
    for idx, (key, value) in enumerate(query_pairs):
        if key == "sslmode" and value == "":
            query_pairs[idx] = (key, "disable")
            modified = True
            break

    if not modified:
        return conn_str

    new_query = urlencode(query_pairs, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


@dataclass(frozen=True)
class Settings:
    """Immutable settings object loaded from environment variables."""

    model_name: str
    dascope_api_key: Optional[str]
    dascope_base_url: Optional[str]
    openai_embeddings_api_key: str
    litellm_base_url: Optional[str]
    postgres_connection_string: str
    default_collection: str
    chunk_size: int
    chunk_overlap: int
    retriever_top_k: int

    @property
    def psycopg_connection(self) -> str:
        """Coerce connection string to psycopg3 driver URI."""
        conn_str = self.postgres_connection_string
        if conn_str.startswith("postgresql://"):
            return conn_str.replace("postgresql://", "postgresql+psycopg://", 1)
        if not conn_str.startswith("postgresql+psycopg://") and "://" in conn_str:
            return f"postgresql+psycopg://{conn_str.split('://', 1)[-1]}"
        return conn_str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    raw_conn = _require_env("POSTGRES_CONNECTION_STRING")
    normalized_conn = _normalize_conn_string(raw_conn)

    return Settings(
        model_name=os.getenv("MODEL_NAME", "qwen-plus-latest"),
        dascope_api_key=os.getenv("DASHSCOPE_API_KEY"),
        dascope_base_url=os.getenv("DASHSCOPE_BASE_URL"),
        openai_embeddings_api_key=_require_env("OPENAI_EMBEDDINGS_API_KEY"),
        litellm_base_url=os.getenv("LITELLM_BASE_URL"),
        postgres_connection_string=normalized_conn,
        default_collection=os.getenv("VECTOR_COLLECTION", "pdf_documents"),
        chunk_size=_coerce_int("CHUNK_SIZE", 1000),
        chunk_overlap=_coerce_int("CHUNK_OVERLAP", 200),
        retriever_top_k=_coerce_int("RETRIEVER_TOP_K", 2),
    )


__all__ = ["Settings", "get_settings"]

