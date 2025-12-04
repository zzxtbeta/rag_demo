# LangGraph Agentic RAG 实现设计文档

**参考文档**: https://docs.langchain.com/oss/python/langgraph/agentic-rag

## 核心概念

LangGraph Agentic RAG 是一个**复杂的多步推理**系统,包含文档相关性评分、问题重写等高级功能。

## 架构设计

```
START
  ↓
generate_query_or_respond (LLM 决策)
  ↓
tools_condition (条件路由)
  ├─→ END (直接回答)
  └─→ retrieve (调用检索工具)
       ↓
     grade_documents (文档评分)
       ├─→ generate_answer (生成答案) → END
       └─→ rewrite_question (重写问题) → generate_query_or_respond
```

## 关键组件

### 1. Vector Store (与 LangChain RAG 相同)

```python
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

vectorstore = InMemoryVectorStore.from_documents(
    documents=doc_splits,
    embedding=OpenAIEmbeddings()
)
retriever = vectorstore.as_retriever()
```

### 2. 检索工具 (使用 create_retriever_tool)

**官方推荐方式** (与 LangChain RAG 不同):

```python
from langchain.tools.retriever import create_retriever_tool

retriever_tool = create_retriever_tool(
    retriever,
    name="retrieve_documents",
    description="Search and return information from the knowledge base."
)
```

**与 LangChain RAG 的区别**:
- ❌ 不使用 `@tool` 装饰器
- ✅ 使用 `create_retriever_tool()` 工厂函数
- ✅ 自动处理文档返回和序列化

### 3. Graph 节点定义

#### 节点 1: generate_query_or_respond
```python
def generate_query_or_respond(state: MessagesState):
    """决定是调用检索工具还是直接回答."""
    llm = ChatOpenAI(model="gpt-4o")
    llm_with_tools = llm.bind_tools([retriever_tool])
    
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}
```

#### 节点 2: grade_documents
```python
def grade_documents(state: MessagesState):
    """评估检索到的文档是否相关."""
    last_message = state["messages"][-1]
    docs = last_message.content  # 从 ToolMessage 获取文档
    
    # 使用 LLM 评估文档相关性
    if is_relevant(docs):
        return "generate_answer"  # 相关 → 生成答案
    else:
        return "rewrite_question"  # 不相关 → 重写问题
```

#### 节点 3: rewrite_question
```python
def rewrite_question(state: MessagesState):
    """重写问题以优化检索."""
    original_question = state["messages"][0].content
    
    # 使用 LLM 重写问题
    rewritten = llm.invoke(f"重写这个问题: {original_question}")
    
    return {"messages": [HumanMessage(content=rewritten)]}
```

#### 节点 4: generate_answer
```python
def generate_answer(state: MessagesState):
    """基于相关文档生成最终答案."""
    docs = state["messages"][-1].content
    question = state["messages"][0].content
    
    prompt = f"基于以下文档回答问题:\n{docs}\n\n问题: {question}"
    response = llm.invoke(prompt)
    
    return {"messages": [response]}
```

### 4. Graph 组装

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

workflow = StateGraph(MessagesState)

# 添加节点
workflow.add_node("generate_query_or_respond", generate_query_or_respond)
workflow.add_node("retrieve", ToolNode([retriever_tool]))
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("rewrite_question", rewrite_question)
workflow.add_node("generate_answer", generate_answer)

# 添加边
workflow.add_edge(START, "generate_query_or_respond")

# 条件边: 决定是检索还是直接回答
workflow.add_conditional_edges(
    "generate_query_or_respond",
    tools_condition,  # 检查是否有 tool_calls
    {
        "tools": "retrieve",  # 有 tool_calls → 检索
        END: END,             # 无 tool_calls → 结束
    },
)

# 条件边: 评估文档相关性
workflow.add_conditional_edges(
    "retrieve",
    grade_documents,  # 返回 "generate_answer" 或 "rewrite_question"
)

workflow.add_edge("generate_answer", END)
workflow.add_edge("rewrite_question", "generate_query_or_respond")  # 循环

# 编译
graph = workflow.compile()
```

## 执行流程示例

### 场景 1: 文档相关,一次检索成功
```
用户: "象量科技是做什么的?"
  ↓
generate_query_or_respond → 决定调用 retriever_tool
  ↓
retrieve → 检索到相关文档
  ↓
grade_documents → 文档相关 ✅
  ↓
generate_answer → 生成答案
  ↓
END
```

### 场景 2: 文档不相关,需要重写问题
```
用户: "他们的主要产品?"  (问题不够具体)
  ↓
generate_query_or_respond → 调用 retriever_tool
  ↓
retrieve → 检索到不相关文档
  ↓
grade_documents → 文档不相关 ❌
  ↓
rewrite_question → "象量科技的主要产品是什么?"
  ↓
generate_query_or_respond → 再次调用 retriever_tool
  ↓
retrieve → 检索到相关文档
  ↓
grade_documents → 文档相关 ✅
  ↓
generate_answer → 生成答案
  ↓
END
```

## 适用场景

✅ **适合**:
- 复杂问答需求
- 需要多步推理
- 需要文档相关性验证
- 需要问题优化

❌ **不适合**:
- 简单快速问答 (用 LangChain RAG)
- 对延迟敏感的场景

## 与 LangChain RAG 的对比

| 特性 | LangChain RAG | LangGraph Agentic RAG |
|------|--------------|----------------------|
| 检索工具 | `@tool` + `similarity_search()` | `create_retriever_tool()` |
| 决策逻辑 | LLM 直接决策 | Graph 节点 + 条件边 |
| 文档评分 | ❌ 无 | ✅ `grade_documents` 节点 |
| 问题重写 | ❌ 无 | ✅ `rewrite_question` 节点 |
| 复杂度 | 简单 (单步) | 复杂 (多步循环) |
| 响应速度 | 快 | 慢 (多次 LLM 调用) |

## 与本项目的区别

| 特性 | LangGraph Agentic RAG | 本项目当前实现 |
|------|---------------------|---------------|
| 检索工具 | `create_retriever_tool()` | ❌ `@tool` + `get_retriever()` |
| 文档评分 | ✅ `grade_documents` 节点 | ❌ 无 |
| 问题重写 | ✅ `rewrite_question` 节点 | ❌ 无 |
| 条件路由 | ✅ `tools_condition` + 自定义路由 | ❌ 简单的 `route_message` |
| 用途 | 文档知识库检索 | ❌ 混合了 `runtime.store` (用户记忆) |

## 本项目的错误

### ❌ 错误 1: 混淆了 RAG 检索和用户记忆
```python
# 这是用户记忆存储,不是 RAG 文档检索!
memories = await cast(BaseStore, runtime.store).asearch(
    ("memories", user_id),
    query=str([m.content for m in state.messages[-3:]]),
    limit=10,
)
```

### ❌ 错误 2: 使用了错误的工具类型
```python
# 应该使用 create_retriever_tool() 而不是 @tool
@tool
async def retrieve_documents(query: str) -> list[Document]:
    ...
```

### ❌ 错误 3: 缺少核心节点
- 缺少 `grade_documents` 节点
- 缺少 `rewrite_question` 节点
- 缺少 `generate_answer` 节点

## 正确的实现方式

```python
# src/agent/tools.py
from langchain.tools.retriever import create_retriever_tool
from agent.vectorstore import get_retriever

# ✅ 使用 create_retriever_tool
retriever_tool = create_retriever_tool(
    get_retriever(),
    name="retrieve_documents",
    description="从 PDF 知识库检索相关文档."
)
```

```python
# src/agent/graph.py
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

def generate_query_or_respond(state: State, runtime: Runtime[Context]):
    llm = load_chat_model()
    llm_with_tools = llm.bind_tools([retriever_tool])
    response = llm_with_tools.invoke(state.messages)
    return {"messages": [response]}

def grade_documents(state: State):
    # 评估文档相关性
    ...
    return "generate_answer" if relevant else "rewrite_question"

def rewrite_question(state: State):
    # 重写问题
    ...

def generate_answer(state: State):
    # 生成最终答案
    ...

# 构建 Graph
workflow = StateGraph(State)
workflow.add_node("generate_query_or_respond", generate_query_or_respond)
workflow.add_node("retrieve", ToolNode([retriever_tool]))
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("rewrite_question", rewrite_question)
workflow.add_node("generate_answer", generate_answer)

workflow.add_edge(START, "generate_query_or_respond")
workflow.add_conditional_edges(
    "generate_query_or_respond",
    tools_condition,
    {"tools": "retrieve", END: END}
)
workflow.add_conditional_edges("retrieve", grade_documents)
workflow.add_edge("generate_answer", END)
workflow.add_edge("rewrite_question", "generate_query_or_respond")

graph = workflow.compile()
```

## 总结

LangGraph Agentic RAG 的核心是:
1. **create_retriever_tool()** 创建检索工具
2. **多节点 Graph** 实现复杂推理流程
3. **条件路由** 实现文档评分和问题重写
4. **循环结构** 允许多次尝试检索

**完全不涉及 `runtime.store`!** 那是用于跨线程的用户记忆,与 RAG 文档检索是两个独立的功能。
