"""Async Redis Pub/Sub utilities."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict

from redis.asyncio import Redis, from_url

from config.settings import get_settings

logger = logging.getLogger(__name__)

try:
    from langchain_core.messages import BaseMessage, message_to_dict
except Exception:
    BaseMessage = None
    message_to_dict = None


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    """获取缓存的异步 Redis 客户端实例。

    ✅ 流程：
    1. 从配置中读取 REDIS_URL
    2. 如果未配置，抛出 RuntimeError
    3. 创建并返回异步 Redis 客户端（单例模式）

    返回：
    - Redis: 异步 Redis 客户端实例

    注意：
    - 使用 @lru_cache 确保全局只有一个 Redis 客户端实例
    - 客户端配置为 UTF-8 编码，自动解码响应
    - 如果 REDIS_URL 未配置，会在首次调用时抛出异常
    """
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL is not configured.")
    return from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


@dataclass
class StreamMessage:
    """流式消息数据结构，用于 Redis Pub/Sub 通信。

    字段说明：
    - thread_id: 会话线程 ID，用于频道命名和消息路由
    - node_name: 节点名称（如 "query_or_respond"、"tools"、"workflow"）
    - message_type: 消息类型（"start"、"output"、"complete"、"error"）
    - status: 状态（"started"、"starting"、"running"、"completed"、"failed"）
    - timestamp: Unix 时间戳（秒）
    - data: 消息数据（可能是 state delta、错误信息等）
    - execution_time_ms: 执行时间（毫秒），节点完成时提供
    """

    thread_id: str
    node_name: str
    message_type: str
    status: str
    timestamp: float
    data: Any
    execution_time_ms: float | None = None

    def to_json(self) -> str:
        """将 StreamMessage 序列化为 JSON 字符串。

        ✅ 处理流程：
        1. 使用 __dict__.copy() 获取消息字典
        2. 通过 json.dumps 的 default 参数处理非 JSON 类型：
           - BaseMessage（如 AIMessage）→ 使用 message_to_dict 转换
           - 其他对象 → 转换为字符串
        3. 如果序列化失败，返回错误回退消息

        返回：
        - str: JSON 格式的消息字符串

        注意：
        - 自动处理 LangChain 消息对象的序列化问题
        - 序列化失败时会返回包含错误信息的回退消息
        - 确保所有字段都能被正确序列化
        """

        def _default(obj: Any):
            """Convert non-JSON-serializable objects."""
            if BaseMessage is not None and isinstance(obj, BaseMessage):
                if message_to_dict is not None:
                    return message_to_dict(obj)
                return {
                    "type": obj.__class__.__name__,
                    "content": getattr(obj, "content", ""),
                }
            return str(obj)

        try:
            msg_dict = self.__dict__.copy()
            return json.dumps(msg_dict, ensure_ascii=False, default=_default)
        except Exception as e:
            logger.error(f"Serialization error: {e}", exc_info=True)
            fallback = {
                "thread_id": self.thread_id,
                "node_name": self.node_name,
                "message_type": self.message_type,
                "status": "error",
                "error": f"Serialization failed: {str(e)}",
                "timestamp": time.time(),
            }
            return json.dumps(fallback, ensure_ascii=False)


class RedisPublisher:
    """工作流流式事件的高层发布器。

    职责：
    - 封装 Redis Pub/Sub 发布逻辑
    - 提供便捷的节点事件发布方法
    - 统一频道命名规范：workflow:{thread_id}:{node_name}:{message_type}
    """

    def __init__(self, client: Redis | None = None) -> None:
        """初始化发布器。

        参数：
        - client: Redis 客户端实例，如果为 None 则使用全局单例
        """
        self._client: Redis = client or get_redis_client()

    @staticmethod
    def _channel(thread_id: str, node_name: str, message_type: str) -> str:
        """生成 Redis 频道名称。

        格式：workflow:{thread_id}:{node_name}:{message_type}

        示例：workflow:thread_123:query_or_respond:output
        """
        return f"workflow:{thread_id}:{node_name}:{message_type}"

    async def publish_message(self, message: StreamMessage) -> None:
        """发布消息到 Redis Pub/Sub。

        ✅ 流程：
        1. 根据消息的 thread_id、node_name、message_type 生成频道名
        2. 将消息序列化为 JSON
        3. 发布到 Redis
        4. 记录日志（成功或失败）

        参数：
        - message: StreamMessage 实例

        注意：
        - 发布失败会记录错误日志，但不会抛出异常
        - 确保消息已正确序列化后再调用此方法
        """
        channel = self._channel(
            message.thread_id, message.node_name, message.message_type
        )
        try:
            await self._client.publish(channel, message.to_json())
            logger.debug(f"Published to {channel}")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}", exc_info=True)

    async def publish_node_output(
        self,
        thread_id: str,
        node_name: str,
        data: Any,
        *,
        status: str = "running",
        message_type: str = "output",
        execution_time_ms: float | None = None,
    ) -> None:
        """发布节点输出事件。

        ✅ 流程：
        1. 构建 StreamMessage 对象
        2. 设置时间戳和执行时间
        3. 调用 publish_message 发布到 Redis

        参数：
        - thread_id: 会话线程 ID
        - node_name: 节点名称（如 "query_or_respond"、"tools"）
        - data: 节点输出数据（通常是 state delta）
        - status: 状态（"starting"、"running"、"completed"）
        - message_type: 消息类型（"start"、"output"）
        - execution_time_ms: 执行时间（毫秒），节点完成时提供

        发布频道：
        - workflow:{thread_id}:{node_name}:{message_type}
        """
        msg = StreamMessage(
            thread_id=thread_id,
            node_name=node_name,
            message_type=message_type,
            status=status,
            timestamp=time.time(),
            data=data,
            execution_time_ms=execution_time_ms,
        )
        await self.publish_message(msg)

    async def publish_workflow_complete(
        self,
        thread_id: str,
        *,
        data: Dict[str, Any] | None = None,
        execution_time_ms: float | None = None,
    ) -> None:
        """发布工作流完成事件。

        ✅ 流程：
        1. 构建 StreamMessage，node_name 固定为 "workflow"
        2. message_type 为 "complete"，status 为 "completed"
        3. 包含总执行时间和节点时间统计（在 data 中）
        4. 发布到 Redis

        参数：
        - thread_id: 会话线程 ID
        - data: 额外数据（通常包含 node_times、total_ms 等统计信息）
        - execution_time_ms: 总执行时间（毫秒）

        发布频道：
        - workflow:{thread_id}:workflow:complete

        注意：
        - 前端收到此事件后可以停止流式指示器
        - data 中通常包含各节点的执行时间统计
        """
        msg = StreamMessage(
            thread_id=thread_id,
            node_name="workflow",
            message_type="complete",
            status="completed",
            timestamp=time.time(),
            data=data or {},
            execution_time_ms=execution_time_ms,
        )
        await self.publish_message(msg)

    async def publish_workflow_error(
        self,
        thread_id: str,
        error: str,
        *,
        data: Dict[str, Any] | None = None,
    ) -> None:
        """发布工作流错误事件。

        ✅ 流程：
        1. 构建 StreamMessage，node_name 固定为 "workflow"
        2. message_type 为 "error"，status 为 "failed"
        3. 错误信息放在 data.error 中
        4. 可以包含额外的错误元数据（如 error_type）
        5. 发布到 Redis

        参数：
        - thread_id: 会话线程 ID
        - error: 错误消息字符串
        - data: 额外数据（通常包含 error_type、timeout_seconds 等）

        发布频道：
        - workflow:{thread_id}:workflow:error

        注意：
        - 前端收到此事件后应显示错误提示
        - data.error_type 可用于区分不同类型的错误（timeout、execution_error）
        """
        msg = StreamMessage(
            thread_id=thread_id,
            node_name="workflow",
            message_type="error",
            status="failed",
            timestamp=time.time(),
            data={"error": error, **(data or {})},
            execution_time_ms=None,
        )
        await self.publish_message(msg)


__all__ = ["get_redis_client", "RedisPublisher", "StreamMessage"]


