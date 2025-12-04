"""Chat-related API endpoints."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from api.dependencies import get_graph, get_redis_publisher
from api.schemas import ChatRequest, ChatResponse, StreamStartResponse
from api.utils import extract_content
from config.settings import get_settings
from infra.redis_pubsub import RedisPublisher, StreamMessage

logger = logging.getLogger(__name__)

try:
    from langchain_core.messages import BaseMessage, message_to_dict  # type: ignore
except Exception:  # pragma: no cover - defensive
    BaseMessage = None  # type: ignore[assignment]
    message_to_dict = None  # type: ignore[assignment]


router = APIRouter()


def _normalize_update(obj: Any) -> Any:
    """递归转换 LangChain 消息对象为 JSON 可序列化格式。

    ✅ 处理流程：
    1. 如果是 BaseMessage（如 AIMessage），使用 message_to_dict 转换
    2. 如果是字典/列表/元组，递归处理所有嵌套元素
    3. 其他类型直接返回

    参数：
    - obj: 待转换的对象（可能是 BaseMessage、dict、list、tuple 等）

    返回：
    - 转换后的 JSON 友好格式对象

    注意：
    - 此函数用于在发布到 Redis 前预处理 LangGraph 的 state delta
    - 确保 AIMessage 等 LangChain 对象能被正确序列化
    """
    if BaseMessage is not None and isinstance(obj, BaseMessage):
        if message_to_dict is not None:
            return message_to_dict(obj)
        return {"type": obj.__class__.__name__, "content": getattr(obj, "content", "")}
    if isinstance(obj, dict):
        return {k: _normalize_update(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_update(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_normalize_update(v) for v in obj)
    return obj


@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, graph=Depends(get_graph)):
    """同步聊天接口，执行完整工作流后返回最终答案。

    ✅ 流程：
    1. 构建 LangGraph 配置（thread_id、user_id）
    2. 调用 graph.ainvoke 同步执行整个工作流
    3. 从结果中提取最后一条消息的 content
    4. 返回包含 thread_id、user_id、answer 的响应

    参数：
    - req: 聊天请求，包含 thread_id、user_id、message
    - graph: LangGraph 工作流实例（通过依赖注入）

    返回：
    - ChatResponse: 包含 thread_id、user_id、最终答案

    注意：
    - 此接口会等待整个工作流完成，适合不需要实时更新的场景
    - 如需实时节点级更新，请使用 /chat/stream 接口
    """
    config = {"configurable": {"thread_id": req.thread_id}}
    if req.user_id:
        config["configurable"]["user_id"] = req.user_id

    payload = {"messages": [{"role": "user", "content": req.message}]}
    result = await graph.ainvoke(payload, config)

    messages = result.get("messages", [])
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Model returned empty response",
        )

    answer = extract_content(messages[-1])
    return ChatResponse(thread_id=req.thread_id, user_id=req.user_id, answer=answer)


async def _stream_workflow_to_redis(
    *,
    graph,
    payload: dict[str, Any],
    config: dict[str, Any],
    thread_id: str,
    publisher: RedisPublisher,
) -> None:
    """后台执行工作流并将节点更新发布到 Redis。

    ✅ 流程：
    1. 发布工作流开始事件（workflow:start）
    2. 使用 stream_mode="updates" 流式执行 graph.astream
    3. 对每个节点更新：
       - 发布节点开始事件（如果节点切换）
       - 规范化节点输出数据（处理 AIMessage 等）
       - 发布节点完成事件（包含执行时间）
    4. 工作流完成后发布 workflow:complete（包含所有节点时间统计）
    5. 发生错误时发布 workflow:error（区分超时、取消、执行错误）

    参数：
    - graph: LangGraph 工作流实例
    - payload: 输入数据，包含 messages 数组
    - config: LangGraph 配置，包含 thread_id、user_id
    - thread_id: 会话线程 ID，用于 Redis 频道命名
    - publisher: Redis 发布器实例

    事件发布：
    - workflow:{thread_id}:workflow:start - 工作流开始
    - workflow:{thread_id}:{node_name}:start - 节点开始（推断）
    - workflow:{thread_id}:{node_name}:output - 节点完成
    - workflow:{thread_id}:workflow:complete - 工作流完成
    - workflow:{thread_id}:workflow:error - 工作流错误

    注意：
    - 节点开始事件是通过追踪 last_node 推断的，不是真正的开始时间
    - 执行时间记录的是节点间时间间隔，不是精确的节点执行时间
    - 超时时间由 WORKFLOW_TIMEOUT_SECONDS 配置（默认 300 秒）
    - CancelledError 不会发布错误事件（用户主动取消）
    """
    start_time = time.perf_counter()
    node_times: dict[str, float] = {}
    last_node: str | None = None
    node_start_time = start_time

    settings = get_settings()
    timeout_seconds = settings.workflow_timeout_seconds

    await publisher.publish_message(
        StreamMessage(
            thread_id=thread_id,
            node_name="workflow",
            message_type="start",
            status="started",
            timestamp=time.time(),
            data={"input": payload},
        )
    )

    async def _process_stream():
        async for chunk in graph.astream(
            payload,
            config,
            stream_mode="updates",
        ):
            for node_name, update in chunk.items():
                nonlocal last_node, node_start_time
                if node_name != last_node and last_node is not None:
                    elapsed_ms = (time.perf_counter() - node_start_time) * 1000
                    node_times[last_node] = elapsed_ms

                if node_name != last_node:
                    await publisher.publish_node_output(
                        thread_id=thread_id,
                        node_name=node_name,
                        data={"status": "starting"},
                        status="starting",
                        message_type="start",
                    )
                    node_start_time = time.perf_counter()

                normalized = _normalize_update(update)
                elapsed_ms = (time.perf_counter() - node_start_time) * 1000
                node_times[node_name] = elapsed_ms

                await publisher.publish_node_output(
                    thread_id=thread_id,
                    node_name=node_name,
                    data=normalized,
                    status="completed",
                    message_type="output",
                    execution_time_ms=elapsed_ms,
                )
                last_node = node_name
                node_start_time = time.perf_counter()

    try:
        await asyncio.wait_for(_process_stream(), timeout=timeout_seconds)

        total_ms = (time.perf_counter() - start_time) * 1000
        await publisher.publish_workflow_complete(
            thread_id=thread_id,
            data={"node_times": node_times, "total_ms": total_ms},
            execution_time_ms=total_ms,
        )
    except asyncio.CancelledError:
        logger.info(f"Workflow cancelled: {thread_id}")
    except asyncio.TimeoutError:
        logger.warning(f"Workflow timeout after {timeout_seconds}s: {thread_id}")
        await publisher.publish_workflow_error(
            thread_id=thread_id,
            error=f"Workflow execution exceeded {timeout_seconds}s timeout",
            data={"error_type": "timeout", "timeout_seconds": timeout_seconds},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Workflow error: {exc}")
        await publisher.publish_workflow_error(
            thread_id=thread_id,
            error=str(exc),
            data={"error_type": "execution_error"},
        )


@router.post("/stream", response_model=StreamStartResponse)
async def chat_stream_endpoint(
    req: ChatRequest,
    background_tasks: BackgroundTasks,
    graph=Depends(get_graph),
    publisher: RedisPublisher = Depends(get_redis_publisher),
):
    """启动流式聊天工作流并发布节点更新到 Redis。

    ✅ 流程：
    1. 立即返回 thread_id 和 WebSocket 订阅频道
    2. 后台启动 graph.astream，发送节点事件到 Redis
    3. 前端通过 WebSocket 订阅 Redis 频道接收实时更新

    返回的响应包含：
    - thread_id: 工作流会话标识，用于后续状态查询和恢复
    - user_id: 用户标识（可选），用于记忆命名空间
    - ws_channel: Redis 频道模式，格式为 workflow:{thread_id}:*
    - status: 固定为 "streaming"，表示流式执行已启动

    参数：
    - req: 聊天请求，包含 thread_id、user_id、message
    - background_tasks: FastAPI 后台任务管理器
    - graph: LangGraph 工作流实例（通过依赖注入）
    - publisher: Redis 发布器实例（通过依赖注入）

    返回：
    - StreamStartResponse: 包含 thread_id、ws_channel、status

    前端使用方式：
    1. 调用此接口获取 thread_id 和 ws_channel
    2. 连接 WebSocket: ws://host/ws/{thread_id}
    3. 订阅 Redis 频道: workflow:{thread_id}:*
    4. 接收实时节点更新事件

    注意：
    - 此接口立即返回，不等待工作流完成
    - 实际工作流在后台异步执行，通过 Redis Pub/Sub 推送更新
    - 前端需要主动订阅 WebSocket 才能接收更新
    - 同一个 thread_id 可以多次调用，共享对话上下文
    """
    config: dict[str, Any] = {"configurable": {"thread_id": req.thread_id}}
    if req.user_id:
        config["configurable"]["user_id"] = req.user_id

    payload: dict[str, Any] = {
        "messages": [{"role": "user", "content": req.message}]
    }

    background_tasks.add_task(
        _stream_workflow_to_redis,
        graph=graph,
        payload=payload,
        config=config,
        thread_id=req.thread_id,
        publisher=publisher,
    )

    return StreamStartResponse(
        thread_id=req.thread_id,
        user_id=req.user_id,
        ws_channel=f"workflow:{req.thread_id}:*",
        status="streaming",
    )


__all__ = ["router"]

