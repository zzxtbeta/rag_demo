# LangGraph Memory Store 设计文档

**参考文档**: https://docs.langchain.com/oss/python/langchain/long-term-memory

## 核心概念

LangGraph Memory Store 用于**跨线程(thread)的长期记忆存储**,与 RAG 文档检索完全独立!

## 两种记忆类型

### 1. 短期记忆 (Short-term Memory)
- **作用域**: 单个线程 (thread)
- **实现**: LangGraph State + Checkpointer
- **用途**: 当前对话的消息历史
- **持久化**: 存储在 checkpoint 数据库

### 2. 长期记忆 (Long-term Memory)
- **作用域**: 跨所有线程
- **实现**: LangGraph Store (BaseStore)
- **用途**: 用户偏好、历史信息等
- **持久化**: 独立的 Store 数据库

## Memory Store vs RAG Vector Store

| 对比项 | Memory Store | RAG Vector Store |
|--------|--------------|------------------|
| **用途** | 用户记忆存储 | 文档知识库检索 |
| **作用域** | 跨线程 (所有对话) | 无状态 (所有用户共享) |
| **数据类型** | JSON 文档 (用户信息) | 文档分块 (PDF、Web等) |
| **命名空间** | `("users", user_id)` | `collection_name` |
| **访问方式** | `runtime.store.get/put/search` | `vector_store.similarity_search` |
| **嵌入配置** | `langgraph.json` 配置 | 代码中初始化 |
| **检索目的** | 获取用户偏好 | 获取相关知识 |

## Memory Store 架构

```
用户 A (user_123)
  ├─ Thread 1: 对话 1
  ├─ Thread 2: 对话 2
  └─ Thread 3: 对话 3
       ↑
       所有线程共享访问
       ↓
  Memory Store
    ("users", "user_123") → {
      "name": "张三",
      "preferences": "喜欢简洁回答",
      "language": "中文"
    }
```

## 实现步骤

### 1. 配置 langgraph.json

```json
{
  "store": {
    "index": {
      "dims": 3072,
      "embed": "openai:text-embedding-3-large",
      "embed_kwargs": {
        "openai_api_key": "${OPENAI_EMBEDDINGS_API_KEY}",
        "openai_api_base": "${LITELLM_BASE_URL}"
      }
    }
  }
}
```

**关键点**:
- `dims`: 嵌入维度 (text-embedding-3-large 是 3072)
- `embed`: 嵌入模型标识符
- `embed_kwargs`: API 配置 (支持自定义 base_url)

### 2. 在工具中访问 Store

```python
from langchain.tools import tool, ToolRuntime
from dataclasses import dataclass

@dataclass
class Context:
    user_id: str

@tool
def get_user_preferences(runtime: ToolRuntime[Context]) -> str:
    """获取用户偏好设置."""
    user_id = runtime.context.user_id
    
    # ✅ 通过 runtime.store 访问
    store = runtime.store
    
    # 从 store 读取用户信息
    user_info = store.get(("users",), user_id)
    
    if user_info:
        return user_info.value["preferences"]
    else:
        return "未找到用户偏好"

@tool
def save_user_preference(preference: str, runtime: ToolRuntime[Context]):
    """保存用户偏好."""
    user_id = runtime.context.user_id
    
    # 写入 store
    runtime.store.put(
        ("users",),  # 命名空间
        user_id,     # 键
        {"preferences": preference}  # 值
    )
```

### 3. 在 Graph 节点中访问 Store

```python
async def call_model(state: State, runtime: Runtime[Context]) -> dict:
    """调用模型,同时检索用户记忆."""
    user_id = runtime.context.user_id
    
    # ✅ 语义搜索用户记忆
    memories = await runtime.store.asearch(
        ("users", user_id),  # 命名空间
        query="用户的语言偏好",  # 搜索查询
        limit=5
    )
    
    # 将记忆注入到 prompt
    memory_context = "\n".join([m.value for m in memories])
    
    llm = load_chat_model()
    response = await llm.ainvoke([
        {"role": "system", "content": f"用户记忆: {memory_context}"},
        *state.messages
    ])
    
    return {"messages": [response]}
```

### 4. 创建 Agent

```python
from langchain.agents import create_agent
from langgraph.store.memory import InMemoryStore

# 创建 store
store = InMemoryStore()

# 写入示例数据
store.put(
    ("users",),
    "user_123",
    {
        "name": "张三",
        "language": "中文",
        "preferences": "喜欢简洁的技术解释"
    }
)

# 创建 agent
agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[get_user_preferences, save_user_preference],
    store=store,  # ✅ 传递 store
    context_schema=Context
)

# 调用 agent
response = agent.invoke(
    {"messages": [{"role": "user", "content": "你好"}]},
    context=Context(user_id="user_123")  # ✅ 传递 context
)
```

## Store 的 API

### 写入数据: `store.put()`
```python
store.put(
    ("users",),           # 命名空间 (tuple)
    "user_123",           # 键 (string)
    {"name": "张三"}      # 值 (dict)
)
```

### 读取数据: `store.get()`
```python
item = store.get(("users",), "user_123")
if item:
    print(item.value)  # {"name": "张三"}
```

### 语义搜索: `store.search()`
```python
results = store.search(
    ("users", "user_123"),  # 命名空间
    query="语言偏好",        # 搜索查询
    filter={"role": "admin"},  # 可选过滤器
    limit=5
)
```

### 异步版本
```python
await store.aput(...)
await store.aget(...)
await store.asearch(...)
```

## 命名空间设计

### 推荐模式
```python
# 用户维度
("users", user_id)

# 组织维度
("organizations", org_id)

# 应用维度
("app_settings", app_id)

# 多层级
("users", user_id, "preferences")
("users", user_id, "history")
```

## 本项目中的错误使用

### ❌ 错误: 把 Memory Store 当作 RAG Vector Store

```python
# graph.py 第 31 行 - 这是错误的!
memories = await cast(BaseStore, runtime.store).asearch(
    ("memories", user_id),
    query=str([m.content for m in state.messages[-3:]]),
    limit=10,
)

# 这在检索用户记忆,不是检索 PDF 文档!
```

**问题分析**:
1. `runtime.store` 是 Memory Store,用于存储用户信息
2. 用户从未向 `("memories", user_id)` 命名空间写入任何数据
3. 即使有数据,也应该是用户偏好,不是 PDF 文档内容
4. PDF 文档应该从 `PGVector` 检索,不是从 `runtime.store`

### ✅ 正确的分离

```python
# 1. RAG 文档检索 (使用 PGVector)
from agent.vectorstore import get_retriever

retriever = get_retriever()
docs = await retriever.ainvoke("象量科技是做什么的?")  # 检索 PDF 文档

# 2. 用户记忆检索 (使用 runtime.store)
memories = await runtime.store.asearch(
    ("users", user_id),
    query="用户偏好"
)  # 检索用户信息
```

## 完整示例: RAG + Memory Store

```python
async def call_model(state: State, runtime: Runtime[Context]) -> dict:
    """同时使用 RAG 和 Memory Store."""
    user_id = runtime.context.user_id
    
    # 1. 从 Memory Store 获取用户偏好
    user_prefs = await runtime.store.aget(("users",), user_id)
    user_context = user_prefs.value if user_prefs else {}
    
    # 2. 构建 prompt
    system_prompt = f"""
    你是一个智能助手。
    用户信息: {user_context}
    
    你可以调用 retrieve_documents 工具检索 PDF 文档。
    """
    
    # 3. 调用 LLM (LLM 会决定是否调用 retrieve_documents)
    llm = load_chat_model()
    llm_with_tools = llm.bind_tools([retrieve_documents_tool])
    
    response = await llm_with_tools.ainvoke([
        {"role": "system", "content": system_prompt},
        *state.messages
    ])
    
    return {"messages": [response]}
```

## 总结

### Memory Store 的关键特点:
1. **跨线程共享**: 所有对话都能访问同一用户的记忆
2. **命名空间隔离**: 不同用户/组织的数据互不干扰
3. **语义搜索**: 支持向量相似度检索
4. **JSON 存储**: 存储结构化的用户信息

### 与 RAG 的本质区别:
- **Memory Store**: 存储"关于用户的信息" (主语是用户)
- **RAG Vector Store**: 存储"用户想查询的知识" (主语是知识库)

### 何时使用:
- ✅ **Memory Store**: 用户偏好、历史操作、个性化设置
- ✅ **RAG Vector Store**: PDF文档、技术文档、知识库内容
- ✅ **两者结合**: 个性化的知识问答系统

**本项目当前的错误**: 把 Memory Store 当成了 RAG Vector Store,导致 OpenAI quota 错误,因为:
1. 尝试用 `runtime.store.asearch()` 检索文档 (应该用 `vector_store.similarity_search()`)
2. 配置了 Memory Store 的 embeddings (不需要,因为没用来存储用户记忆)
3. 混淆了两个完全不同的功能模块
