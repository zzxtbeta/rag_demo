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
    """确保连接字符串查询参数格式正确。"""
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
    """不可变设置对象，从环境变量加载。"""

    chat_model: str
    dashscope_api_key: Optional[str]
    dascope_base_url: Optional[str]
    embeddings_model: str
    litellm_base_url: Optional[str]
    postgres_connection_string: str
    default_collection: str
    chunk_size: int
    chunk_overlap: int
    retriever_top_k: int
    rerank_enabled: bool
    rerank_model: str
    rerank_top_n: int
    redis_url: Optional[str]
    redis_stream_enabled: bool
    stream_ttl_seconds: int
    stream_max_length: int
    workflow_timeout_seconds: int
    # LangSmith 配置
    langsmith_api_key: Optional[str]
    langsmith_endpoint: str
    langsmith_project: str
    # Document processing 配置
    frontend_images_dir: str
    frontend_image_prefix: str
    # Project search API 配置
    project_search_api_url: Optional[str]
    project_search_api_username: Optional[str]
    project_search_api_password: Optional[str]
    project_search_enabled: bool
    # Project search database 配置（如果直接访问数据库而非 API）
    project_search_db_url: Optional[str]

    @property
    def psycopg_connection(self) -> str:
        """将连接字符串强制为 psycopg3 驱动程序 URI。"""
        conn_str = self.postgres_connection_string
        if conn_str.startswith("postgresql://"):
            return conn_str.replace("postgresql://", "postgresql+psycopg://", 1)
        if not conn_str.startswith("postgresql+psycopg://") and "://" in conn_str:
            return f"postgresql+psycopg://{conn_str.split('://', 1)[-1]}"
        return conn_str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回缓存的设置实例。"""
    raw_conn = _require_env("POSTGRES_CONNECTION_STRING")
    normalized_conn = _normalize_conn_string(raw_conn)

    return Settings(
        chat_model=os.getenv("CHAT_MODEL", "qwen-plus-latest"),
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
        dascope_base_url=os.getenv("DASHSCOPE_BASE_URL"),
        embeddings_model=os.getenv("EMBEDDINGS_MODEL", "text-embedding-v4"),
        litellm_base_url=os.getenv("LITELLM_BASE_URL"),
        postgres_connection_string=normalized_conn,
        default_collection=os.getenv("VECTOR_COLLECTION", "pdf_documents"),
        chunk_size=_coerce_int("CHUNK_SIZE", 1000),
        chunk_overlap=_coerce_int("CHUNK_OVERLAP", 200),
        retriever_top_k=_coerce_int("RETRIEVER_TOP_K", 4),
        rerank_enabled=os.getenv("RERANK_ENABLED", "false").lower() == "true",
        rerank_model=os.getenv("RERANK_MODEL", "qwen3-rerank"),
        rerank_top_n=_coerce_int("RERANK_TOP_N", 3),
        redis_url=os.getenv("REDIS_URL"),
        redis_stream_enabled=os.getenv("REDIS_STREAM_ENABLED", "false").lower() == "true",
        stream_ttl_seconds=_coerce_int("STREAM_TTL_SECONDS", 3600),
        stream_max_length=_coerce_int("STREAM_MAX_LENGTH", 1000),
        workflow_timeout_seconds=_coerce_int("WORKFLOW_TIMEOUT_SECONDS", 300),
        # LangSmith 配置
        langsmith_api_key=os.getenv("LANGCHAIN_API_KEY"),
        langsmith_endpoint=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
        langsmith_project=os.getenv("LANGSMITH_PROJECT", "default"),
        # Document processing 配置
        frontend_images_dir=os.getenv("FRONTEND_IMAGES_DIR", "./frontend/public/documents/images"),
        frontend_image_prefix=os.getenv("FRONTEND_IMAGE_PREFIX", "/documents/images"),
        # Project search API 配置
        project_search_api_url=os.getenv("PROJECT_SEARCH_API_URL"),
        project_search_api_username=os.getenv("PROJECT_SEARCH_API_USERNAME"),
        project_search_api_password=os.getenv("PROJECT_SEARCH_API_PASSWORD"),
        project_search_enabled=os.getenv("PROJECT_SEARCH_ENABLED", "false").lower() == "true",
        # Project search database 配置
        project_search_db_url=os.getenv("PROJECT_SEARCH_DB_URL"),
    )


__all__ = ["Settings", "get_settings"]

