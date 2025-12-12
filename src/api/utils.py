"""API 层的辅助工具。"""

from __future__ import annotations

from langchain_core.messages import BaseMessage


def extract_content(message: BaseMessage | dict | str) -> str:
    """将 LangChain 消息或字典正规化为纯文本字符串。"""
    if isinstance(message, BaseMessage):
        return getattr(message, "content", "")
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(message)


__all__ = ["extract_content"]

