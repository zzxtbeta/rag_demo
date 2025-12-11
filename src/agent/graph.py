"""Simple RAG implementation with LangGraph.

Reference: https://docs.langchain.com/oss/python/langchain/rag

This module implements a straightforward RAG workflow:
1. Call LLM with retrieval tool
2. Retrieve relevant documents
3. Generate answer based on retrieved context
"""

from datetime import datetime, timezone
from functools import lru_cache
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.store.base import BaseStore

from agent import prompts
from config.settings import get_settings
from tools.retrieval import retrieve_context
from tools.project_search import search_projects
from utils.llm import load_chat_model


# ============================================================================
# Model
# ============================================================================


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@lru_cache(maxsize=10)
def _get_llm(chat_model: Optional[str] = None):
    """Return a cached chat model instance.
    
    Args:
        chat_model: Optional model name. If None, uses default from settings.
    
    Returns:
        BaseChatModel: Configured chat model instance.
    """
    if chat_model is None:
        settings = get_settings()
        chat_model = settings.chat_model
    return load_chat_model(fully_specified_name=chat_model, temperature=0.7, max_retries=2)


def _prepend_system_prompt(messages: List) -> List:
    """Add the system prompt with the current time to the message list."""
    system_message = SystemMessage(content=prompts.SYSTEM_PROMPT.format(time=_now_iso()))
    return [system_message, *messages]


def _extract_user_question(messages: List) -> str:
    """Return the most recent user question."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message.content
    return ""


def _extract_retrieved_context(messages: List) -> str:
    """Return the latest tool output, if any."""
    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            return message.content
    return ""


# ============================================================================
# Graph Nodes (async)
# ============================================================================

async def query_or_respond(state: MessagesState, config: Optional[RunnableConfig] = None):
    """Call LLM with retrieval tools to decide if documents/projects are needed.
    
    Args:
        state: MessagesState with user question
        config: Optional LangGraph config containing configurable parameters
        
    Returns:
        dict: Updated state with AI response (includes tool_calls if retrieval needed)
    """
    # Extract chat_model from config if provided
    chat_model = None
    if config and hasattr(config, "configurable") and config.configurable:
        chat_model = config.configurable.get("chat_model")
    elif config and isinstance(config, dict) and "configurable" in config:
        chat_model = config["configurable"].get("chat_model")
    
    # Build tools list based on configuration
    tools = [retrieve_context]
    settings = get_settings()
    if settings.project_search_enabled:
        tools.append(search_projects)
    
    llm = _get_llm(chat_model)
    llm_with_tools = llm.bind_tools(tools)
    response = await llm_with_tools.ainvoke(
        _prepend_system_prompt(state["messages"])
    )
    return {"messages": [response]}


async def generate(state: MessagesState, config: Optional[RunnableConfig] = None):
    """Generate answer based on retrieved documents.
    
    Args:
        state: MessagesState with conversation history and retrieved documents
        config: Optional LangGraph config containing configurable parameters
        
    Returns:
        dict: Updated state with final answer
    """
    # Extract chat_model from config if provided
    chat_model = None
    if config and hasattr(config, "configurable") and config.configurable:
        chat_model = config.configurable.get("chat_model")
    elif config and isinstance(config, dict) and "configurable" in config:
        chat_model = config["configurable"].get("chat_model")
    
    question = _extract_user_question(state["messages"])
    documents = _extract_retrieved_context(state["messages"])
    prompt = prompts.GENERATE_ANSWER_PROMPT.format(
        question=question or "No question provided.",
        documents=documents or "No supporting documents were retrieved.",
    )
    llm = _get_llm(chat_model)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"messages": [response]}


# ============================================================================
# Build Graph
# ============================================================================

# Initialize workflow
workflow = StateGraph(MessagesState)

# Build tools list based on configuration
_tools = [retrieve_context]
_settings = get_settings()
if _settings.project_search_enabled:
    _tools.append(search_projects)

# Add nodes
workflow.add_node("query_or_respond", query_or_respond)
workflow.add_node("tools", ToolNode(_tools))
workflow.add_node("generate", generate)

# Set entry point
workflow.set_entry_point("query_or_respond")

# Conditional edge: if tool_calls exist, retrieve documents; otherwise end
workflow.add_conditional_edges(
    "query_or_respond",
    tools_condition,
)

# After retrieval, generate answer
workflow.add_edge("tools", "generate")

# After generating answer, end
workflow.add_edge("generate", END)

# ============================================================================
# Graph Compilation Helpers
# ============================================================================

def build_graph(
    *,
    checkpointer: Optional[object] = None,
    store: Optional[BaseStore] = None,
):
    """Compile the graph for use with LangGraph API / dev server.
    
    在 LangGraph API / Cloud 环境下，checkpoint 持久化由平台统一管理，
    这里不再强制绑定自定义 checkpointer。
    
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
