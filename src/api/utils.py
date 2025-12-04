"""Helper utilities for API layer."""

from __future__ import annotations

from langchain_core.messages import BaseMessage


def extract_content(message: BaseMessage | dict | str) -> str:
    """Normalize LangChain message or dict to plain string."""
    if isinstance(message, BaseMessage):
        return getattr(message, "content", "")
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(message)


__all__ = ["extract_content"]

