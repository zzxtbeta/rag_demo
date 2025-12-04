"""Unit tests for Redis Pub/Sub serialization."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest

from infra.redis_pubsub import StreamMessage


class TestStreamMessageSerialization:
    """测试 StreamMessage 的 JSON 序列化功能，特别是 AIMessage 的处理。"""

    def test_basic_serialization(self):
        """测试基本类型的序列化。"""
        msg = StreamMessage(
            thread_id="test-thread-123",
            node_name="test_node",
            message_type="output",
            status="running",
            timestamp=1234567890.0,
            data={"key": "value", "number": 42},
            execution_time_ms=100.5,
        )

        json_str = msg.to_json()
        assert isinstance(json_str, str)

        # 验证可以反序列化
        parsed = json.loads(json_str)
        assert parsed["thread_id"] == "test-thread-123"
        assert parsed["node_name"] == "test_node"
        assert parsed["data"]["key"] == "value"
        assert parsed["data"]["number"] == 42
        assert parsed["execution_time_ms"] == 100.5

    def test_aimessage_serialization(self):
        """测试 AIMessage 的序列化（核心修复点）。"""
        try:
            from langchain_core.messages import AIMessage
        except ImportError:
            pytest.skip("langchain_core not available")

        # 创建一个包含 AIMessage 的消息
        ai_message = AIMessage(content="Hello from AI", tool_calls=[])

        msg = StreamMessage(
            thread_id="test-thread-aimessage",
            node_name="generate",
            message_type="output",
            status="completed",
            timestamp=1234567890.0,
            data={
                "messages": [ai_message],
                "other_data": "test",
            },
        )

        # ✅ 关键测试：序列化不应该抛出异常
        json_str = msg.to_json()
        assert isinstance(json_str, str)

        # 验证可以反序列化
        parsed = json.loads(json_str)
        assert parsed["thread_id"] == "test-thread-aimessage"
        assert parsed["node_name"] == "generate"

        # 验证 AIMessage 被正确转换
        messages = parsed["data"]["messages"]
        assert isinstance(messages, list)
        assert len(messages) == 1

        # message_to_dict 转换后的格式：{"type": "ai", "data": {"content": ...}}
        msg_dict = messages[0]
        assert "type" in msg_dict
        assert msg_dict["type"] == "ai"
        # content 在 data 字段中
        assert msg_dict.get("data", {}).get("content") == "Hello from AI"

    def test_nested_aimessage_in_dict(self):
        """测试嵌套在字典中的 AIMessage。"""
        try:
            from langchain_core.messages import AIMessage, HumanMessage
        except ImportError:
            pytest.skip("langchain_core not available")

        ai_msg = AIMessage(content="AI response")
        human_msg = HumanMessage(content="User question")

        msg = StreamMessage(
            thread_id="test-nested",
            node_name="query_or_respond",
            message_type="output",
            status="running",
            timestamp=1234567890.0,
            data={
                "messages": [human_msg, ai_msg],
                "metadata": {
                    "last_message": ai_msg,
                    "count": 2,
                },
            },
        )

        json_str = msg.to_json()
        parsed = json.loads(json_str)

        # 验证嵌套的消息都被正确转换
        assert len(parsed["data"]["messages"]) == 2
        assert parsed["data"]["metadata"]["count"] == 2

    def test_aimessage_in_list(self):
        """测试列表中的多个 AIMessage。"""
        try:
            from langchain_core.messages import AIMessage
        except ImportError:
            pytest.skip("langchain_core not available")

        messages = [
            AIMessage(content=f"Response {i}")
            for i in range(3)
        ]

        msg = StreamMessage(
            thread_id="test-list",
            node_name="generate",
            message_type="output",
            status="completed",
            timestamp=1234567890.0,
            data={"messages": messages},
        )

        json_str = msg.to_json()
        parsed = json.loads(json_str)

        assert len(parsed["data"]["messages"]) == 3
        for i, msg_dict in enumerate(parsed["data"]["messages"]):
            # message_to_dict 返回格式：{"type": "ai", "data": {"content": ...}}
            assert msg_dict.get("data", {}).get("content") == f"Response {i}"
            assert msg_dict["type"] == "ai"

    def test_mixed_types(self):
        """测试混合类型的数据（字符串、数字、AIMessage）。"""
        try:
            from langchain_core.messages import AIMessage
        except ImportError:
            pytest.skip("langchain_core not available")

        ai_msg = AIMessage(content="Mixed content")

        msg = StreamMessage(
            thread_id="test-mixed",
            node_name="test",
            message_type="output",
            status="running",
            timestamp=1234567890.0,
            data={
                "string": "text",
                "number": 42,
                "boolean": True,
                "list": [1, 2, 3],
                "message": ai_msg,
                "nested": {
                    "inner": ai_msg,
                },
            },
        )

        json_str = msg.to_json()
        parsed = json.loads(json_str)

        assert parsed["data"]["string"] == "text"
        assert parsed["data"]["number"] == 42
        assert parsed["data"]["boolean"] is True
        assert parsed["data"]["list"] == [1, 2, 3]
        # message 和 nested.inner 都应该是转换后的字典
        assert isinstance(parsed["data"]["message"], dict)
        assert isinstance(parsed["data"]["nested"]["inner"], dict)

    def test_fallback_on_serialization_error(self):
        """测试序列化错误时的 fallback 机制。"""
        # 创建一个会导致序列化失败的对象
        class Unserializable:
            def __str__(self):
                raise Exception("Cannot serialize")

        msg = StreamMessage(
            thread_id="test-fallback",
            node_name="test",
            message_type="output",
            status="error",
            timestamp=1234567890.0,
            data={"bad_obj": Unserializable()},
        )

        # 应该使用 fallback，不会抛出异常
        json_str = msg.to_json()
        assert isinstance(json_str, str)

        # fallback 应该包含基本字段
        parsed = json.loads(json_str)
        assert "thread_id" in parsed
        assert "node_name" in parsed

    def test_empty_data(self):
        """测试空数据的序列化。"""
        msg = StreamMessage(
            thread_id="test-empty",
            node_name="test",
            message_type="output",
            status="completed",
            timestamp=1234567890.0,
            data={},
        )

        json_str = msg.to_json()
        parsed = json.loads(json_str)

        assert parsed["data"] == {}
        assert parsed["execution_time_ms"] is None

    def test_real_world_scenario(self):
        """测试真实场景：LangGraph updates 格式。"""
        try:
            from langchain_core.messages import AIMessage, HumanMessage
        except ImportError:
            pytest.skip("langchain_core not available")

        # 模拟 LangGraph astream(stream_mode="updates") 返回的格式
        update_data = {
            "messages": [
                HumanMessage(content="What is RAG?"),
                AIMessage(content="RAG stands for Retrieval Augmented Generation..."),
            ],
            "next": ["generate"],
        }

        msg = StreamMessage(
            thread_id="thread_real_123",
            node_name="query_or_respond",
            message_type="output",
            status="running",
            timestamp=1234567890.0,
            data=update_data,
        )

        json_str = msg.to_json()
        parsed = json.loads(json_str)

        # 验证结构完整
        assert parsed["thread_id"] == "thread_real_123"
        assert parsed["node_name"] == "query_or_respond"
        assert len(parsed["data"]["messages"]) == 2
        assert parsed["data"]["next"] == ["generate"]

        # 验证消息内容（message_to_dict 返回格式：{"type": "...", "data": {"content": ...}}）
        human_msg = parsed["data"]["messages"][0]
        ai_msg = parsed["data"]["messages"][1]
        assert human_msg.get("data", {}).get("content") == "What is RAG?"
        assert human_msg["type"] == "human"
        assert "RAG stands for" in ai_msg.get("data", {}).get("content", "")
        assert ai_msg["type"] == "ai"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

