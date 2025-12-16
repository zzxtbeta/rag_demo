"""RAG 系统的向量存储工具。

当前运行路径：
- `tools.retrieval.retrieve_context` 使用 `get_vector_store()` 做相似度检索
- `utils.mineru_processor.MineruProcessor` 可选将处理后的 chunks 写入同一向量库
"""

from functools import lru_cache
from typing import Optional
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_postgres import PGVector

from config.settings import get_settings


def get_embeddings() -> DashScopeEmbeddings:
    """初始化 DashScope Qwen 嵌入模型。"""
    settings = get_settings()
    return DashScopeEmbeddings(
        model=settings.embeddings_model,
        dashscope_api_key=settings.dashscope_api_key,
    )


def initialize_vector_store(
    collection_name: str = "pdf_documents",
    connection_string: Optional[str] = None,
) -> PGVector:
    """使用嵌入初始化 PGVector 存储。
    
    参数：
        collection_name: 向量存储中集合的名称。
        connection_string: PostgreSQL 连接字符串。如果为 None，从环境读取。
        
    返回：
        PGVector: 初始化的向量存储。
    """
    settings = get_settings()
    if connection_string is None:
        connection_string = settings.psycopg_connection
    if collection_name == "pdf_documents":
        collection_name = settings.default_collection
    
    embeddings = get_embeddings()
    
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection_string,
        use_jsonb=True,
    )
    
    return vector_store


@lru_cache(maxsize=None)
def get_vector_store(
    collection_name: str = "pdf_documents",
) -> PGVector:
    """返回给定集合的缓存 PGVector 实例。
    
    参数：
        collection_name: 向量存储中集合的名称。
        
    返回：
        PGVector: 缓存的向量存储实例。
    """
    settings = get_settings()
    if collection_name == "pdf_documents":
        collection_name = settings.default_collection
    return initialize_vector_store(collection_name=collection_name)


__all__ = [
    "get_embeddings",
    "initialize_vector_store",
    "get_vector_store",
]
