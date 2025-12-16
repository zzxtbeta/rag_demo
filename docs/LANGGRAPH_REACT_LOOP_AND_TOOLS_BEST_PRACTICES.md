# LangGraph / LangChain：工具使用、ReAct 循环、Runtime 与错误处理（基于官方文档的最小改动建议）

> 依据并严格限定于以下三份官方文档（只在这些文档明确说明的范围内提出建议）：
> - LangChain Tools：https://docs.langchain.com/oss/python/langchain/tools#tools
> - LangGraph Quickstart（Full code example）：https://docs.langchain.com/oss/python/langgraph/quickstart#full-code-example
> - LangChain Agents（Example of ReAct loop）：https://docs.langchain.com/oss/python/langchain/agents#example-of-react-loop

本文目标：对照你当前的图实现（见 [src/agent/graph.py](../src/agent/graph.py)），用官方文档的“工具调用循环 / ReAct loop / runtime 注入 / 工具错误处理”的说明，给出一个**必要且最小**的完善方案（避免引入评分、重写、额外页面等冗余操作）。

---

## 1. 官方文档的关键事实（直接影响架构选择）

### 1.1 ReAct 循环的本质：模型 ↔ 工具 的多轮交替

在 Agents 文档中，ReAct 被描述为：代理在“简短推理 → 发起工具调用 → 接收观察（tool result）→ 继续决策”之间交替，直到能输出最终答案。
- 文档用“Reasoning + Acting”描述这种循环，并给出了连续两次工具调用（先搜索再查库存）的示例。

这意味着：
- **工具调用不是一次性的步骤**；当模型在看到工具结果后仍认为需要更多信息，它会继续发起下一轮 tool call。
- 运行时需要一个“循环机制”，让工具结果（ToolMessage）回流到下一次模型调用。

### 1.1.1 一次产生多个 tool_calls 是合理的

在 Agents 文档对 Tools 的说明中，明确提到 Agent 能做到：
- “Multiple tool calls in sequence (triggered by a single prompt)”
- “Parallel tool calls when appropriate”

因此你在 trace 里看到：同一个 `AIMessage` 一次性给出两个 tool_calls（比如先查项目、再查天气）是合理且常见的行为。
在 LangGraph 侧，这通常意味着 ToolNode 会在一次 tools 节点执行中处理这一批 tool_calls。

### 1.2 LangGraph Quickstart 的“循环执行图”是权威模板

LangGraph Quickstart 的 Full code example 明确给出了一个最小 agent loop 的图结构：
- 一个模型节点 `llm_call`：调用 `model_with_tools.invoke(...)`，由模型决定是否产生 `tool_calls`
- 一个工具节点 `tool_node`：执行 `state["messages"][-1].tool_calls`，把结果作为 `ToolMessage(..., tool_call_id=...)` 追加进消息列表
- 一个结束逻辑 `should_continue`：如果最后一条消息包含 `tool_calls` 则去工具节点，否则 `END`
- 一条关键回边：`tool_node -> llm_call`

Quickstart 代码中，循环的关键点是：
- `should_continue` 只判断“最后消息是否有 tool_calls”
- 工具节点的输出必须是 ToolMessage，且**携带 tool_call_id**，用于把工具结果与对应的 tool call 关联

结论：如果你希望你的 RAG 支持“多轮检索/多轮工具调用”，你的图至少要具备 Quickstart 这种“工具执行后回到模型节点”的回路。

### 1.3 Tools 文档：ToolRuntime 是官方推荐的 runtime 注入方式

Tools 文档强调：
- 工具是带 schema 的 callable（`@tool` 装饰器 + 类型标注 + docstring 作为描述）
- 一些参数名是保留字（`config`、`runtime`），用于框架内部注入；把它们当作普通业务参数会触发运行时报错
- 若要访问运行时信息，应使用 `ToolRuntime` 参数：它**不会暴露给模型**，但能访问：state、context、store、stream_writer、config、tool_call_id 等
- 若工具里使用 `runtime.stream_writer`，工具必须在 LangGraph 执行上下文中被调用

结论：
- 对需要读取/写入状态、长程记忆、流式更新的工具，应优先采用 `ToolRuntime` 注入模式，而不是全局变量或把上下文塞进 tool args。

### 1.4 Agents 文档：工具错误处理要“回传 ToolMessage 给模型”

Agents 文档提供了一个明确的错误处理方式：
- 使用 `@wrap_tool_call` 装饰器创建 middleware
- 在 middleware 内捕获异常并返回 `ToolMessage(content=..., tool_call_id=request.tool_call["id"])`

结论：
- 工具失败时，不是简单 raise 让运行崩掉；而是把错误作为 ToolMessage 回给模型，让模型在 ReAct loop 中做下一步决策（例如改参数、换工具、或改成向用户澄清）。

---

## 2. 对照你当前实现：哪里符合官方、哪里会限制能力

### 2.1 你当前的图结构（简述）

你的 [src/agent/graph.py](../src/agent/graph.py) 当前路径是：
- `query_or_respond`（模型 + bind_tools）
- `tools`（ToolNode）
- `generate`（模型不 bind_tools）
- `END`

并通过 `tools_condition` 从 `query_or_respond` 分流：
- 有 tool_calls -> `tools`
- 无 tool_calls -> `END`

### 2.2 关键差异：你现在没有 Quickstart 的“回边”，所以不是 ReAct loop

按照 Quickstart 的 Full code example，真正的 tool loop 需要：
- `tool_node -> llm_call` 回边

而你现在：
- `tools -> generate -> END`

这会导致：
- **最多只能执行一轮工具调用**（一次 ToolNode 批次），然后直接进入生成结束。
- 这与 Agents 文档描述的 ReAct（多轮工具调用）不一致。

如果你的目标是“简化但仍保留 ReAct/循环能力”，那么最小改动应当是把 `tools` 的输出回流到“带 tools 的模型节点”再判断是否继续。

---

## 3. 最小改动的完善方案（严格按官方模板收敛）

下面给出两种方案，都符合 Quickstart 的循环结构；区别是你是否坚持保留独立的 `generate` 节点。

### 方案 A（最贴近官方、改动最少）：只保留一个模型节点 + 工具节点，模型自己输出最终答案

- 模型节点：始终是 `model_with_tools`（即 bind_tools 后的模型）
- 工具节点：ToolNode 或者你自定义的 tool_node（Quickstart 手写版）
- 回边：`tools -> query_or_respond`
- 结束：在模型节点后判断 tool_calls（可用 `tools_condition` 或 Quickstart 的 should_continue）

优点：
- 完全对齐 Quickstart 的“循环执行”范式
- 最少节点、最少状态字段

代价：
- 你不再有“单独生成阶段”；最终回答由同一个模型节点产生

### 方案 B（保留两段式回答，但仍支持循环）：循环完成后再进入 generate

- 节点 1：`query_or_respond`（bind_tools）
- 节点 2：`tools`（ToolNode）
- 节点 3：`generate`（不 bind_tools）

关键边：
- `query_or_respond` -> conditional（有 tool_calls 则进入 tools，否则进入 generate 或 END）
- `tools -> query_or_respond`（回边，用于下一轮 ReAct）
- 当 `query_or_respond` 产出“无 tool_calls 的 AIMessage”时，再进入 `generate`（最终整合输出）

优点：
- 你仍保留“检索/工具使用阶段”和“最终生成阶段”的职责分离

注意：
- 这会比方案 A 多一个节点与一条分流，但仍属于“必要改动”，因为它保留了你原本的两段式意图。

---

## 3.1 本仓库当前选择：采用方案 A

基于你提供的 trace 观察：
- `query_or_respond` 在 tools 之后已经会根据 ToolMessage 继续生成最终回答
- 因此 `generate` 节点在该行为下会产生重复/冗余

当前代码已收敛为方案 A：
- `query_or_respond`（bind_tools 的模型节点）
- `tools`（ToolNode 执行 tool_calls）
- 形成回路：`tools -> query_or_respond`
- 当模型不再产生 `tool_calls`，图结束并直接输出最终 `AIMessage`

---

## 4. State 的最佳实践（按 Quickstart 的 TypedDict 写法）

你给的参考：

```python
from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
import operator

class MessagesState(TypedDict):
	messages: Annotated[list[AnyMessage], operator.add]
	llm_calls: int
```

这与 Quickstart 的 Full code example 是一致的：
- `messages: Annotated[list[AnyMessage], operator.add]`
- `llm_calls: int` 并在模型节点里做 `state.get('llm_calls', 0) + 1`

建议（仍是最小集合）：
- 保留 `messages` + `llm_calls` 两个字段即可
- 其余你之前提到的复杂字段（sources、research_loop_count 等）只有在你真的实现多分支研究循环时才引入

补充说明（面向“只放重要参数”）：
- **短期对话/推理需要的内容**：放进 state（例如 `messages`，以及你想观测的计数器如 `llm_calls`）
- **不会随对话演化、属于运行配置的内容**：不要放 state，应该走 `RunnableConfig`（例如 `chat_model`、`enable_websearch`）
- **跨会话的长期信息**：优先用 store/DB（而不是塞进 state），避免 state 变成“不可控的大对象”

---

## 5. 工具定义与 runtime（按 Tools 文档约束）

### 5.1 工具 schema 与描述

Tools 文档强调：
- 类型标注定义输入 schema
- docstring 会成为 tool description，影响模型什么时候用工具

因此你的工具应确保：
- 类型标注完整
- docstring 清晰、短且可操作（不要把策略写得过长导致模型迷失）

### 5.2 避免保留参数名冲突

Tools 文档列出了保留参数名：`config`、`runtime`。
- 这些名称不能作为“普通 tool args”使用，否则会触发运行时错误

如果你需要给工具注入上下文/状态：
- 使用 `ToolRuntime` 参数（文档明确该参数不会暴露给模型），而不是把业务上下文做成字符串/JSON 传进 query。

### 5.3 使用 ToolRuntime 的场景

Tools 文档明确 ToolRuntime 可访问：
- State（如 messages）
- Context（如 user_id、session 等不可变信息）
- Store（长程记忆）
- Stream Writer（工具执行过程中的自定义 streaming）
- Config（RunnableConfig）
- Tool Call ID

如果你后续要做：
- “工具在执行时往前端实时汇报进度”
- “工具需要读写 store（例如缓存检索结果/用户偏好）”

按 Tools 文档，应走 ToolRuntime 注入。

---

## 6. 工具错误处理（按 Agents 文档的 middleware 方式）

Agents 文档的 Tool error handling 推荐做法是：
- 用 `@wrap_tool_call` 创建 middleware
- 捕获工具异常并返回 `ToolMessage`（带 tool_call_id）

这能保证：
- 错误信息进入消息流
- 模型能在下一轮 ReAct 中“看见错误并调整动作”，而不是直接崩溃

你可以把这作为“全局默认的工具错误处理策略”，并保持 message 内容简短、可执行（例如提示用户补充必要参数，或让模型尝试更保守的查询）。

在本仓库中，我们将这一模式接入 ToolNode 的 `wrap_tool_call`：
- 目标行为与文档一致：工具异常时返回 `ToolMessage(..., tool_call_id=...)` 回到模型
- 这样不会因为单次工具失败导致整条图崩溃，模型仍可继续下一轮决策（换参数/换工具/向用户澄清）

### 6.1 本仓库的“异步工具 + ToolNode”注意事项（实战补充）

这部分是对官方“工具错误处理”示例的工程化落地注意点：目标不变（异常 -> `ToolMessage`），但需要避免 sync/async 混用导致的运行时错误。

我们踩到的典型问题：
- `NotImplementedError('StructuredTool does not support sync invocation.')`：说明 ToolNode 走了同步调用路径，但你的工具是 async-only。
- ASGI / LangGraph dev 的阻塞检测（例如 `BlockingError`）：说明你在 async 执行上下文里做了阻塞网络调用（常见于某些社区工具的 `.invoke()`）。

本仓库的修复策略：
- ToolNode 侧：用 **async wrapper**（`awrap_tool_call`）而不是 sync 的 `wrap_tool_call`，确保工具调用走异步路径，从而兼容 async tools。
- 工具实现侧：对“只提供 sync `.invoke()` 的网络工具”，在 async tool 内用 `await asyncio.to_thread(...)` 包装，避免阻塞事件循环。

官方参考（错误处理的核心模式）：
- “Handling tool errors” 示例强调：捕获异常并返回 `ToolMessage(content=..., tool_call_id=request.tool_call["id"])`（可用 `@wrap_tool_call` middleware 或 ToolNode 的错误处理配置）。

本仓库对应实现位置：
- ToolNode wrapper：见 [src/tools/toolkit.py](../src/tools/toolkit.py)
- Tavily web search 异步封装：见 [src/tools/web_search.py](../src/tools/web_search.py)

---

## 9. 本仓库：参数与配置在哪里控制？是否需要 agent/configuration.py？

按“最小必要”原则，目前有三类参数来源：

1) **环境/静态配置（启动时确定）**：见 `config/settings.py`（由环境变量加载）。
- 例如：默认 `CHAT_MODEL`、Tavily key、项目搜索开关等。

2) **每次调用的运行参数（request-level）**：通过 `RunnableConfig` 的 `configurable` 传入。
- 例如：`chat_model`、`enable_websearch`。
- 在 API 里组装位置：聊天接口会构造 `config = {"configurable": {...}}`，然后传给 `graph.astream(...)`。

3) **图编译期依赖（基础设施）**：通过 `build_graph(checkpointer=..., store=...)` 传入。
- 本仓库在 FastAPI lifespan 中初始化并注入（比如 checkpointer）。

是否需要 `agent/configuration.py`：
- **不强制需要**：如果你只需要少量 runtime 参数（`chat_model`、`enable_websearch`），直接从 `config["configurable"]` 读取即可。
- **什么时候值得加**：当 runtime 参数变多、你希望统一默认值/类型校验/描述文档时，再引入一个轻量的配置解析器会更清晰。

---

## 7. 对你当前代码的“必要改动清单”（不引入冗余）

如果你要对齐官方 ReAct/循环能力，并提升运行时与错误处理的确定性，按上文可归结为：

1. 让图形成 Quickstart 结构的回路：工具节点执行后回到“带 tools 的模型节点”，直到模型不再产生 tool_calls。
2. State 采用 Quickstart 的 TypedDict 写法：`messages + llm_calls` 即可。
3. 工具错误处理：按 Agents 文档用 `@wrap_tool_call` middleware，把异常转成 ToolMessage（保留 tool_call_id）。
4. 工具 runtime：按 Tools 文档使用 ToolRuntime 注入，避免把 `config/runtime` 当成普通参数名。

---

## 8. 不在本文范围内的点（避免“自己编造”）

以下内容虽然常见，但不在你指定的三份文档中作为“本次的硬性依据”逐条展开：
- 具体的“并行工具调用开关/参数”（通常属于模型或 bind_tools 的细节）
- ToolNode 的实现细节（并发策略、超时策略）
- LangGraph 的 retry / recursion limit 等更底层的 runtime 机制

如你希望，我可以在下一轮基于你同意的额外官方页面（例如 Models / common-errors / thinking-in-langgraph 等）再补充这些内容。