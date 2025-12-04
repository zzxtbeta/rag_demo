"""Streaming/WebSocket endpoints."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from infra.redis_pubsub import get_redis_client


router = APIRouter()


@router.websocket("/ws/{thread_id}")
async def websocket_stream(websocket: WebSocket, thread_id: str):
    """WebSocket 流式接口，将 Redis Pub/Sub 消息代理到前端。

    ✅ 流程：
    1. 接受 WebSocket 连接
    2. 订阅 Redis 频道模式：workflow:{thread_id}:*
    3. 监听 Redis 消息，转发到 WebSocket 客户端
    4. 客户端断开时自动清理订阅

    参数：
    - websocket: FastAPI WebSocket 连接对象
    - thread_id: 会话线程 ID，从 URL 路径参数获取

    订阅频道：
    - workflow:{thread_id}:* （匹配所有该线程的事件）

    消息格式：
    - 接收：Redis Pub/Sub 消息（JSON 字符串）
    - 转发：直接作为文本消息发送到 WebSocket

    注意：
    - 前端需要先调用 /chat/stream 启动工作流，再连接此 WebSocket
    - 支持多个客户端同时订阅同一个 thread_id
    - 客户端断开时会自动取消 Redis 订阅
    - 消息格式为 StreamMessage 的 JSON 序列化结果
    """
    await websocket.accept()
    redis: Redis = get_redis_client()
    pubsub = redis.pubsub()
    pattern = f"workflow:{thread_id}:*"
    await pubsub.psubscribe(pattern)

    try:
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                await websocket.send_text(data)
    except WebSocketDisconnect:
        # Client disconnected
        pass
    finally:
        await pubsub.close()


__all__ = ["router"]


