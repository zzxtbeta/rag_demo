"""定义共享值。"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from typing_extensions import Annotated


@dataclass(kw_only=True)
class State:
    """主图状态。"""

    messages: Annotated[list[AnyMessage], add_messages]
    """对话中的消息。"""
    
    retrieved_documents: list[Document] | None = None
    """从向量存储中检索的用于 RAG 的文档。"""


__all__ = [
    "State",
]
