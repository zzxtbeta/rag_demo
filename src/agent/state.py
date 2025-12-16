"""定义共享状态类型。

说明：
LangGraph Quickstart 的 Full code example 使用 `TypedDict` 定义 State，
并通过 `Annotated[..., operator.add]` 指定 reducer，保证 messages 追加而非覆盖。
"""

from __future__ import annotations

import operator

from langchain_core.messages import AnyMessage
from typing_extensions import Annotated, TypedDict


class State(TypedDict, total=False):
    """主图状态（最小集合）。"""

    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


__all__ = ["State"]
