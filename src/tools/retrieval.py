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
    """Retrieve information to help answer a query."""
    settings = get_settings()
    vector_store = get_vector_store()
    retrieved_docs = vector_store.similarity_search(query, k=settings.retriever_top_k)
    return _serialize_documents(retrieved_docs), retrieved_docs


__all__ = ["retrieve_context"]