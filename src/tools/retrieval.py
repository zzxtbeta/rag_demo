"""使用 LangGraph Agentic RAG 模式定义代理的检索工具。"""

from typing import Iterable, Optional

from langchain.tools import tool
from langchain_core.documents import Document

from agent.vectorstore import get_vector_store
from config.settings import get_settings


def _serialize_documents(documents: Iterable, include_scores: bool = False) -> str:
    """将文档序列化为字符串供 LLM 消耗。
    
    参数：
        documents: 文档迭代器
        include_scores: 是否在输出中包含相关性分数
    """
    parts: list[str] = []
    for doc in documents:
        source = doc.metadata if doc.metadata else {}
        content = f"Source: {source}\nContent: {doc.page_content}"
        
        # 如果文档包含相关性分数，添加到输出
        if include_scores and "relevance_score" in doc.metadata:
            score = doc.metadata["relevance_score"]
            content += f"\nRelevance Score: {score:.4f}"
        
        parts.append(content)
    return "\n\n".join(parts)


def _rerank_documents(
    documents: list[Document], query: str, settings
) -> Optional[list[Document]]:
    """使用 DashScope Rerank 重排文档。
    
    参数：
        documents: 待重排的文档列表
        query: 查询文本
        settings: 配置对象
        
    返回：
        重排后的文档列表，如果 rerank 禁用则返回 None
    """
    if not settings.rerank_enabled or not documents:
        return None
    
    try:
        from langchain_community.document_compressors.dashscope_rerank import (
            DashScopeRerank,
        )
        
        reranker = DashScopeRerank(
            model=settings.rerank_model,
            dashscope_api_key=settings.dashscope_api_key,
            top_n=settings.rerank_top_n,
        )
        
        reranked_docs = reranker.compress_documents(documents, query)
        return list(reranked_docs)
    except ImportError:
        raise ImportError(
            "Could not import DashScopeRerank. "
            "Please install it with `pip install dashscope`."
        )
    except Exception as e:
        raise RuntimeError(f"Rerank failed: {str(e)}")


@tool(response_format="content_and_artifact")
def retrieve_context(query: str):
    """搜索 PDF/向量知识库以获取公司/项目/文档信息。

    当用户询问任何公司、项目、业务范围、融资、新闻、
    产品、合作方、政策/标书/招标文件等时，需要基于知识库给出证据和摘要时使用。

    返回：
        content: str - 人类可读的来源 + LLM 的内容（包含相关性分数）
        artifact: list - 用于引用的原始 Document 对象
    """
    settings = get_settings()
    vector_store = get_vector_store()
    
    # 第一步：向量检索
    retrieved_docs = vector_store.similarity_search(query, k=settings.retriever_top_k)
    
    # 第二步：可选的 Rerank 重排
    if settings.rerank_enabled and retrieved_docs:
        reranked_docs = _rerank_documents(retrieved_docs, query, settings)
        if reranked_docs:
            retrieved_docs = reranked_docs
    
    # 返回 content_and_artifact 格式（元组）
    return _serialize_documents(retrieved_docs, include_scores=True), retrieved_docs

__all__ = ["retrieve_context"]