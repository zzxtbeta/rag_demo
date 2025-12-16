## Context
本变更覆盖后端 LangGraph ReAct loop、工具层 async/错误处理、history API 过滤与前端 WebSocket 流式 UI 的一致性。

## Goals / Non-Goals
- Goals:
  - 对齐 LangGraph Quickstart 的最小 ReAct loop（模型节点 ↔ ToolNode 循环）
  - 工具层在 async/ASGI 环境稳定运行（无阻塞、无 sync/async 路径错配）
  - 实时渲染与刷新后的 history 渲染一致：每轮只展示最终 assistant 回复
  - 保持 agent 目录干净，移除未使用遗留实现
- Non-Goals:
  - 不新增额外页面/功能（例如新的 UI 面板、更多节点类型）
  - 不引入新的持久化模型或重做消息协议

## Decisions
### Decision 1: Scheme A（单模型节点 + tools 节点）
- 选择 `query_or_respond`（bind_tools）与 `tools`（ToolNode）形成回路。
- 结束条件：最后一条 AIMessage 不含 tool_calls。
- 理由：实际 trace 表明模型在 tools 之后已能直接生成最终回答，独立 `generate` 节点会造成冗余与 UI 复杂度。

### Decision 2: ToolNode 采用 async wrapper（`awrap_tool_call`）
- 使用 `awrap_tool_call` 包装工具调用错误处理，确保 ToolNode 走异步执行路径。
- 理由：避免 sync 路径触发 async-only 工具的 `NotImplementedError('StructuredTool does not support sync invocation.')`。

### Decision 3: web_search 在 async tool 内用 `asyncio.to_thread()`
- Tavily 社区工具的 `.invoke()` 为同步网络调用，在 ASGI/事件循环内可能触发阻塞检测。
- 采用 `await asyncio.to_thread(tavily_tool.invoke, {"query": query})` 规避阻塞。

### Decision 4: history 过滤兼容 BaseMessage 与 dict
- Checkpointer/序列化路径可能返回 dict 格式消息；不能只用 `isinstance(HumanMessage)` 判断 role。
- 统一按 dict 的 `role/type` 兜底识别，并维持原先“只返回 user + 最终 assistant”的接口契约。

### Decision 5: 前端实时渲染只保留最终 assistant
- Turn 组织按 userMessages 索引匹配 assistantMessages[i]；若同轮出现多条 assistant，会错误取第一条草稿。
- 通过把 token 流 assistant 绑定 nodeName，并在 query_or_respond output 上基于 `tool_calls` 回滚草稿，保证每轮只保留一个最终 assistant。

## Risks / Trade-offs
- 草稿回滚可能出现“短暂闪现”体验（取决于 token 与 output 到达顺序）。当前策略优先正确性。
- 如果未来引入更多 LLM 节点，需要扩展前端对 nodeName 的策略（当前已为 Scheme A 收敛）。

## Validation
- 实测：工具循环、web_search、history 刷新、实时 UI 最终回复渲染均正常。

## Key Files
- `src/tools/toolkit.py`: 工具注册、ToolNode 构建、async wrapper（`awrap_tool_call`）与 ToolMessage 错误回传
- `src/tools/web_search.py`: async web search + `asyncio.to_thread` 包装 Tavily 同步 `.invoke()`
- `src/agent/graph.py`: Scheme A ReAct loop（`query_or_respond` ↔ `tools`）
- `src/api/routes/chat.py`: history 输出兼容 dict/BaseMessage，稳定 role 与过滤中间消息
- `frontend/src/hooks/useChatStream.ts`: 实时渲染回滚 tool-call 草稿 assistant，保留最终回答
