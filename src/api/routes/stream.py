"""流式/WebSocket 端点。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from config.settings import get_settings
from infra.redis_pubsub import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter()


async def _send_stream_history(
    websocket: WebSocket, redis: Redis, thread_id: str
) -> str:
    """读取并发送 Stream 历史消息。

    返回最后一条消息的 ID，用于后续的阻塞读取。
    """
    stream_key = f"workflow:execution:{thread_id}"
    last_id = "0-0"

    try:
        messages = await redis.xrange(stream_key)
        for message_id, fields in messages:
            last_id = message_id
            # 构建消息对象，包含 message_id 用于前端续订
            # 添加 is_history 标志，前端可以区分历史消息和新消息
            msg = {
                "message_id": message_id,
                "is_history": True,
                **fields,
            }
            await websocket.send_text(json.dumps(msg, ensure_ascii=False))
    except Exception as e:
        logger.error(f"Failed to read stream history: {e}", exc_info=True)

    return last_id


async def _stream_new_messages(
    websocket: WebSocket, redis: Redis, thread_id: str, last_id: str
) -> None:
    """阻塞读取新消息并发送到 WebSocket。"""
    stream_key = f"workflow:execution:{thread_id}"

    while True:
        try:
            streams = await redis.xread(
                {stream_key: last_id}, block=1000, count=10
            )
            if streams:
                for stream, messages in streams:
                    for message_id, fields in messages:
                        last_id = message_id
                        # 构建消息对象，包含 message_id
                        msg = {
                            "message_id": message_id,
                            **fields,
                        }
                        await websocket.send_text(
                            json.dumps(msg, ensure_ascii=False)
                        )
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"XREAD failed: {e}", exc_info=True)
            await asyncio.sleep(1)


async def _stream_pubsub_fallback(
    websocket: WebSocket, redis: Redis, thread_id: str
) -> None:
    """Pub/Sub 降级方案（当 Stream 不可用时）。"""
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
        pass
    finally:
        await pubsub.close()


@router.websocket("/ws/{thread_id}")
async def websocket_stream(
    websocket: WebSocket, thread_id: str, last_id: Optional[str] = None
):
    """WebSocket 流式接口，支持 Stream 和 Pub/Sub 两种模式。

    ✅ 流程（Stream 模式）：
    1. 接受 WebSocket 连接
    2. 读取历史消息（XRANGE）
    3. 阻塞读取新消息（XREAD）
    4. 支持从 last_id 续订

    ✅ 流程（Pub/Sub 降级）：
    1. 如果 Stream 不可用，使用 Pub/Sub
    2. 订阅频道模式：workflow:{thread_id}:*
    3. 监听消息并转发

    参数：
    - websocket: FastAPI WebSocket 连接对象
    - thread_id: 会话线程 ID
    - last_id: 可选，从该消息 ID 之后开始读取（用于续订）

    消息格式：
    - 包含 message_id 字段（用于前端保存和续订）
    - 包含 node_name、message_type、status、timestamp、data 等字段

    注意：
    - 前端可以通过 localStorage 保存 last_id
    - 重连时通过 ?last_id={id} 参数传递
    - 如果 Stream 不可用，自动降级到 Pub/Sub
    """
    await websocket.accept()
    redis: Redis = get_redis_client()
    settings = get_settings()

    try:
        if settings.redis_stream_enabled:
            # Stream 模式
            if last_id:
                # 从指定位置续订
                await _stream_new_messages(websocket, redis, thread_id, last_id)
            else:
                # 先读历史，再读新消息
                last_id = await _send_stream_history(websocket, redis, thread_id)
                await _stream_new_messages(websocket, redis, thread_id, last_id)
        else:
            # Pub/Sub 降级模式
            await _stream_pubsub_fallback(websocket, redis, thread_id)
    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected: {thread_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await websocket.close(code=1011, reason="Internal server error")


__all__ = ["router"]


