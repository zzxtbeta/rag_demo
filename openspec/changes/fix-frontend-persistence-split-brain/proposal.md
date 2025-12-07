# 修复前端消息持久化与“脑裂”问题提案

## 1. 背景与问题 (Background & Problem)

在 RAG 系统的开发过程中，我们遇到了严重的前端状态一致性问题。用户在刷新页面后，会观察到以下现象：
1.  **消息重复**：同一条对话内容出现两次。
2.  **Timeline 丢失**：原本展示的“执行过程”（Node Timeline，如检索、思考过程）在刷新后消失，只剩下最终的问答文本。
3.  **排序混乱**：消息的时间顺序可能错乱。

### 根本原因分析 (Root Cause Analysis)

这是一个典型的分布式系统中的“脑裂”（Split Brain）问题，源于我们维护了两个不一致的数据源：

1.  **前端 LocalStorage (过程数据)**：
    *   存储了流式接收到的实时事件（`NodeStart`, `NodeOutput`, `Token`）。
    *   包含丰富的执行细节（Timeline）。
    *   ID 由前端生成（基于时间戳）。
    *   时间戳是客户端本地时间。

2.  **后端 PostgresSaver (结果数据)**：
    *   存储了 LangGraph 的 Checkpoint（State）。
    *   只包含最终的 LangChain 消息对象（`HumanMessage`, `AIMessage`）。
    *   **丢失了过程事件**（Checkpoint 不存储“节点开始”这种瞬时状态）。
    *   ID 在读取时动态生成或基于 UUID。
    *   时间戳在读取时可能动态计算。

当用户刷新页面时，前端试图将 LocalStorage 的“过程数据”与后端返回的“结果数据”进行合并。由于 ID 格式不同（`1765..._user` vs `thread_..._history_0`）且时间戳不一致，去重逻辑失效，导致数据重复；同时，由于后端不返回过程事件，Timeline 无法从后端数据中恢复。

## 2. 设计方案 (Design Proposal)

为了彻底解决此问题，我们采用 **"单一事实来源" (Single Source of Truth)** + **"历史重构" (History Reconstruction)** 的设计模式。

### 2.1 核心原则

1.  **后端为主**：后端数据库（LangGraph Checkpoint）是唯一可信的历史数据源。
2.  **前端无状态化**：前端不再依赖 LocalStorage 持久化历史消息，LocalStorage 仅用于存储用户偏好或草稿。
3.  **过程合成 (Process Synthesis)**：既然后端只存“结果”（消息），前端负责根据“结果”反推“过程”（Timeline）。

### 2.2 LangGraph 与前后端交互原理

*   **LangGraph Checkpoint 机制**：
    LangGraph 使用 `PostgresSaver` 在每个节点（Node）执行完毕后保存状态（State）。状态中主要包含的是 `messages` 列表。它**不保存**流式传输过程中的 `on_chat_model_stream` 事件。因此，直接从 Checkpoint 读取只能得到对话的“快照”。

*   **Timeline 重构逻辑**：
    虽然 Checkpoint 丢失了瞬时事件，但我们可以通过消息类型推断出发生了什么：
    *   如果存在一条 `AIMessage`，说明 `query_or_respond`（LLM 节点）一定执行过，并且成功输出了。
    *   如果存在一条 `ToolMessage`，说明 `tools`（工具节点）一定执行过。
    *   如果 `AIMessage` 中包含 `tool_calls`，说明 LLM 决定了要调用工具。

### 2.3 详细设计

#### 后端变更 (Backend)

1.  **Schema 升级**：
    扩展 `HistoryMessage` 对象，使其具备完整的 LangChain 消息保真度。
    *   新增 `type`: 区分 `human`, `ai`, `tool`, `system`。
    *   新增 `tool_calls`: 存储 AI 的工具调用意图。
    *   新增 `id`: 提供稳定的、确定性的唯一标识符。

2.  **API 增强**：
    修改 `GET /threads/{thread_id}/history` 接口：
    *   **不再过滤 ToolMessage**：之前为了简洁隐藏了工具消息，现在为了重构 Timeline，必须返回。
    *   **生成稳定 ID**：如果消息本身没有 ID，基于 `thread_id` + `index` 生成确定性 ID，确保多次请求 ID 一致。

#### 前端变更 (Frontend)

1.  **移除合并逻辑**：删除复杂的 LocalStorage 与 API 数据合并/去重代码。
2.  **合成 Timeline (Synthesizing Timeline)**：
    在接收到后端历史列表后，遍历消息并动态插入“伪造”的节点事件：
    *   遇到 `assistant` (AI) 消息 -> 插入 `NodeStart(query_or_respond)` 和 `NodeOutput(query_or_respond)`。
    *   遇到 `tool` 消息 -> 插入 `NodeStart(tool_name)` 和 `NodeOutput(tool_name)`。
    *   通过微调时间戳（如 `timestamp - 10ms`）确保这些合成事件在 Timeline 中正确排序。

## 3. 优势 (Benefits)

*   **鲁棒性 (Robustness)**：无论刷新多少次，Timeline 都能完美复原，且与后端数据严格一致。
*   **简洁性 (Simplicity)**：消除了复杂且容易出错的前端去重逻辑。
*   **可维护性 (Maintainability)**：遵循单一数据源原则，Debug 更加容易（只需看后端返回什么）。

## 4. 局限性 (Limitations)

*   **精度损失**：重构的 Timeline 中，节点的“执行时间”是模拟的，而非真实的耗时。但对于用户回顾历史来说，这通常不重要。
*   **流式中断**：如果在流式输出过程中刷新页面，正在生成的那条消息可能会丢失（因为它还没存入 Checkpoint），只能恢复到上一个完整的 Checkpoint。这是 HTTP/WebSocket 的物理限制。
