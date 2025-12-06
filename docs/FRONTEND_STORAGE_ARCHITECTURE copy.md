# 前端存储架构与中间节点输出实现文档

## 目录
1. [需求概述](#需求概述)
2. [系统架构](#系统架构)
3. [存储机制](#存储机制)
4. [中间节点输出实现](#中间节点输出实现)
5. [LangSmith 集成](#langsmith-集成)
6. [未来改进方向](#未来改进方向)

---

## 需求概述

### 核心需求
1. **消息持久化**：用户发送的消息、AI 回复、以及**中间执行过程**（节点输出）都需要持久化
2. **跨会话恢复**：刷新页面后，所有历史对话和中间过程都能完整恢复
3. **实时更新**：在对话进行中，实时显示 AI 的执行步骤（工具调用、检索过程等）
4. **多线程管理**：支持多个对话线程，每个线程独立存储

### 业务场景
- 用户发送问题："象量科技这个公司如何？"
- AI 需要调用 `retrieve_context` 工具检索知识库
- 用户需要看到：
  - ✅ 用户消息："象量科技这个公司如何？"
  - ✅ **执行过程**：`query_or_respond` 节点开始 → 调用 `retrieve_context` → 检索完成
  - ✅ AI 回复：基于检索结果的回答

**关键点**：执行过程（node 消息）需要持久化，刷新页面后仍能看到这些中间步骤。

---

## 系统架构

### 整体架构图（重构后）

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (React)                         │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  ChatWindow  │  │ useChatStream│  │  WebSocket   │     │
│  │              │  │              │  │   Client     │     │
│  │  渲染消息    │←→│  状态管理    │←→│  接收Token   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                │
│                    ┌───────▼───────┐                        │
│                    │ localStorage  │                        │
│                    │  (缓存存储)   │                        │
│                    └───────────────┘                        │
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP/WebSocket
                             │
┌────────────────────────────▼─────────────────────────────────┐
│                      后端 (FastAPI)                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Chat API    │  │ LangGraph    │  │ LangSmith    │     │
│  │              │  │  Workflow    │  │  Tracing     │     │
│  │  /chat/stream│→ │  执行工作流  │→ │  自动记录    │     │
│  │  /trace      │← │              │  │  执行链路    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                │
│                    ┌───────▼───────┐                        │
│                    │  Checkpointer │                        │
│                    │  (Postgres)   │                        │
│                    └───────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### 数据流向

1. **发送消息**：
   ```
   用户输入 → 前端 sendMessage() → POST /chat/stream → 后端启动工作流
   ```

2. **实时更新**：
   ```
   LangGraph 执行 → Redis Pub/Sub → WebSocket → 前端接收 Token → 更新 UI
   LangGraph 执行 → LangSmith 自动记录 → 持久化到云端
   ```

3. **持久化**：
   ```
   前端接收 Token → setMessages() → useEffect 监听 → localStorage 缓存
   LangSmith 自动记录所有 node 执行过程 → 云端持久化
   ```

4. **恢复数据**：
   ```
   页面加载 → loadThreadHistory() → GET /chat/threads/{id}/trace → 
   从 LangSmith 获取完整执行链路 → 合并 messages 和 node 消息
   ```

---

## 存储机制

### 后端存储

#### 1. LangGraph Checkpointer（Postgres）

**存储内容**：
- ✅ User 消息（HumanMessage）
- ✅ Assistant 消息（AIMessage）
- ✅ System 消息
- ❌ **不存储** node 执行步骤

**存储位置**：
- 数据库：Postgres（通过 `PostgresSaver`）
- 表结构：由 LangGraph 自动管理
- 命名空间：`thread_id` + `user_id`（可选）

**API 端点**：
```python
GET /chat/threads/{thread_id}/history
# 返回：ThreadHistory
# {
#   "thread_id": "...",
#   "messages": [
#     {"role": "user", "content": "...", "timestamp": ...},
#     {"role": "assistant", "content": "...", "timestamp": ...}
#   ],
#   "total_messages": 2
# }
```

#### 2. LangSmith（云端持久化）⭐ **新增**

**存储内容**：
- ✅ 所有 node 执行过程（query_or_respond, tools, generate）
- ✅ Tool 调用（retrieve_context）
- ✅ LLM 调用（输入、输出、token 使用）
- ✅ 执行时间、错误信息
- ✅ Parent-child 关系（树形结构）

**存储方式**：
- **云端持久化**：LangSmith 自动记录所有执行过程
- **自动追踪**：只需设置环境变量即可启用
- **树形结构**：自动维护 parent-child 关系

**配置**：
```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_api_key
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_PROJECT=gravaity
```

**API 端点**：
```python
GET /chat/threads/{thread_id}/trace
# 返回：ThreadTrace
# {
#   "thread_id": "...",
#   "messages": [...],  # user/assistant 消息
#   "trace_tree": {     # 完整的执行链路树
#     "id": "...",
#     "name": "query_or_respond",
#     "type": "chain",
#     "children": [...]
#   },
#   "total_runs": 5
# }
```

#### 3. Redis Pub/Sub（临时，仅用于实时流式响应）

**存储内容**：
- ✅ Token 级别的流式消息（用于前端实时显示）
- ❌ **不再推送** node 事件（由 LangSmith 自动记录）

**存储方式**：
- **不持久化**：Redis Pub/Sub 是发布-订阅模式，消息发送后即消失
- 频道命名：`workflow:{thread_id}:{node_name}:token`
- 消息格式：`StreamMessage`（JSON 序列化）

**生命周期**：
- 消息发布后，如果没有订阅者，消息丢失
- 前端通过 WebSocket 实时接收 Token，但刷新后从 LangSmith 恢复

---

### 前端存储

#### 1. localStorage（浏览器本地缓存）

**存储内容**：
- ✅ 线程列表（`chat_threads`）
- ✅ 当前活跃线程（`chat_active_thread`）
- ✅ 用户选择的模型（`chat_model`）
- ✅ **消息缓存**（`chat_messages_{threadId}`）
  - User 消息
  - Assistant 消息
  - **Node 消息**（从 LangSmith trace API 获取）

**存储结构**：

```typescript
// 线程列表
localStorage.setItem("chat_threads", JSON.stringify([
  { id: "thread_xxx", title: "New Chat", lastUpdated: 1234567890 }
]));

// 当前活跃线程
localStorage.setItem("chat_active_thread", "thread_xxx");

// 消息列表（每个线程独立存储，作为缓存）
localStorage.setItem("chat_messages_thread_xxx", JSON.stringify([
  {
    id: "thread_xxx_msg_0",
    threadId: "thread_xxx",
    role: "user",
    content: "你好！",
    timestamp: 1764946696517
  },
  {
    id: "xxx_node",
    threadId: "thread_xxx",
    role: "node",
    content: '{"inputs": {...}, "outputs": {...}}',
    nodeName: "query_or_respond",
    messageType: "output",
    timestamp: 1764946697258
  },
  {
    id: "thread_xxx_msg_1",
    threadId: "thread_xxx",
    role: "assistant",
    content: "你好！很高兴为你服务...",
    timestamp: 1764946697260
  }
]));
```

**存储时机**：
- 从 LangSmith trace API 加载后自动保存（作为缓存）
- 实时接收 Token 时自动保存

**限制**：
- 浏览器存储限制：通常 5-10MB
- **仅作为缓存**：LangSmith 是真相源，localStorage 用于离线模式或快速加载

---

## 中间节点输出实现

### 后端实现

#### 1. LangSmith 自动追踪

**位置**：`src/api/app.py` → 应用启动时启用

**流程**：
```python
# 应用启动时自动启用 LangSmith 追踪
settings = get_settings()
if settings.langsmith_tracing:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
```

**关键点**：
- ✅ LangGraph 自动追踪所有 node、tool、llm 调用
- ✅ 无需代码改动，只需设置环境变量
- ✅ 自动维护 parent-child 关系

#### 2. 工作流执行与 Token 流式响应

**位置**：`src/api/routes/chat.py` → `_stream_workflow_to_redis()`

**流程**：
```python
async def _stream_workflow_to_redis(...):
    # 使用 stream_mode=["messages"] 流式执行
    async for stream_mode, chunk in graph.astream(
        payload,
        config,
        stream_mode=["messages"],  # 只使用 messages 模式
    ):
        if stream_mode == "messages":
            # 发布 token 级别的流式消息（用于前端实时显示）
            await publisher.publish_node_output(
                thread_id=thread_id,
                node_name=node_name,
                data={"token": token_content},
                message_type="token",
            )
    # Node 执行过程由 LangSmith 自动记录，无需手动推送
```

**关键点**：
- ✅ 只推送 Token 流式消息（用于前端实时显示）
- ✅ Node 执行过程由 LangSmith 自动记录
- ✅ 简化了代码，移除了复杂的 node 事件推送逻辑

#### 3. Trace API 端点

**位置**：`src/api/routes/chat.py` → `get_thread_trace()`

**流程**：
```python
@router.get("/threads/{thread_id}/trace")
async def get_thread_trace(thread_id: str):
    # 1. 从 checkpointer 获取 messages（user/assistant）
    state = await graph.aget_state(config)
    messages = state.values.get("messages", [])
    
    # 2. 从 LangSmith 查询该 thread_id 的所有 runs
    client = Client(api_key=settings.langsmith_api_key)
    runs = client.list_runs(
        project_name=settings.langsmith_project,
        filter=f'eq(metadata_value, "{thread_id}")'
    )
    
    # 3. 构建树形结构（parent-child 关系）
    trace_tree = build_trace_tree(runs)
    
    # 4. 返回完整的执行链路
    return ThreadTrace(
        thread_id=thread_id,
        messages=history_messages,
        trace_tree=trace_tree,
        total_runs=len(runs)
    )
```

---

### 前端实现

#### 1. WebSocket 连接与 Token 接收

**位置**：`frontend/src/hooks/useChatStream.ts` → `attachWebSocket()`

**实现**：
```typescript
const attachWebSocket = useCallback((threadId: string) => {
  const ws = new WebSocket(`ws://localhost:8000/ws/${threadId}`);
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const { message_type, data: rawData } = data;
    
    if (message_type === "token") {
      // Token 流式消息：追加到 assistant 消息
      const token = rawData.token || "";
      setMessages(prev => {
        const lastMsg = prev[prev.length - 1];
        if (lastMsg?.role === "assistant") {
          return prev.map((msg, idx) =>
            idx === prev.length - 1
              ? { ...msg, content: msg.content + token }
              : msg
          );
        } else {
          return [...prev, {
            role: "assistant",
            content: token,
            timestamp: Date.now()
          }];
        }
      });
    }
    // 注意：node 消息现在由 LangSmith 自动记录，刷新后从 trace API 获取
  };
}, []);
```

**关键点**：
- ✅ WebSocket 只处理 Token 流式消息（用于实时显示）
- ✅ Node 消息不再通过 WebSocket 推送
- ✅ 刷新后从 LangSmith trace API 获取完整执行链路

#### 2. 消息恢复与 Trace 加载

**位置**：`frontend/src/hooks/useChatStream.ts` → `loadThreadHistory()`

**流程**：
```typescript
const loadThreadHistory = async (threadId: string) => {
  try {
    // 1. 从 LangSmith trace API 获取完整的执行链路
    const traceResponse = await fetch(`/chat/threads/${threadId}/trace`);
    const traceData = await traceResponse.json();
    
    // 2. 提取 messages（user/assistant）
    const historyMessages = traceData.messages.map((msg, index) => ({
      id: `${threadId}_msg_${index}`,
      role: msg.role,
      content: msg.content,
      timestamp: msg.timestamp * 1000, // 转换为毫秒
    }));
    
    // 3. 从 trace_tree 提取 node 消息
    const nodeMessages = flattenTraceTree(traceData.trace_tree, threadId);
    
    // 4. 合并并排序
    const allMessages = [
      ...historyMessages,
      ...nodeMessages,
    ].sort((a, b) => a.timestamp - b.timestamp);
    
    setMessages(allMessages);
    saveMessagesToStorage(threadId, allMessages); // 保存到缓存
  } catch (error) {
    // Fallback: 从 localStorage 加载（离线模式）
    const localMessages = loadMessagesFromStorage(threadId);
    setMessages(localMessages);
  }
};

// 将 trace_tree 转换为 node 消息
function flattenTraceTree(node: TraceNode, threadId: string): ChatMessage[] {
  const messages: ChatMessage[] = [];
  
  // 递归处理子节点
  if (node.children) {
    for (const child of node.children) {
      messages.push(...flattenTraceTree(child, threadId));
    }
  }
  
  // 将当前节点转换为 node 消息
  if (node.type && node.name) {
    messages.push({
      id: `${node.id}_node`,
      threadId: threadId,
      role: "node",
      content: JSON.stringify({
        inputs: node.inputs,
        outputs: node.outputs,
        duration_ms: node.duration_ms,
      }, null, 2),
      nodeName: node.name,
      messageType: "output",
      timestamp: new Date(node.start_time).getTime(),
    });
  }
  
  return messages;
}
```

**关键点**：
- ✅ **LangSmith 是真相源**：刷新后从 trace API 获取完整执行链路
- ✅ localStorage 仅作为缓存：用于离线模式或快速加载
- ✅ 简化了合并逻辑：不再需要复杂的去重和合并策略

#### 3. 消息组织与渲染

**位置**：`frontend/src/components/ChatWindow.tsx` → `useMemo(() => {...})`

**流程**：
```typescript
const turns = useMemo(() => {
  // 1. 按时间戳排序
  const sortedMessages = [...messages].sort((a, b) => a.timestamp - b.timestamp);
  
  // 2. 建立 user 消息到 turn 的映射
  const userMessageTurns = new Map();
  for (const msg of sortedMessages) {
    if (msg.role === "user") {
      userMessageTurns.set(msg.id, {
        userMessage: msg,
        nodeSteps: [],
        assistantMessage: null,
      });
    } else if (msg.role === "assistant") {
      // 关联到最近的 user 消息
      // ...
    }
  }
  
  // 3. 关联 node 消息到对应的 user 消息
  for (const msg of sortedMessages) {
    if (msg.role === "node") {
      // 找到最近的、时间戳小于 node 消息的 user 消息
      // ...
    }
  }
  
  return Array.from(userMessageTurns.values()).sort(
    (a, b) => a.userMessage.timestamp - b.userMessage.timestamp
  );
}, [messages]);
```

**关键点**：
- ✅ 使用两遍扫描：先处理 user/assistant，再处理 node
- ✅ 通过时间戳关联 node 消息到对应的 user 消息
- ✅ 如果时间戳有问题，使用 fallback 策略

---

## LangSmith 集成

### 配置

**环境变量**：
```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_api_key
# 或使用 LANGCHAIN_API_KEY（兼容）
LANGCHAIN_API_KEY=your_api_key
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_PROJECT=gravaity
```

**后端配置**：
- `src/config/settings.py`：添加 LangSmith 配置项
- `src/api/app.py`：应用启动时自动启用追踪

**依赖**：
- `langsmith>=0.2.4`：已添加到 `pyproject.toml`

### 优势

1. **自动追踪**：无需代码改动，只需设置环境变量
2. **完整记录**：记录所有 node、tool、llm 调用
3. **树形结构**：自动维护 parent-child 关系
4. **云端持久化**：跨设备、长期保留
5. **可视化界面**：LangSmith UI 提供完整的执行链路可视化

### 使用方式

1. **查看执行链路**：
   - 访问 LangSmith UI：https://smith.langchain.com
   - 选择项目：`gravaity`
   - 查看每个 thread 的完整执行链路

2. **前端获取执行链路**：
   ```typescript
   const response = await fetch(`/chat/threads/${threadId}/trace`);
   const { messages, trace_tree } = await response.json();
   ```

---

## 未来改进方向

### 短期改进（已完成）

1. ✅ **LangSmith 集成**：自动追踪所有执行过程
2. ✅ **简化架构**：移除复杂的 Redis node 事件推送
3. ✅ **Trace API**：提供完整的执行链路查询接口
4. ✅ **前端重构**：从 LangSmith API 获取执行链路

### 中期改进（1-2 月）

1. **增量同步**：只同步新增消息，而不是全量加载
2. **压缩存储**：压缩 localStorage 中的数据，节省空间
3. **离线支持**：使用 IndexedDB 替代 localStorage，支持更大数据量
4. **错误处理**：更好的错误处理和重试机制

### 长期改进（3-6 月）

1. **消息搜索**：支持搜索历史消息和 node 输出
2. **消息导出**：支持导出对话历史（包括 node 消息）
3. **性能优化**：优化 trace API 查询性能
4. **多设备同步**：支持多设备间同步消息（需要后端支持）

---

## 附录

### 相关文件

- **前端**：
  - `frontend/src/hooks/useChatStream.ts` - 消息状态管理和存储
  - `frontend/src/components/ChatWindow.tsx` - 消息渲染和组织
  - `frontend/src/types.ts` - 消息类型定义

- **后端**：
  - `src/api/routes/chat.py` - 聊天 API 和 trace API
  - `src/api/routes/stream.py` - WebSocket 代理
  - `src/infra/redis_pubsub.py` - Redis 发布器（仅用于 Token 流式响应）
  - `src/agent/graph.py` - LangGraph 工作流
  - `src/config/settings.py` - LangSmith 配置

### 调试工具

- **浏览器 Console**：查看 `[DEBUG]` 日志
- **LangSmith UI**：查看完整的执行链路
- **localStorage 检查**：
  ```javascript
  // 查看所有消息
  Object.keys(localStorage).filter(k => k.startsWith('chat_messages_'))
  
  // 查看特定线程的消息
  JSON.parse(localStorage.getItem('chat_messages_thread_xxx'))
  ```

### 常见问题

1. **Q: 刷新后 node 消息丢失？**
   - A: 检查 LangSmith 配置是否正确，查看 trace API 是否返回数据

2. **Q: node 消息关联到错误的 user 消息？**
   - A: 检查时间戳是否正确，查看 `[DEBUG ChatWindow]` 日志

3. **Q: trace API 返回空数据？**
   - A: 检查 LangSmith 环境变量配置，确保 `LANGSMITH_TRACING=true`

---

**文档版本**：v2.0  
**最后更新**：2025-01-XX  
**维护者**：开发团队
