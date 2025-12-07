"""API request/response schemas."""

from __future__ import annotations

from typing import Any, Literal, Optional

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

    - chat_model: 聊天使用的模型名称（可选），如未指定则使用默认配置
    """

    thread_id: str = Field(..., description="Conversation thread identifier")
    user_id: Optional[str] = Field(
        None, description="Optional user identifier for memory namespacing"
    )
    message: str = Field(..., description="User query content")
    chat_model: Optional[str] = Field(
        None, description="Optional chat model name (e.g., 'qwen-plus-latest', 'qwen-max-latest', 'qwen-flash')"
    )


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


class HistoryMessage(BaseModel):
    """历史消息项。

    字段：
    - id: 消息唯一标识
    - role: 消息角色（"user"、"assistant"、"system"、"tool"）
    - content: 消息内容文本
    - timestamp: 消息时间戳（可选）
    - type: 原始消息类型（"human", "ai", "tool", "system"）
    - name: 消息名称（如工具名称）
    - tool_calls: 工具调用列表（仅 AI 消息）
    - tool_call_id: 工具调用 ID（仅 Tool 消息）
    """

    id: str
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    timestamp: Optional[float] = None
    type: str
    name: Optional[str] = None
    tool_calls: list[dict] = []
    tool_call_id: Optional[str] = None
    artifact: Optional[Any] = None


class ThreadHistory(BaseModel):
    """线程的完整历史记录。

    字段：
    - thread_id: 会话线程标识
    - messages: 历史消息列表
    - total_messages: 消息总数
    """

    thread_id: str
    messages: list[HistoryMessage]
    total_messages: int


class TraceRun(BaseModel):
    """LangSmith Trace Run 数据。

    字段：
    - run_id: Run 唯一标识
    - name: Run 名称（如节点名称、LLM 调用名称）
    - run_type: Run 类型（"llm", "chain", "tool", "retriever" 等）
    - start_time: 开始时间（ISO 格式字符串）
    - end_time: 结束时间（ISO 格式字符串，可选）
    - latency_ms: 执行延迟（毫秒）
    - total_tokens: Token 总数（可选）
    - prompt_tokens: Prompt Token 数（可选）
    - completion_tokens: Completion Token 数（可选）
    - error: 错误信息（可选）
    - inputs: 输入数据（可选）
    - outputs: 输出数据（可选）
    - parent_run_id: 父 Run ID（可选）
    """

    run_id: str
    name: str
    run_type: str
    start_time: str
    end_time: Optional[str] = None
    latency_ms: Optional[float] = None
    total_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    error: Optional[str] = None
    inputs: Optional[dict] = None
    outputs: Optional[dict] = None
    parent_run_id: Optional[str] = None
    children: Optional[list["TraceRun"]] = None


class ThreadHistoryWithTrace(BaseModel):
    """线程的完整历史记录（包含 LangSmith Trace）。

    字段：
    - thread_id: 会话线程标识
    - messages: 历史消息列表
    - total_messages: 消息总数
    - trace_runs: LangSmith Trace Runs（按时间正序排列）
    - trace_tree: Trace 执行树（只包含根节点）
    - root_run_id: 顶层 Run ID（用于构造 LangSmith trace 链接）
    - total_latency_ms: 总执行时间（毫秒）
    - total_tokens: 总 Token 消耗
    """

    thread_id: str
    messages: list[HistoryMessage]
    total_messages: int
    trace_runs: list[TraceRun] = []
    trace_tree: list[TraceRun] = []
    root_run_id: Optional[str] = None
    total_latency_ms: Optional[float] = None
    total_tokens: Optional[int] = None


__all__ = [
    "ChatRequest",
    "ChatResponse",
    "StreamStartResponse",
    "Message",
    "HistoryMessage",
    "ThreadHistory",
    "TraceRun",
    "ThreadHistoryWithTrace",
]

