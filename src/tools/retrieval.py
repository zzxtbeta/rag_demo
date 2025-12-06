"""Define the agent's retrieval tool using LangGraph Agentic RAG pattern."""

from typing import Iterable

from langchain.tools import tool

from agent.vectorstore import get_vector_store
from config.settings import get_settings


def _serialize_documents(documents: Iterable) -> str:
    """Serialize documents into a string for LLM consumption."""
    parts: list[str] = []
    for doc in documents:
        source = doc.metadata if doc.metadata else {}
        parts.append(f"Source: {source}\nContent: {doc.page_content}")
    return "\n\n".join(parts)


@tool(response_format="content_and_artifact")
def retrieve_context(query: str):
    """Search the PDF/vector knowledge base for company/project/document info.

    Use this first when users ask about any company,项目、业务范围、融资、新闻、
    产品、合作方、政策/标书/招标文件等，需要基于知识库给出证据和摘要时调用。

    Returns:
        serialized_text: str - human-readable sources + content for the LLM
        raw_documents: list - original Document objects for citation
    """
    settings = get_settings()
    vector_store = get_vector_store()
    retrieved_docs = vector_store.similarity_search(query, k=settings.retriever_top_k)
    return _serialize_documents(retrieved_docs), retrieved_docs


__all__ = ["retrieve_context"]