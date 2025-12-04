"""API request/response schemas."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Minimal message payload accepted by the graph."""

    role: Literal["user", "assistant", "system"] = "user"
    content: str


class ChatRequest(BaseModel):
    """Input payload for /chat endpoint."""

    thread_id: str = Field(..., description="Conversation thread identifier")
    user_id: Optional[str] = Field(
        None, description="Optional user identifier for memory namespacing"
    )
    message: str = Field(..., description="User query content")


class ChatResponse(BaseModel):
    """Normalized response for /chat endpoint."""

    thread_id: str
    user_id: Optional[str]
    answer: str


__all__ = ["ChatRequest", "ChatResponse", "Message"]

