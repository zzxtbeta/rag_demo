"""Unit tests for Redis Stream functionality."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from infra.redis_pubsub import RedisPublisher, StreamMessage


class TestRedisPublisherStream:
    """测试 RedisPublisher 的 Stream 发布功能。"""

    @pytest.mark.asyncio
    async def test_stream_key_generation(self):
        """测试 Stream key 生成。"""
        key = RedisPublisher._stream_key("thread_123")
        assert key == "workflow:execution:thread_123"

    @pytest.mark.asyncio
    async def test_publish_to_stream(self):
        """测试发布消息到 Stream。"""
        mock_redis = AsyncMock()
        mock_redis.xadd.return_value = "1705740000000-0"
        mock_redis.xtrim = AsyncMock()
        mock_redis.expire = AsyncMock()

        with patch("infra.redis_pubsub.get_settings") as mock_settings:
            mock_settings.return_value.redis_stream_enabled = True
            mock_settings.return_value.stream_ttl_seconds = 3600
            mock_settings.return_value.stream_max_length = 1000

            publisher = RedisPublisher(client=mock_redis)

            msg = StreamMessage(
                thread_id="thread_123",
                node_name="query_or_respond",
                message_type="output",
                status="completed",
                timestamp=1705740000.0,
                data={"key": "value"},
                execution_time_ms=100.5,
            )

            message_id = await publisher._publish_to_stream(msg)

            # 验证 XADD 被调用
            assert mock_redis.xadd.called
            assert message_id == "1705740000000-0"

            # 验证 XTRIM 被调用
            assert mock_redis.xtrim.called
            call_args = mock_redis.xtrim.call_args
            assert call_args[0][0] == "workflow:execution:thread_123"
            assert call_args[1]["maxlen"] == 1000

            # 验证 EXPIRE 被调用
            assert mock_redis.expire.called
            call_args = mock_redis.expire.call_args
            assert call_args[0][0] == "workflow:execution:thread_123"
            assert call_args[0][1] == 3600

    @pytest.mark.asyncio
    async def test_publish_to_stream_with_execution_time(self):
        """测试发布消息到 Stream 时包含执行时间。"""
        mock_redis = AsyncMock()
        mock_redis.xadd.return_value = "1705740000000-0"
        mock_redis.xtrim = AsyncMock()
        mock_redis.expire = AsyncMock()

        with patch("infra.redis_pubsub.get_settings") as mock_settings:
            mock_settings.return_value.redis_stream_enabled = True
            mock_settings.return_value.stream_ttl_seconds = 3600
            mock_settings.return_value.stream_max_length = 1000

            publisher = RedisPublisher(client=mock_redis)

            msg = StreamMessage(
                thread_id="thread_123",
                node_name="tools",
                message_type="output",
                status="completed",
                timestamp=1705740000.0,
                data={"result": "success"},
                execution_time_ms=250.5,
            )

            await publisher._publish_to_stream(msg)

            # 验证 XADD 的字段包含 execution_time_ms
            call_args = mock_redis.xadd.call_args
            fields = call_args[0][1]
            assert "execution_time_ms" in fields
            assert fields["execution_time_ms"] == "250.5"

    @pytest.mark.asyncio
    async def test_publish_message_with_stream_enabled(self):
        """测试 publish_message 在 Stream 启用时同时发布到 Stream 和 Pub/Sub。"""
        mock_redis = AsyncMock()
        mock_redis.xadd.return_value = "1705740000000-0"
        mock_redis.xtrim = AsyncMock()
        mock_redis.expire = AsyncMock()
        mock_redis.publish = AsyncMock()

        with patch("infra.redis_pubsub.get_settings") as mock_settings:
            mock_settings.return_value.redis_stream_enabled = True
            mock_settings.return_value.stream_ttl_seconds = 3600
            mock_settings.return_value.stream_max_length = 1000

            publisher = RedisPublisher(client=mock_redis)

            msg = StreamMessage(
                thread_id="thread_123",
                node_name="query_or_respond",
                message_type="token",
                status="streaming",
                timestamp=1705740000.0,
                data={"token": "你好"},
            )

            await publisher.publish_message(msg)

            # 验证 Stream 发布
            assert mock_redis.xadd.called
            assert mock_redis.xtrim.called
            assert mock_redis.expire.called

            # 验证 Pub/Sub 发布
            assert mock_redis.publish.called
            call_args = mock_redis.publish.call_args
            assert "workflow:thread_123:query_or_respond:token" in call_args[0]

    @pytest.mark.asyncio
    async def test_publish_message_with_stream_disabled(self):
        """测试 publish_message 在 Stream 禁用时只发布到 Pub/Sub。"""
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock()

        with patch("infra.redis_pubsub.get_settings") as mock_settings:
            mock_settings.return_value.redis_stream_enabled = False
            mock_settings.return_value.stream_ttl_seconds = 3600
            mock_settings.return_value.stream_max_length = 1000

            publisher = RedisPublisher(client=mock_redis)

            msg = StreamMessage(
                thread_id="thread_123",
                node_name="query_or_respond",
                message_type="token",
                status="streaming",
                timestamp=1705740000.0,
                data={"token": "你好"},
            )

            await publisher.publish_message(msg)

            # 验证只发布到 Pub/Sub
            assert mock_redis.publish.called
            assert not mock_redis.xadd.called

    @pytest.mark.asyncio
    async def test_stream_message_serialization_for_stream(self):
        """测试消息序列化为 Stream 字段格式。"""
        msg = StreamMessage(
            thread_id="thread_123",
            node_name="generate",
            message_type="output",
            status="completed",
            timestamp=1705740000.123,
            data={"messages": [{"type": "ai", "content": "Hello"}]},
            execution_time_ms=500.0,
        )

        # 模拟 Stream 字段格式
        fields = {
            "node_name": msg.node_name,
            "message_type": msg.message_type,
            "status": msg.status,
            "timestamp": str(msg.timestamp),
            "data": json.dumps(msg.data, ensure_ascii=False, default=str),
            "execution_time_ms": str(msg.execution_time_ms),
        }

        # 验证字段可以反序列化
        assert fields["node_name"] == "generate"
        assert fields["message_type"] == "output"
        assert fields["status"] == "completed"
        assert fields["timestamp"] == "1705740000.123"
        assert fields["execution_time_ms"] == "500.0"

        # 验证 data 可以反序列化
        data = json.loads(fields["data"])
        assert data["messages"][0]["type"] == "ai"

    @pytest.mark.asyncio
    async def test_publish_node_output_with_stream(self):
        """测试 publish_node_output 在 Stream 启用时的行为。"""
        mock_redis = AsyncMock()
        mock_redis.xadd.return_value = "1705740000000-0"
        mock_redis.xtrim = AsyncMock()
        mock_redis.expire = AsyncMock()
        mock_redis.publish = AsyncMock()

        with patch("infra.redis_pubsub.get_settings") as mock_settings:
            mock_settings.return_value.redis_stream_enabled = True
            mock_settings.return_value.stream_ttl_seconds = 3600
            mock_settings.return_value.stream_max_length = 1000

            publisher = RedisPublisher(client=mock_redis)

            await publisher.publish_node_output(
                thread_id="thread_123",
                node_name="tools",
                data={"result": "success"},
                status="completed",
                message_type="output",
                execution_time_ms=200.0,
            )

            # 验证消息被发布到 Stream
            assert mock_redis.xadd.called

    @pytest.mark.asyncio
    async def test_publish_workflow_complete_with_stream(self):
        """测试 publish_workflow_complete 在 Stream 启用时的行为。"""
        mock_redis = AsyncMock()
        mock_redis.xadd.return_value = "1705740000000-0"
        mock_redis.xtrim = AsyncMock()
        mock_redis.expire = AsyncMock()
        mock_redis.publish = AsyncMock()

        with patch("infra.redis_pubsub.get_settings") as mock_settings:
            mock_settings.return_value.redis_stream_enabled = True
            mock_settings.return_value.stream_ttl_seconds = 3600
            mock_settings.return_value.stream_max_length = 1000

            publisher = RedisPublisher(client=mock_redis)

            await publisher.publish_workflow_complete(
                thread_id="thread_123",
                data={"node_times": {"query_or_respond": 100, "tools": 200}},
                execution_time_ms=300.0,
            )

            # 验证消息被发布到 Stream
            assert mock_redis.xadd.called

    @pytest.mark.asyncio
    async def test_publish_workflow_error_with_stream(self):
        """测试 publish_workflow_error 在 Stream 启用时的行为。"""
        mock_redis = AsyncMock()
        mock_redis.xadd.return_value = "1705740000000-0"
        mock_redis.xtrim = AsyncMock()
        mock_redis.expire = AsyncMock()
        mock_redis.publish = AsyncMock()

        with patch("infra.redis_pubsub.get_settings") as mock_settings:
            mock_settings.return_value.redis_stream_enabled = True
            mock_settings.return_value.stream_ttl_seconds = 3600
            mock_settings.return_value.stream_max_length = 1000

            publisher = RedisPublisher(client=mock_redis)

            await publisher.publish_workflow_error(
                thread_id="thread_123",
                error="Workflow timeout",
                data={"error_type": "timeout", "timeout_seconds": 300},
            )

            # 验证消息被发布到 Stream
            assert mock_redis.xadd.called

    @pytest.mark.asyncio
    async def test_stream_publish_error_handling(self):
        """测试 Stream 发布失败时的错误处理。"""
        mock_redis = AsyncMock()
        mock_redis.xadd.side_effect = Exception("Redis connection failed")

        with patch("infra.redis_pubsub.get_settings") as mock_settings:
            mock_settings.return_value.redis_stream_enabled = True
            mock_settings.return_value.stream_ttl_seconds = 3600
            mock_settings.return_value.stream_max_length = 1000

            publisher = RedisPublisher(client=mock_redis)

            msg = StreamMessage(
                thread_id="thread_123",
                node_name="query_or_respond",
                message_type="output",
                status="completed",
                timestamp=1705740000.0,
                data={"key": "value"},
            )

            # 应该不抛出异常，只记录错误
            message_id = await publisher._publish_to_stream(msg)
            assert message_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
