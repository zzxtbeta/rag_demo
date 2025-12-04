"""API request/response schemas."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """消息载荷，LangGraph 工作流接受的最小消息格式。

    字段：

    - role: 消息角色（"user"、"assistant"、"system"），默认为 "user"

    - content: 消息内容文本
    """

    role: Literal["user", "assistant", "system"] = "user"
    content: str


class ChatRequest(BaseModel):
    """聊天请求载荷。

    字段：

    - thread_id: 会话线程标识，用于状态持久化和上下文管理

    - user_id: 用户标识（可选），用于记忆命名空间隔离

    - message: 用户查询内容
    """

    thread_id: str = Field(..., description="Conversation thread identifier")
    user_id: Optional[str] = Field(
        None, description="Optional user identifier for memory namespacing"
    )
    message: str = Field(..., description="User query content")


class ChatResponse(BaseModel):
    """同步聊天接口响应。

    字段：

    - thread_id: 会话线程标识，与请求中的 thread_id 一致

    - user_id: 用户标识（可选），与请求中的 user_id 一致

    - answer: 工作流执行后的最终答案
    """

    thread_id: str
    user_id: Optional[str]
    answer: str


class StreamStartResponse(BaseModel):
    """流式聊天接口响应，表示工作流已启动。

    ✅ 使用方式：

    1. 前端收到此响应后，使用 thread_id 连接 WebSocket

    2. WebSocket 地址：ws://host/ws/{thread_id}

    3. 订阅 Redis 频道模式：ws_channel（如 workflow:{thread_id}:*）

    4. 接收实时节点更新事件

    

    字段：

    - thread_id: 会话线程标识，用于后续状态查询和 WebSocket 连接

    - user_id: 用户标识（可选）

    - ws_channel: Redis 频道模式，格式为 workflow:{thread_id}:*

    - status: 固定为 "streaming"，表示流式执行已启动
    """

    thread_id: str
    user_id: Optional[str]
    ws_channel: str = Field(..., description="Redis channel pattern for WebSocket subscription")
    status: str = "streaming"


__all__ = ["ChatRequest", "ChatResponse", "StreamStartResponse", "Message"]

