# LangChain RAG 实现设计文档

**参考文档**: https://docs.langchain.com/oss/python/langchain/rag

## 核心概念

LangChain RAG 是一个**简单的单步检索-生成**模式,适用于基础问答场景。

## 架构设计

```
用户问题 → LLM决策 → 调用检索工具 → 返回文档 → LLM生成答案
```

## 关键组件

### 1. Vector Store (文档存储)

```python
from langchain_postgres import PGVector

vector_store = PGVector(
    embeddings=embeddings,
    collection_name="my_docs",
    connection="postgresql+psycopg://...",
)
```

### 2. 检索工具 (使用 @tool 装饰器)

**官方推荐方式**:

```python
from langchain.tools import tool

@tool
def retrieve_context(query: str) -> str:
    """Retrieve information related to a query."""
    retrieved_docs = vector_store.similarity_search(query, k=2)
    
    # 序列化文档内容
    serialized = "\n".join([
        f"Source: {doc.metadata.get('source', 'unknown')}\n"
        f"Content: {doc.page_content}"
        for doc in retrieved_docs
    ])
    
    return serialized
```

**核心特点**:
- 直接使用 `vector_store.similarity_search()`
- 手动序列化文档内容为字符串
- 返回格式化的文本给 LLM

### 3. Agent 构建

```python
from langchain.agents import create_agent

tools = [retrieve_context]
agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=tools,
    system_prompt="你可以使用检索工具查询知识库..."
)
```

## 执行流程

1. **用户提问**: "象量科技是做什么的?"
2. **LLM 决策**: 判断需要调用 `retrieve_context` 工具
3. **工具执行**: `vector_store.similarity_search("象量科技是做什么的", k=2)`
4. **文档返回**: 返回序列化的文档内容字符串
5. **LLM 生成**: 基于检索到的文档内容生成答案

## 适用场景

✅ **适合**:
- 简单问答
- 单步检索即可解决的问题
- 需要快速响应的场景

❌ **不适合**:
- 需要多步推理
- 需要文档相关性评分
- 需要问题重写优化

## 与本项目的区别

| 特性 | LangChain RAG | 本项目当前实现 |
|------|--------------|---------------|
| 检索方式 | `similarity_search()` | ❌ `runtime.store.asearch()` (错误!) |
| 工具类型 | `@tool` 装饰器 | `@tool` 装饰器 ✅ |
| 用途 | 文档知识库检索 | 用户记忆存储 (错误!) |
| 返回格式 | 序列化字符串 | Document 对象 |

## 正确的实现方式

```python
# src/agent/tools.py
from langchain.tools import tool
from agent.vectorstore import get_retriever

@tool
async def retrieve_documents(query: str) -> str:
    """从知识库检索相关文档."""
    retriever = get_retriever()
    docs = await retriever.ainvoke(query)
    
    # 序列化为字符串
    return "\n\n".join([
        f"来源: {doc.metadata.get('source', '未知')}\n内容: {doc.page_content}"
        for doc in docs
    ])
```

```python
# src/agent/graph.py
async def call_model(state: State, runtime: Runtime[Context]) -> dict:
    """调用模型生成响应."""
    model = runtime.context.model
    llm = load_chat_model(model)
    
    # ✅ 绑定检索工具
    msg = await llm.bind_tools([retrieve_documents]).ainvoke(
        [{"role": "system", "content": sys}, *state.messages]
    )
    return {"messages": [msg]}
```

## 总结

LangChain RAG 的核心是:
1. **Vector Store** 负责文档存储和相似度搜索
2. **@tool 装饰器**包装 `similarity_search()` 方法
3. **简单的单步检索**,无额外路由逻辑
4. **返回字符串格式**的文档内容给 LLM

**不涉及 `runtime.store`!** 那是用于跨线程的用户记忆存储。
