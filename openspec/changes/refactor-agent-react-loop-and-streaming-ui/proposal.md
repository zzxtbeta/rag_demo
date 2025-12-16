# Change: Refactor agent ReAct loop + streaming UI consistency

## Why
- 之前的图结构不是完整的 ReAct 循环（缺少 `tools -> llm(with tools)` 回边），导致只能一轮工具调用或出现冗余的 `generate` 节点。
- 工具层存在 sync/async 路径混用风险：async-only 工具在同步调用路径会触发 `StructuredTool does not support sync invocation`；同时 ASGI 环境下同步网络调用会触发阻塞检测。
- 前端实时渲染在“同一轮出现多条 assistant（草稿 + 最终答案）”时，会因 Turn 组织逻辑按索引取第一条 assistant 而显示错误，需要在实时流中只保留最终回复。
- 刷新后 history 重建曾出现 role 误判（序列化 dict 消息被当作 assistant），导致历史渲染错乱。

## What Changes
### Backend
- 将 Agent 工作流收敛为 Quickstart 对齐的最小 ReAct loop（Scheme A）：`query_or_respond <-> tools`，直到不再产生 `tool_calls` 结束。
- 引入工具注册与 ToolNode 构建的统一入口（按 request 开关启用 websearch），并接入官方风格的工具错误处理：异常转为 `ToolMessage(..., tool_call_id=...)` 反馈给模型。
- 修复 ASGI 下的阻塞调用：将 Tavily web search 以 async tool 形式封装，并对同步 `.invoke()` 使用 `asyncio.to_thread()`。
- 修复 `/chat/threads/{thread_id}/history`：兼容 checkpointer 返回的 dict 序列化消息，正确识别 user/assistant/tool/system，并过滤中间 tool 调用阶段的 AI 消息。

#### Key Files (Backend)
- `src/tools/toolkit.py`
  - 统一工具清单：区分“模型可见工具”（按 `enable_websearch` 动态）与 “ToolNode 全量工具”（编译期 superset）
  - ToolNode 统一构造：固定 `messages_key`，并接入工具错误处理 wrapper
  - Async 兼容：使用 `awrap_tool_call`，避免 ToolNode 走 sync 路径导致 async-only 工具报错
- `src/tools/web_search.py`
  - `web_search` 为 async tool；对 Tavily 同步 `.invoke()` 使用 `asyncio.to_thread()` 避免阻塞
- `src/agent/graph.py`
  - Scheme A 循环：`query_or_respond` ↔ `tools`，移除冗余 `generate`
- `src/api/routes/chat.py`
  - history：兼容 BaseMessage/dict 两种消息形态，稳定输出 role 并过滤中间 tool-call 消息

### Frontend
- 修复实时聊天渲染：当 `query_or_respond` 首次输出是“将调用工具”的草稿 assistant 时，不应被当作最终回复。
- 实现策略：token 流生成的 assistant 带上 `nodeName`；在收到 `query_or_respond` output 时，若该次 AIMessage 含 `tool_calls`，回滚本轮草稿 assistant；若不含 `tool_calls`，确保本轮只保留一个最终 assistant（必要时用 output 的完整 content 覆盖 token 拼接内容）。

#### Key Files (Frontend)
- `frontend/src/hooks/useChatStream.ts`
  - 修复实时渲染：识别并回滚“工具调用草稿 assistant”，保证每轮只保留最终 assistant

### Docs / Cleanup
- 将本次实战结论补充到文档：ToolNode 的 async wrapper（`awrap_tool_call`）与 ASGI blocking 规避（`asyncio.to_thread`）。
- 清理 `src/agent/` 目录中未使用的遗留内容（未被当前运行路径依赖的 prompt 常量、旧 PDF loader/indexer/retriever 方法、未用 import）。

## Impact
- 影响范围：后端 agent/workflow、工具层、history API、前端 WebSocket 流式渲染。
- 行为变化：实时 UI 不再显示“工具调用意图草稿”，只显示最终回答；历史渲染角色与过滤规则更稳定。

## Implementation Status
- ✅ 已实现并在本地验证：
  - 工具循环可正常执行，多 tool_calls 可在一次 tools 节点批量执行。
  - web_search 不再触发 ASGI 阻塞错误。
  - 刷新后 history 渲染恢复正常；实时渲染可正确显示最终回答。
