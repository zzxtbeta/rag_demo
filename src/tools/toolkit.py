"""Tool registry and ToolNode construction.

This module centralizes:
- Which tools are available
- How tools are exposed to the model (per-request)
- How the tool execution node is configured (global)

Keeping this out of `agent/graph.py` helps the graph remain clear.
"""

from __future__ import annotations

import asyncio
from typing import List

from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolNode

from config.settings import get_settings
from tools.project_search import search_projects
from tools.retrieval import retrieve_context
from tools.web_search import web_search


def get_model_tools(*, enable_websearch: bool) -> List:
    """Tools bound to the model for a single request."""
    settings = get_settings()

    tools: list = [retrieve_context]
    if settings.project_search_enabled:
        tools.append(search_projects)
    if enable_websearch and settings.tavily_api_key:
        tools.append(web_search)

    return tools


def get_tool_node_tools() -> List:
    """Tools available to the ToolNode.

    This should be a superset of any tools that might be requested by the model
    across requests, because the ToolNode is typically constructed at graph build
    time (not per request).
    """
    settings = get_settings()

    tools: list = [retrieve_context]
    if settings.project_search_enabled:
        tools.append(search_projects)
    if settings.tavily_api_key:
        tools.append(web_search)

    return tools


def handle_tool_errors(request, handler):
    """Return ToolMessage to the model when a tool fails.

    This follows the official Agents docs pattern: catch exception and return
    `ToolMessage(..., tool_call_id=request.tool_call["id"])`.
    """
    try:
        return handler(request)
    except Exception as e:  # noqa: BLE001
        return ToolMessage(
            content=f"Tool error: Please check your input and try again. ({str(e)})",
            name=request.tool_call.get("name"),
            tool_call_id=request.tool_call["id"],
        )


async def ahandle_tool_errors(request, handler):
    """Async variant of tool error wrapper.

    Important: ToolNode chooses sync vs async execution based on whether it gets
    `wrap_tool_call` or `awrap_tool_call`. If we pass a sync wrapper while running
    in an async graph, ToolNode may fall back to sync tool invocation, which breaks
    async tools (e.g., StructuredTool that only supports async).
    """
    try:
        result = handler(request)
        if asyncio.iscoroutine(result):
            return await result
        return result
    except Exception as e:  # noqa: BLE001
        return ToolMessage(
            content=f"Tool error: Please check your input and try again. ({str(e)})",
            name=request.tool_call.get("name"),
            tool_call_id=request.tool_call["id"],
        )


def build_tool_node(*, messages_key: str = "messages") -> ToolNode:
    """Build a ToolNode with consistent error handling."""
    return ToolNode(
        get_tool_node_tools(),
        messages_key=messages_key,
        handle_tool_errors=True,
        awrap_tool_call=ahandle_tool_errors,
    )


__all__ = [
    "get_model_tools",
    "get_tool_node_tools",
    "handle_tool_errors",
    "ahandle_tool_errors",
    "build_tool_node",
]
