"""LangGraph Graph API: minimal ReAct-style tool loop.

Structure (aligned with LangGraph Quickstart full code example):
- LLM node decides whether to call tools
- Tool node executes tool_calls and returns ToolMessage(s)
- Loop: tools -> LLM until no tool_calls, then END
"""

from functools import lru_cache
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.store.base import BaseStore

from agent import prompts
from agent.state import State
from config.settings import get_settings
from tools.toolkit import build_tool_node, get_model_tools
from utils.graph_helpers import prepend_system_prompt
from utils.llm import load_chat_model


# ============================================================================
# 模型
# ============================================================================


@lru_cache(maxsize=10)
def _get_llm(chat_model: Optional[str] = None):
    """返回缓存的聊天模型实例。
    
    参数：
        chat_model: 可选的模型名称。如果为 None，使用设置中的默认值。
    
    返回：
        BaseChatModel: 配置好的聊天模型实例。
    """
    if chat_model is None:
        settings = get_settings()
        chat_model = settings.chat_model
    return load_chat_model(
        fully_specified_name=chat_model,
        temperature=0.7,
        max_retries=2,
    )


# ============================================================================
# 图节点（异步）
# ============================================================================

async def query_or_respond(state: State, config: Optional[RunnableConfig] = None):
    """LLM decides whether to call tools or reply directly."""
    # 从配置中提取参数
    chat_model = None
    enable_websearch = False
    enable_retrieval = None
    if config and hasattr(config, "configurable") and config.configurable:
        chat_model = config.configurable.get("chat_model")
        enable_websearch = config.configurable.get("enable_websearch", False)
        enable_retrieval = config.configurable.get("enable_retrieval")
    elif config and isinstance(config, dict) and "configurable" in config:
        chat_model = config["configurable"].get("chat_model")
        enable_websearch = config["configurable"].get("enable_websearch", False)
        enable_retrieval = config["configurable"].get("enable_retrieval")
    
    tools = get_model_tools(enable_websearch=enable_websearch, enable_retrieval=enable_retrieval)
    
    llm = _get_llm(chat_model)
    llm_with_tools = llm.bind_tools(tools)
    response = await llm_with_tools.ainvoke(
        prepend_system_prompt(state["messages"], prompts.SYSTEM_PROMPT)
    )

    # 统计 LLM 调用次数（参考 LangGraph Quickstart full code example 的写法）
    llm_calls = state.get("llm_calls", 0) + 1

    return {"messages": [response], "llm_calls": llm_calls}


def _should_continue(state: State):
    """Route to tools if the last AIMessage contains tool calls; else end."""
    messages = state.get("messages", [])
    if messages and getattr(messages[-1], "tool_calls", None):
        return "tools"
    return END


# ============================================================================
# 构建图
# ============================================================================

# 初始化工作流
workflow = StateGraph(State)

# 添加节点
workflow.add_node("query_or_respond", query_or_respond)
workflow.add_node("tools", build_tool_node())

# 设置入口点
workflow.set_entry_point("query_or_respond")

workflow.add_conditional_edges(
    "query_or_respond",
    _should_continue,
    ["tools", END],
)

# 工具执行后回到 LLM，形成循环（ReAct loop 结构）
workflow.add_edge("tools", "query_or_respond")

# ============================================================================
# 图编译辅助函数
# ============================================================================

def build_graph(
    *,
    checkpointer: Optional[object] = None,
    store: Optional[BaseStore] = None,
):
    """为 LangGraph API / 开发服务器编译图。
    - 本地直接调用时：可通过 `build_graph(checkpointer=...)` 传入自定义 Saver。
    - 使用 `langgraph dev` / `langgraph up` 时：平台会忽略代码层的 checkpointer，
      并根据环境变量（如 POSTGRES_URI）自动配置持久化。
    """
    compile_kwargs: dict = {"store": store}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    compiled = workflow.compile(**compile_kwargs)
    compiled.name = "Gravaity_Agent"
    return compiled


graph = build_graph()


__all__ = ["graph", "build_graph"]
