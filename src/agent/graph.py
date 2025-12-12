"""使用 LangGraph 的简单 RAG 实现。

参考：https://docs.langchain.com/oss/python/langchain/rag

本模块实现了一个直接的 RAG 工作流：
1. 使用检索工具调用 LLM
2. 检索相关文档
3. 基于检索的上下文生成答案
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
from tools.web_search import web_search
from utils.llm import load_chat_model


# ============================================================================
# 模型
# ============================================================================


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    return load_chat_model(fully_specified_name=chat_model, temperature=0.7, max_retries=2)


def _prepend_system_prompt(messages: List) -> List:
    """将包含当前时间的系统提示添加到消息列表中。"""
    system_message = SystemMessage(content=prompts.SYSTEM_PROMPT.format(time=_now_iso()))
    return [system_message, *messages]


def _extract_user_question(messages: List) -> str:
    """返回最近的用户问题。"""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message.content
    return ""


def _extract_retrieved_context(messages: List) -> str:
    """返回最新的工具输出（如果有）。"""
    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            return message.content
    return ""


# ============================================================================
# 图节点（异步）
# ============================================================================

async def query_or_respond(state: MessagesState, config: Optional[RunnableConfig] = None):
    """使用检索工具调用 LLM 以决定是否需要文档/项目/网络搜索。
    
    参数：
        state: 包含用户问题的 MessagesState
        config: 可选的 LangGraph 配置，包含可配置参数
            - chat_model: 使用的聊天模型
            - enable_websearch: 是否启用网络搜索（默认 False）
        
    返回：
        dict: 更新后的状态，包含 AI 响应（如需检索则包含 tool_calls）
    """
    # 从配置中提取参数
    chat_model = None
    enable_websearch = False
    if config and hasattr(config, "configurable") and config.configurable:
        chat_model = config.configurable.get("chat_model")
        enable_websearch = config.configurable.get("enable_websearch", False)
    elif config and isinstance(config, dict) and "configurable" in config:
        chat_model = config["configurable"].get("chat_model")
        enable_websearch = config["configurable"].get("enable_websearch", False)
    
    # 根据配置构建工具列表
    tools = [retrieve_context]
    settings = get_settings()
    if settings.project_search_enabled:
        tools.append(search_projects)
    if enable_websearch and settings.tavily_api_key:
        tools.append(web_search)
    
    llm = _get_llm(chat_model)
    llm_with_tools = llm.bind_tools(tools)
    response = await llm_with_tools.ainvoke(
        _prepend_system_prompt(state["messages"])
    )
    return {"messages": [response]}


async def generate(state: MessagesState, config: Optional[RunnableConfig] = None):
    """基于检索的文档生成答案。
    
    参数：
        state: 包含对话历史和检索文档的 MessagesState
        config: 可选的 LangGraph 配置，包含可配置参数
        
    返回：
        dict: 更新后的状态，包含最终答案
    """
    # 从配置中提取 chat_model（如果提供）
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
# 构建图
# ============================================================================

# 初始化工作流
workflow = StateGraph(MessagesState)

# 根据配置构建工具列表
_tools = [retrieve_context]
_settings = get_settings()
if _settings.project_search_enabled:
    _tools.append(search_projects)
if _settings.tavily_api_key:
    _tools.append(web_search)

# 添加节点
workflow.add_node("query_or_respond", query_or_respond)
workflow.add_node("tools", ToolNode(_tools))
workflow.add_node("generate", generate)

# 设置入口点
workflow.set_entry_point("query_or_respond")

# 条件边：如果存在 tool_calls，检索文档；否则结束
workflow.add_conditional_edges(
    "query_or_respond",
    tools_condition,
)

# 检索后，生成答案
workflow.add_edge("tools", "generate")

# 生成答案后，结束
workflow.add_edge("generate", END)

# ============================================================================
# 图编译辅助函数
# ============================================================================

def build_graph(
    *,
    checkpointer: Optional[object] = None,
    store: Optional[BaseStore] = None,
):
    """为 LangGraph API / 开发服务器编译图。
    
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
