# 当前项目错误分析与修复方案

## 核心问题

**你混淆了三个完全不同的概念:**

1. **LangChain RAG** (简单文档检索)
2. **LangGraph Agentic RAG** (复杂多步检索)
3. **LangGraph Memory Store** (用户记忆存储)

## 错误 1: 把 Memory Store 当作 RAG Vector Store

### 当前错误代码 (graph.py:31)

```python
# ❌ 这是在检索用户记忆,不是检索 PDF 文档!
memories = await cast(BaseStore, runtime.store).asearch(
    ("memories", user_id),
    query=str([m.content for m in state.messages[-3:]]),
    limit=10,
)
```

### 错误分析

| 项目 | 应该做什么 | 实际做了什么 |
|------|-----------|-------------|
| **目标** | 检索 PDF 文档内容 | 检索用户记忆 |
| **数据源** | PGVector 数据库 | Memory Store |
| **API** | `vector_store.similarity_search()` | `runtime.store.asearch()` |
| **命名空间** | `collection_name="pdf_documents"` | `("memories", user_id)` |
| **用途** | 回答"象量科技是什么" | 回答"这个用户喜欢什么" |

### 为什么会报 OpenAI quota 错误?

```
错误链路:
1. 用户发送消息 → graph.py call_model()
2. call_model() 调用 runtime.store.asearch()
3. Memory Store 需要将查询向量化
4. langgraph.json 配置的 embeddings 调用 OpenAI API
5. OpenAI API 返回 429 - quota exceeded
```

**根本原因**: Memory Store 不应该被用来检索 PDF 文档!

## 错误 2: langgraph.json 配置错误

### 当前配置

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

### 问题分析

| 配置项 | 用途 | 是否需要 |
|--------|------|---------|
| `store.index` | Memory Store 的向量搜索配置 | ❌ 不需要 (没用 Memory Store) |
| `dims: 3072` | text-embedding-3-large 的维度 | ❌ 不需要 |
| `embed_kwargs` | 自定义 API 端点 | ❌ 不需要 |

**结论**: 因为项目不需要 Memory Store,应该删除整个 `store` 配置!

## 错误 3: 工具实现方式错误

### 当前实现 (tools.py)

```python
# ❌ 这是 LangChain RAG 的方式,但返回类型错误
@tool
async def retrieve_documents(query: str) -> list[Document]:
    """Search for documents in the vector store."""
    retriever = get_retriever()
    docs = await retriever.ainvoke(query)
    return docs  # ❌ 应该返回字符串,不是 Document 列表
```

### 问题分析

根据官方文档,有两种正确方式:

#### 方式 1: LangChain RAG (简单)
```python
from langchain.tools import tool

@tool
async def retrieve_documents(query: str) -> str:  # ✅ 返回字符串
    """Search for documents in the vector store."""
    retriever = get_retriever()
    docs = await retriever.ainvoke(query)
    
    # ✅ 序列化为字符串
    return "\n\n".join([
        f"来源: {doc.metadata.get('source', '未知')}\n"
        f"内容: {doc.page_content}"
        for doc in docs
    ])
```

#### 方式 2: LangGraph Agentic RAG (复杂)
```python
from langchain.tools.retriever import create_retriever_tool

# ✅ 使用官方工厂函数
retriever_tool = create_retriever_tool(
    get_retriever(),
    name="retrieve_documents",
    description="从 PDF 知识库检索相关文档."
)
```

## 错误 4: Graph 结构不完整

### 当前实现

```
START → call_model → execute_tools → call_model → END
```

**问题**: 这是一个简化的 LangChain RAG 流程,但:
- ❌ 混入了 Memory Store 检索
- ❌ 没有文档评分
- ❌ 没有问题重写
- ❌ 不是标准的 Agentic RAG

### 应该选择的方向

#### 选项 A: 简单 LangChain RAG
```
START → call_model (LLM 决策) → execute_tools → call_model → END
```
- 优点: 简单快速
- 缺点: 功能有限
- 适合: 基础问答

#### 选项 B: 完整 LangGraph Agentic RAG
```
START 
  ↓
generate_query_or_respond
  ↓
tools_condition
  ├─→ END
  └─→ retrieve
       ↓
     grade_documents
       ├─→ generate_answer → END
       └─→ rewrite_question → generate_query_or_respond
```
- 优点: 功能完整
- 缺点: 复杂,多次 LLM 调用
- 适合: 复杂推理

## 修复方案

### 方案 A: 保持简单 LangChain RAG 风格

#### 步骤 1: 修复 tools.py
```python
from langchain.tools import tool
from agent.vectorstore import get_retriever

@tool
async def retrieve_documents(query: str) -> str:
    """从 PDF 知识库检索相关文档."""
    retriever = get_retriever()
    docs = await retriever.ainvoke(query)
    
    # 序列化为字符串
    return "\n\n".join([
        f"来源: {doc.metadata.get('source', '未知')}\n"
        f"内容: {doc.page_content}"
        for doc in docs
    ])
```

#### 步骤 2: 修复 graph.py

```python
async def call_model(state: State, runtime: Runtime[Context]) -> dict:
    """调用模型生成响应."""
    model = runtime.context.model
    system_prompt = runtime.context.system_prompt
    
    # ❌ 删除这段 Memory Store 代码
    # memories = await cast(BaseStore, runtime.store).asearch(...)
    
    # ✅ 直接构建 prompt
    sys = system_prompt.format(
        user_info="",  # 不需要用户记忆
        time=datetime.now().isoformat()
    )
    
    llm = load_chat_model(model)
    
    # ✅ 只绑定 retrieve_documents 工具
    msg = await llm.bind_tools([retrieve_documents]).ainvoke(
        [{"role": "system", "content": sys}, *state.messages]
    )
    return {"messages": [msg]}
```

#### 步骤 3: 修复 langgraph.json

```json
{
    "dockerfile_lines": [],
    "graphs": {
        "agent": "./src/agent/graph.py:graph"
    },
    "env": ".env",
    "python_version": "3.11",
    "dependencies": ["."]
    // ❌ 删除整个 store 配置
}
```

#### 步骤 4: 删除不必要的工具

```python
# tools.py

# ❌ 删除 upsert_memory (不需要用户记忆)
# async def upsert_memory(...):
#     ...

# ✅ 只保留 retrieve_documents
```

### 方案 B: 实现完整 LangGraph Agentic RAG

这需要重构整个 graph.py,添加:
1. `generate_query_or_respond` 节点
2. `grade_documents` 节点 (评估文档相关性)
3. `rewrite_question` 节点 (重写问题)
4. `generate_answer` 节点 (生成答案)
5. 条件路由逻辑

**推荐**: 先使用方案 A,确保基础功能正常,再考虑升级到方案 B。

## 修复优先级

### P0 (必须修复 - 阻塞运行)
1. ✅ 删除 `graph.py` 中的 `runtime.store.asearch()` 调用
2. ✅ 删除 `langgraph.json` 中的 `store` 配置
3. ✅ 修复 `retrieve_documents` 返回类型为字符串

### P1 (高优先级 - 影响功能)
4. ✅ 删除 `tools.py` 中的 `upsert_memory` 工具
5. ✅ 更新 `prompts.py` 移除 Memory Store 相关描述
6. ✅ 更新 `README.md` 移除用户记忆功能描述

### P2 (中优先级 - 优化体验)
7. ⏭️ 添加文档评分逻辑 (可选)
8. ⏭️ 添加问题重写逻辑 (可选)
9. ⏭️ 改进 prompt 工程

## 测试验证

### 修复后测试步骤
1. 启动服务: `langgraph dev`
2. 发送测试问题: "象量科技是做什么的?"
3. 预期行为:
   - LLM 决定调用 `retrieve_documents` 工具
   - 工具从 PGVector 检索文档
   - 返回序列化的文档内容
   - LLM 基于文档生成答案
4. 验证没有 OpenAI quota 错误

### 验证检查点
- ✅ 没有调用 `runtime.store.asearch()`
- ✅ 没有向 OpenAI embeddings API 发送请求
- ✅ 成功从 PGVector 检索文档
- ✅ LLM 成功生成答案

## 总结

**核心问题**: 把三个不同的概念混在一起了!

| 概念 | 用途 | 数据源 | 本项目是否需要 |
|------|------|--------|---------------|
| LangChain RAG | PDF 文档检索 | PGVector | ✅ 需要 |
| LangGraph Agentic RAG | 复杂多步检索 | PGVector | ⏭️ 可选 |
| Memory Store | 用户记忆存储 | Memory Store | ❌ 不需要 |

**修复方向**: 移除 Memory Store,专注于简单的 RAG 文档检索。

**下一步**: 等待你确认使用方案 A (简单) 还是方案 B (复杂),然后我会执行修复。
