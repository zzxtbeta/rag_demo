"""聊天相关的 API 端点。"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from api.dependencies import get_graph, get_redis_publisher
from db.checkpointer import CheckpointerManager
from api.schemas import (
    ChatRequest,
    ChatResponse,
    StreamStartResponse,
    HistoryMessage,
    ThreadHistory,
    TraceRun,
    ThreadHistoryWithTrace,
)
from api.utils import extract_content
from langchain_core.messages import AIMessage, BaseMessage
from config.settings import get_settings
from infra.redis_pubsub import RedisPublisher, StreamMessage
from utils.langsmith_client import get_langsmith_client

logger = logging.getLogger(__name__)

try:
    from langchain_core.messages import BaseMessage, message_to_dict  # type: ignore
except Exception:  # pragma: no cover - 防御性处理
    BaseMessage = None  # type: ignore[assignment]
    message_to_dict = None  # type: ignore[assignment]


router = APIRouter()


def build_trace_tree(trace_runs: list[TraceRun]) -> list[dict[str, Any]]:
    """构建 trace 执行树。
    
    Args:
        trace_runs: TraceRun 对象列表
        
    Returns:
        树形结构的 trace runs（只包含根节点，子节点在 children 字段中）
    """
    if not trace_runs:
        return []
    
    # 将 Pydantic 对象转换为字典
    runs_dict = [r.model_dump() for r in trace_runs]
    
    # 建立索引
    run_map = {r["run_id"]: r for r in runs_dict}
    children_map = {r["run_id"]: [] for r in runs_dict}
    
    # 找到根节点和子节点关系
    roots = []
    for r in runs_dict:
        parent_id = r.get("parent_run_id")
        if parent_id and parent_id in children_map:
            children_map[parent_id].append(r)
        else:
            roots.append(r)
    
    # 深度优先搜索构建树节点
    def build_node(run: dict[str, Any]) -> dict[str, Any]:
        children = children_map.get(run["run_id"], [])
        node = {
            "run_id": run["run_id"],
            "name": run["name"],
            "run_type": run["run_type"],
            "start_time": run["start_time"],
            "end_time": run.get("end_time"),
            "latency_ms": run.get("latency_ms"),
            "total_tokens": run.get("total_tokens"),
            "prompt_tokens": run.get("prompt_tokens"),
            "completion_tokens": run.get("completion_tokens"),
            "error": run.get("error"),
            "inputs": run.get("inputs"),
            "outputs": run.get("outputs"),
            "parent_run_id": run.get("parent_run_id"),
            "children": [build_node(c) for c in children]
        }
        return node
    
    return [build_node(r) for r in roots]


def _normalize_update(obj: Any) -> Any:
    """递归转换 LangChain 消息对象为 JSON 可序列化格式。

    ✅ 处理流程：
    1. 如果是 BaseMessage（如 AIMessage），使用 message_to_dict 转换
    2. 如果是字典/列表/元组，递归处理所有嵌套元素
    3. 其他类型直接返回

    参数：
    - obj: 待转换的对象（可能是 BaseMessage、dict、list、tuple 等）

    返回：
    - 转换后的 JSON 友好格式对象

    注意：
    - 此函数用于在发布到 Redis 前预处理 LangGraph 的 state delta
    - 确保 AIMessage 等 LangChain 对象能被正确序列化
    """
    if BaseMessage is not None and isinstance(obj, BaseMessage):
        if message_to_dict is not None:
            return message_to_dict(obj)
        return {"type": obj.__class__.__name__, "content": getattr(obj, "content", "")}
    if isinstance(obj, dict):
        return {k: _normalize_update(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_update(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_normalize_update(v) for v in obj)
    return obj


async def _stream_workflow_to_redis(
    *,
    graph,
    payload: dict[str, Any],
    config: dict[str, Any],
    thread_id: str,
    publisher: RedisPublisher,
) -> None:
    """后台执行工作流并将节点更新发布到 Redis。

    ✅ 简化流程：
    1. 使用 stream_mode=["updates", "messages", "custom"] 混合模式
    2. 只发布关键事件（completed、token、custom）
    3. 移除 start 事件，保持界面整洁
    4. 工作流完成后发布 workflow:complete
    5. 错误时发布 workflow:error

    参数：
    - graph: LangGraph 工作流实例
    - payload: 输入数据，包含 messages 数组
    - config: LangGraph 配置，包含 thread_id、user_id
    - thread_id: 会话线程 ID，用于 Redis 频道命名
    - publisher: Redis 发布器实例

    事件发布：
    - workflow:{thread_id}:{node_name}:token - LLM token 流式输出
    - workflow:{thread_id}:{node_name}:output - 节点完成
    - workflow:{thread_id}:custom:custom - 自定义状态更新
    - workflow:{thread_id}:workflow:complete - 工作流完成
    - workflow:{thread_id}:workflow:error - 工作流错误

    注意：
    - 混合模式返回 (mode, chunk) 元组
    - messages 模式：LLM token 流式输出
    - updates 模式：节点完成事件（无 start 事件）
    - custom 模式：自定义进度提示（从节点内部发送）
    - 超时时间由 WORKFLOW_TIMEOUT_SECONDS 配置（默认 300 秒）
    """
    start_time = time.perf_counter()
    node_times: dict[str, float] = {}

    settings = get_settings()
    timeout_seconds = settings.workflow_timeout_seconds

    async def _process_stream():
        async for stream_mode, chunk in graph.astream(
            payload,
            config,
            stream_mode=["updates", "messages", "custom"],
        ):
            if stream_mode == "messages":
                # messages 模式：chunk 是 (message_chunk, metadata) 元组
                # 用于流式输出 LLM 生成的 token
                message_chunk, metadata = chunk
                node_name = metadata.get("langgraph_node", "unknown")
                
                # 仅处理 LLM 节点的 token（query_or_respond 和 generate）
                if node_name in ("query_or_respond", "generate"):
                    # 提取 token 内容
                    token_content = ""
                    if hasattr(message_chunk, "content"):
                        token_content = str(message_chunk.content) if message_chunk.content else ""
                    elif hasattr(message_chunk, "text"):
                        token_content = str(message_chunk.text) if message_chunk.text else ""
                    else:
                        # 规范化后从字典提取
                        normalized_chunk = _normalize_update(message_chunk)
                        if isinstance(normalized_chunk, dict):
                            if "content" in normalized_chunk:
                                token_content = str(normalized_chunk["content"])
                            elif isinstance(normalized_chunk.get("text"), str):
                                token_content = normalized_chunk["text"]
                    
                    # 仅发送非空的 token
                    if token_content:
                        await publisher.publish_node_output(
                            thread_id=thread_id,
                            node_name=node_name,
                            data={
                                "token": token_content,
                                "chunk": _normalize_update(message_chunk),
                                "metadata": _normalize_update(metadata),
                            },
                            status="streaming",
                            message_type="token",
                        )
                
            elif stream_mode == "updates":
                # updates 模式：节点完成事件（移除 start 事件）
                for node_name, update in chunk.items():
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    node_times[node_name] = elapsed_ms

                    normalized = _normalize_update(update)
                    # 仅发布节点完成事件
                    await publisher.publish_node_output(
                        thread_id=thread_id,
                        node_name=node_name,
                        data=normalized,
                        status="completed",
                        message_type="output",
                        execution_time_ms=elapsed_ms,
                    )
            
            elif stream_mode == "custom":
                # custom 模式：自定义状态更新（从节点内部发送）
                await publisher.publish_message(
                    StreamMessage(
                        thread_id=thread_id,
                        node_name="custom",
                        message_type="custom",
                        status="info",
                        timestamp=time.time(),
                        data=chunk,
                    )
                )

    try:
        await asyncio.wait_for(_process_stream(), timeout=timeout_seconds)

        total_ms = (time.perf_counter() - start_time) * 1000
        await publisher.publish_workflow_complete(
            thread_id=thread_id,
            data={"node_times": node_times, "total_ms": total_ms},
            execution_time_ms=total_ms,
        )
    except asyncio.CancelledError:
        logger.info(f"Workflow cancelled: {thread_id}")
    except asyncio.TimeoutError:
        logger.warning(f"Workflow timeout after {timeout_seconds}s: {thread_id}")
        await publisher.publish_workflow_error(
            thread_id=thread_id,
            error=f"Workflow execution exceeded {timeout_seconds}s timeout",
            data={"error_type": "timeout", "timeout_seconds": timeout_seconds},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Workflow error: {exc}")
        await publisher.publish_workflow_error(
            thread_id=thread_id,
            error=str(exc),
            data={"error_type": "execution_error"},
        )


@router.post("/stream", response_model=StreamStartResponse)
async def chat_stream_endpoint(
    req: ChatRequest,
    background_tasks: BackgroundTasks,
    graph=Depends(get_graph),
    publisher: RedisPublisher = Depends(get_redis_publisher),
):
    """启动流式聊天工作流并发布节点更新到 Redis。

    ✅ 流程：
    1. 立即返回 thread_id 和 WebSocket 订阅频道
    2. 后台启动 graph.astream，发送节点事件到 Redis
    3. 前端通过 WebSocket 订阅 Redis 频道接收实时更新

    返回的响应包含：
    - thread_id: 工作流会话标识，用于后续状态查询和恢复
    - user_id: 用户标识（可选），用于记忆命名空间
    - ws_channel: Redis 频道模式，格式为 workflow:{thread_id}:*
    - status: 固定为 "streaming"，表示流式执行已启动

    参数：
    - req: 聊天请求，包含 thread_id、user_id、message
    - background_tasks: FastAPI 后台任务管理器
    - graph: LangGraph 工作流实例（通过依赖注入）
    - publisher: Redis 发布器实例（通过依赖注入）

    返回：
    - StreamStartResponse: 包含 thread_id、ws_channel、status

    前端使用方式：
    1. 调用此接口获取 thread_id 和 ws_channel
    2. 连接 WebSocket: ws://host/ws/{thread_id}
    3. 订阅 Redis 频道: workflow:{thread_id}:*
    4. 接收实时节点更新事件

    注意：
    - 此接口立即返回，不等待工作流完成
    - 实际工作流在后台异步执行，通过 Redis Pub/Sub 推送更新
    - 前端需要主动订阅 WebSocket 才能接收更新
    - 同一个 thread_id 可以多次调用，共享对话上下文
    """
    config: dict[str, Any] = {"configurable": {"thread_id": req.thread_id}}
    if req.user_id:
        config["configurable"]["user_id"] = req.user_id
    if req.chat_model:
        config["configurable"]["chat_model"] = req.chat_model
    if req.enable_websearch:
        config["configurable"]["enable_websearch"] = req.enable_websearch

    # Combine message with uploaded documents for LLM
    message_content = req.message
    if req.documents:
        # Add document metadata markers for frontend extraction
        doc_section = "\n\n<uploaded_documents>\n"
        for idx, doc in enumerate(req.documents):
            # Include metadata in markers for frontend to parse
            doc_section += f'<document index="{idx}" filename="{doc.filename}" format="{doc.format}">\n{doc.markdown_content}\n</document>\n'
        doc_section += "</uploaded_documents>"
        message_content += doc_section

    payload: dict[str, Any] = {
        "messages": [{"role": "user", "content": message_content}]
    }

    background_tasks.add_task(
        _stream_workflow_to_redis,
        graph=graph,
        payload=payload,
        config=config,
        thread_id=req.thread_id,
        publisher=publisher,
    )

    return StreamStartResponse(
        thread_id=req.thread_id,
        user_id=req.user_id,
        ws_channel=f"workflow:{req.thread_id}:*",
        status="streaming",
    )


def _filter_user_visible_messages(messages: list[BaseMessage], thread_id: str) -> list[HistoryMessage]:
    """过滤并转换消息为用户可见的格式。
    
    只保留最终消息（用户输入和最终 LLM 输出），排除中间节点的输出。
    
    过滤规则：
    - HumanMessage: 保留所有
    - AIMessage: 只保留没有 tool_calls 的（最终回复）
    - ToolMessage: 跳过（中间过程）
    - SystemMessage: 跳过（系统内部）
    """
    from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage
    
    history_messages: list[HistoryMessage] = []
    
    for i, msg in enumerate(messages):
        # 跳过中间消息类型
        if isinstance(msg, (ToolMessage, SystemMessage)):
            continue
        
        # AI 消息：跳过带 tool_calls 的（中间决策过程）
        if isinstance(msg, AIMessage):
            if msg.tool_calls:
                continue
            # 跳过空内容的 AI 消息
            if not msg.content:
                continue
        
        # 提取基础字段
        msg_type = getattr(msg, "type", "unknown")
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        content = extract_content(msg)
        msg_id = getattr(msg, "id", None) or f"{thread_id}_{i}"
        
        # 提取时间戳
        timestamp = None
        if hasattr(msg, "timestamp"):
            timestamp = msg.timestamp
        elif hasattr(msg, "response_metadata"):
            metadata = getattr(msg, "response_metadata", {})
            if isinstance(metadata, dict):
                timestamp = metadata.get("timestamp")
        
        history_messages.append(
            HistoryMessage(
                id=str(msg_id),
                role=role,
                content=str(content) if content else "",
                timestamp=timestamp,
                type=msg_type,
                name=getattr(msg, "name", None),
                tool_calls=getattr(msg, "tool_calls", []),
                tool_call_id=getattr(msg, "tool_call_id", None),
                artifact=getattr(msg, "artifact", None),
            )
        )
    
    return history_messages


@router.get("/threads/{thread_id}/history", response_model=ThreadHistory)
async def get_thread_history(
    thread_id: str,
    graph=Depends(get_graph),
):
    """获取线程的对话历史（轻量级，不含 Trace）。

    ✅ 用途：
    - 前端默认使用此接口加载历史对话
    - 只返回用户输入和最终 LLM 输出，排除中间节点的处理过程
    - 性能优化，不查询 LangSmith Trace API
    - 适用于对话恢复、历史浏览等场景

    ✅ 流程：
    1. 从 LangGraph Checkpoint 获取当前状态
    2. 过滤消息：只保留用户消息和最终 AI 回复
    3. 转换为 HistoryMessage 格式返回

    参数：
    - thread_id: 会话线程标识

    返回：
    - ThreadHistory: 包含 thread_id、messages 列表、total_messages

    注意：
    - 如果线程不存在，返回 404 错误
    - 自动过滤掉中间节点的输出（如 query_or_respond 的 tool_calls、tools 节点的输出）
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = await graph.aget_state(config)
        
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thread not found: {thread_id}",
            )

        messages = state.values.get("messages", [])
        history_messages = _filter_user_visible_messages(messages, thread_id)

        return ThreadHistory(
            thread_id=thread_id,
            messages=history_messages,
            total_messages=len(history_messages),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Error fetching thread history: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch thread history: {str(exc)}",
        ) from exc


@router.get("/threads/{thread_id}/history-with-trace", response_model=ThreadHistoryWithTrace)
async def get_thread_history_with_trace(thread_id: str, graph=Depends(get_graph)):
    """获取线程的完整历史记录（含 LangSmith Trace 统计）。

    ✅ 用途：
    - 用于调试、性能分析、Token 统计等场景
    - 返回完整的 LangSmith Trace 树,包含所有节点执行信息
    - 提供根节点统计(总延迟、总 Token 消耗等)
    - 前端可选择性使用此接口获取详细执行信息

    ✅ 流程：
    1. 从 LangGraph Checkpoint 获取基本消息历史
    2. 从 LangSmith API 查询该 thread 的所有 Trace Runs
    3. 构建 Trace 树形结构(父子关系)
    4. 递归统计所有节点的 Token 消耗
    5. 合并返回完整数据(消息 + Trace 树 + 统计信息)

    参数：
    - thread_id: 会话线程标识

    返回：
    - ThreadHistoryWithTrace: 包含消息、trace_runs、trace_tree、统计信息

    注意：
    - 如果未配置 LangSmith,trace_runs 将为空数组
    - trace_runs 按 start_time 正序排列(从早到晚)
    - 查询 LangSmith API 有网络开销,建议按需使用
    - 前端默认不使用此接口,避免性能影响
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}

        # 1. 获取基本消息历史
        state = await graph.aget_state(config)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"线程未找到：{thread_id}",
            )

        messages = state.values.get("messages", [])
        history_messages = _filter_user_visible_messages(messages, thread_id)

        # 2. 从 LangSmith 获取 Trace Runs
        trace_runs: list[TraceRun] = []
        langsmith_client = get_langsmith_client()
        
        if langsmith_client:
            try:
                settings = get_settings()
                # 使用 LangSmith 官方推荐的 filter 语法查询 thread_id
                filter_string = (
                    f'and(in(metadata_key, ["session_id","conversation_id","thread_id"]), '
                    f'eq(metadata_value, "{thread_id}"))'
                )
                
                runs = []
                for run in langsmith_client.list_runs(
                    project_name=settings.langsmith_project,
                    filter=filter_string,
                ):
                    runs.append(run)
                
                # 按 start_time 升序排序（从早到晚）
                runs.sort(key=lambda r: r.start_time if r.start_time else 0)
                
                # 转换为 TraceRun
                for run in runs:
                    latency_ms = None
                    if run.end_time and run.start_time:
                        latency_ms = (run.end_time - run.start_time).total_seconds() * 1000
                    
                    trace_run = TraceRun(
                        run_id=str(run.id),
                        name=run.name,
                        run_type=run.run_type,
                        start_time=run.start_time.isoformat() if run.start_time else "",
                        end_time=run.end_time.isoformat() if run.end_time else None,
                        latency_ms=latency_ms,
                        total_tokens=run.total_tokens,
                        prompt_tokens=run.prompt_tokens,
                        completion_tokens=run.completion_tokens,
                        error=run.error,
                        inputs=run.inputs,
                        outputs=run.outputs,
                        parent_run_id=str(run.parent_run_id) if run.parent_run_id else None,
                    )
                    trace_runs.append(trace_run)
                
                logger.info(f"从 LangSmith 获取了 {len(trace_runs)} 个 trace runs，线程 {thread_id}")
            except Exception as exc:
                logger.warning(f"获取 LangSmith traces 失败：{exc}")
                # 不中断请求，继续返回消息历史
        
        # 构建 trace 树
        trace_tree = build_trace_tree(trace_runs)
        
        # 提取根节点信息（用于前端显示统计数据）
        root_run_id = None
        total_latency_ms = None
        total_tokens = None
        
        if trace_tree and len(trace_tree) > 0:
            root_run = trace_tree[0]
            root_run_id = root_run.get("run_id")
            total_latency_ms = root_run.get("latency_ms")
            
            # 汇总所有 token（递归统计所有子节点）
            def sum_tokens(node: dict) -> int:
                # 获取当前节点的 token
                tokens = 0
                if node.get("total_tokens"):
                    tokens = node["total_tokens"]
                elif node.get("prompt_tokens") or node.get("completion_tokens"):
                    # 如果没有 total_tokens，手动计算
                    tokens = (node.get("prompt_tokens") or 0) + (node.get("completion_tokens") or 0)
                
                # 递归累加所有子节点的 token
                for child in node.get("children", []):
                    tokens += sum_tokens(child)
                
                return tokens
            
            total_tokens = sum_tokens(root_run)
            
            logger.info(
                f"📊 Thread {thread_id} stats: "
                f"root_run_id={root_run_id}, "
                f"latency={total_latency_ms}ms, "
                f"tokens={total_tokens}"
            )
        
        return ThreadHistoryWithTrace(
            thread_id=thread_id,
            messages=history_messages,
            total_messages=len(history_messages),
            trace_runs=trace_runs,
            trace_tree=trace_tree,
            root_run_id=root_run_id,
            total_latency_ms=total_latency_ms,
            total_tokens=total_tokens,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Error fetching thread history with trace: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch thread history: {str(exc)}",
        ) from exc


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(thread_id: str):
    """删除指定线程的所有 checkpoint 记录。

    ✅ 流程：
    1. 获取 checkpointer 实例
    2. 调用 checkpointer.delete_thread() 删除所有 checkpoint
    3. 返回 204 No Content

    参数：
    - thread_id: 要删除的会话线程标识

    返回：
    - 204 No Content: 删除成功

    注意：
    - 删除是永久的，无法恢复
    - 会删除该 thread_id 的所有 checkpoint 记录
    """
    try:
        # 根据实际的 LangGraph checkpoint 表结构删除（4 张表）：
        # - checkpoint_writes: 存储 checkpoint 写入数据（依赖 checkpoint_id）
        # - checkpoint_blobs: 存储 checkpoint 二进制数据
        # - checkpoints: 存储 checkpoint 元数据（主表）
        # - checkpoint_migrations: 迁移版本表（不需要删除）
        from db.database import DatabaseManager
        
        pool = await DatabaseManager.get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # 按依赖顺序删除：先删除依赖表，再删除主表
                # 1. 删除 checkpoint_writes（依赖 checkpoint_id）
                await cur.execute(
                    "DELETE FROM checkpoint_writes WHERE thread_id = %s",
                    (thread_id,),
                )
                writes_deleted = cur.rowcount
                
                # 2. 删除 checkpoint_blobs
                await cur.execute(
                    "DELETE FROM checkpoint_blobs WHERE thread_id = %s",
                    (thread_id,),
                )
                blobs_deleted = cur.rowcount
                
                # 3. 删除 checkpoints（主表）
                await cur.execute(
                    "DELETE FROM checkpoints WHERE thread_id = %s",
                    (thread_id,),
                )
                checkpoints_deleted = cur.rowcount
                
                await conn.commit()
                
                logger.info(
                    f"Successfully deleted {checkpoints_deleted} checkpoints, "
                    f"{writes_deleted} checkpoint_writes, "
                    f"and {blobs_deleted} checkpoint_blobs for thread {thread_id}"
                )
        
        return None
    except Exception as exc:
        logger.exception(f"Failed to delete thread {thread_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete thread: {str(exc)}",
        )


__all__ = ["router"]

