# LangGraph Agentic RAG

基于 **LangGraph v1** 和 **PGVector** 的智能文档问答系统，实现异步、可持久化的检索增强生成（RAG）Agent。

当前实现的是一个 **简化版 Agentic RAG**：LLM 自主判断是否需要检索文档，使用工具从 PGVector 检索上下文，并基于检索结果生成答案；同时通过 LangGraph 的 **Postgres checkpointer** 支持基于 `thread_id` 的短期记忆（对话线程）。

参考文档：
- [LangGraph Agentic RAG 教程](https://docs.langchain.com/oss/python/langgraph/agentic-rag)
- [LangChain RAG 指南](https://docs.langchain.com/oss/python/langchain/rag)
- [LangGraph 持久化与记忆](https://docs.langchain.com/oss/python/langgraph/add-memory)

## 功能特性

- 🧠 **智能决策**：LLM 通过工具调用决定是否需要检索文档
- 🔍 **语义检索**：PGVector + OpenAI `text-embedding-3-large`
- 💬 **DashScope Qwen**：使用阿里云通义千问作为推理模型（经 OpenAI 兼容接口）
- 💾 **短期记忆**：基于 `thread_id` 的对话线程，通过 Postgres checkpointer 持久化
- 🧱 **模块化结构**：`agent`（图与状态）、`tools`（工具）、`utils`（通用函数）、`config`（配置）、`db`（持久化）

## 架构设计（当前简化版）

```text
用户问题
  ↓
query_or_respond (LLM 决策，是否调用检索工具)
  ├─→ 无 tool_calls → 直接回答 → END
  └─→ 有 tool_calls → tools (retrieve_context)
       ↓
                       generate (基于检索结果生成答案) → END
```

后续可以按 [官方 Agentic RAG 教程](https://docs.langchain.com/oss/python/langgraph/agentic-rag) 扩展 `grade_documents` / `rewrite_question` 等节点。

## 项目结构（简化）

```text
rag_demo/
├── data/                      # PDF 文档存放目录
├── scripts/
│   ├── __init__.py
│   └── init_vectorstore.py    # 文档索引脚本
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── context.py         # Runtime 上下文（预留）
│   │   ├── graph.py           # LangGraph 图定义（异步节点 + checkpointer）
│   │   ├── state.py           # 状态管理（MessagesState 扩展）
│   │   └── vectorstore.py     # PGVector 封装（索引/检索）
│   ├── tools/
│   │   ├── __init__.py
│   │   └── retrieval.py       # 检索工具（给 LLM 调用）
│   ├── utils/
│   │   ├── __init__.py
│   │   └── llm.py             # 模型加载（DashScope Qwen，经 ChatOpenAI）
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py        # 全局配置（环境变量集中管理）
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py        # PostgreSQL 连接池（psycopg_pool）
│   │   ├── checkpointer.py    # LangGraph PostgresSaver 封装（短期记忆）
│   │   └── memory_store.py    # LangGraph AsyncPostgresStore 封装（长期记忆，预留）
│   └── api/                   # 预留给 FastAPI / LangGraph Agent Server 集成
├── .env.example               # 环境变量示例
├── pyproject.toml             # 项目依赖配置
└── README.md                  # 项目文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install -e .
```

主要依赖：
- `langgraph`：LangGraph 框架（v1）
- `langgraph-checkpoint` / `langgraph-checkpoint-postgres`：Postgres checkpointer
- `langchain-openai`：OpenAI 兼容接口
- `langchain-postgres`：PostgreSQL 向量存储
- `langchain-community`：文档加载器等工具
- `langchain-text-splitters`：文档分块
- `pypdf`：PDF 解析
- `psycopg[binary]`：PostgreSQL 驱动

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并填写必要的配置：

```bash
cp .env.example .env
```

关键配置（与 `config/settings.py` 对应）：

```env
# Embeddings 专用 Key
OPENAI_EMBEDDINGS_API_KEY=your-embeddings-key

# DashScope（Qwen）模型配置（经 OpenAI 兼容协议调用）
MODEL_NAME=qwen-plus-latest
DASHSCOPE_API_KEY=your-dashscope-key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# PostgreSQL 连接字符串（需启用 pgvector）
POSTGRES_CONNECTION_STRING=postgresql://username:password@localhost:5432/dbname

# 可选：自定义集合名与分块参数
VECTOR_COLLECTION=pdf_documents
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
RETRIEVER_TOP_K=2
```

> `config/settings.py` 会自动将 `POSTGRES_CONNECTION_STRING` 转换为 `postgresql+psycopg://` 形式供 PGVector 使用。

### 3. 准备 PostgreSQL 与 pgvector

确保 PostgreSQL 已启用 `pgvector` 扩展：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. 准备 PDF 文档

```bash
mkdir -p data
# 将你的 PDF 文件复制到 data/ 目录
cp /path/to/your/documents/*.pdf data/
```

### 5. 索引文档到向量库

使用脚本将 PDF 文档索引到 PGVector：

```bash
python -m scripts.init_vectorstore
```

可选参数：

- `--pdf-dir`：PDF 文件目录（默认 `./data`）
- `--collection-name`：集合名称（默认读取 `VECTOR_COLLECTION` 环境变量）
- `--chunk-size`：文本块大小（默认 `CHUNK_SIZE`）
- `--chunk-overlap`：块重叠大小（默认 `CHUNK_OVERLAP`）

示例：

```bash
python -m scripts.init_vectorstore \
    --pdf-dir ./data \
  --collection-name pdf_documents \
    --chunk-size 1500 \
    --chunk-overlap 300
```

### 6. 运行异步 RAG Agent（本地调用）

`src/agent/graph.py` 暴露了一个异步图实例 `graph`，并默认使用 Postgres checkpointer 支持基于 `thread_id` 的短期记忆：

```python
from agent.graph import graph

config = {"configurable": {"thread_id": "user-123"}}

result = await graph.ainvoke(
    {"messages": [{"role": "user", "content": "这份文档里提到了哪些关键技术？"}]},
    config,
)

print(result["messages"][-1].content)
```

如果需要流式输出：

```python
async for update in graph.astream(
    {"messages": [{"role": "user", "content": "帮我总结一下文档的主要内容"}]},
    config,
    stream_mode="updates",
):
    # update 里会包含各节点的增量消息
    ...
```

> 同一个 `thread_id` 会共享对话上下文，不同 `thread_id` 之间相互隔离。

### 7. FastAPI 接口

项目内置了一个 FastAPI 服务，可直接对接工作流：

```bash
uvicorn api.app:app --reload
```

`POST /chat` 请求示例：

```json
{
  "thread_id": "user-123",
  "user_id": "alice",
  "message": "帮我总结文档的关键结论"
}
```

响应：

```json
{
  "thread_id": "user-123",
  "user_id": "alice",
  "answer": "..."
}
```

FastAPI 在启动时会：

1. 初始化 PostgreSQL 连接池和 LangGraph Postgres checkpointer；
2. 构建异步 `graph` 实例并缓存到 `app.state`；
3. 每次调用 `/chat` 时，通过 `graph.ainvoke(...)` 与 LangGraph workflow 交互。

当部署到 LangGraph Agent Server / Cloud 时，可通过 `langgraph dev` 或 `langgraph up` 直接加载 `graph`（此时 checkpointer 由平台管理）。

## 后续扩展方向

- **Agentic RAG 完整流程**：增加 `grade_documents` / `rewrite_question` 等节点（参考官方教程）
- **长期记忆（跨线程 Store）**：基于 `src/db/memory_store.py` 注入 `AsyncPostgresStore`，在节点中通过 `store: BaseStore` + `config: RunnableConfig` 做用户记忆的读写（参考官方 [Add Memory 文档](https://docs.langchain.com/oss/python/langgraph/add-memory)）
- **API 层**：在 `src/api/` 中使用 FastAPI 封装对 `graph` 的 `ainvoke/astream` 调用

## 许可证

MIT License

## 参考资源

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph Agentic RAG 教程](https://docs.langchain.com/oss/python/langgraph/agentic-rag)
- [LangChain RAG 教程](https://docs.langchain.com/oss/python/langchain/rag)
- [PGVector 文档](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)

## 使用示例

### 基本对话

```
用户: 文档中提到了什么关键技术?
Agent: [自动调用 retrieve_documents 工具检索相关内容]
Agent: 根据文档,主要提到了以下技术...
```

### 个性化记忆

```
用户: 我对机器学习很感兴趣
Agent: [自动存储用户偏好到 memory store]
Agent: 明白了,我会记住您对机器学习的兴趣...
```

## 配置说明

### LLM 模型配置

默认使用 Anthropic Claude,可以在环境变量或代码中修改:

- Anthropic: `anthropic/claude-sonnet-4-5-20250929`
- OpenAI: `openai/gpt-4o`
- 其他支持的模型...

### 检索参数

在 `vectorstore.py` 中调整检索数量:

```python
search_kwargs = {"k": 4}  # 返回的文档数量
```

### 分块策略

在 `vectorstore.py` 中调整文档分块参数:

```python
chunk_size = 1000       # 每个块的最大字符数
chunk_overlap = 200     # 块之间的重叠字符数
```

## 许可证

MIT License

## 参考资源

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangChain RAG 教程](https://python.langchain.com/docs/tutorials/rag/)
- [PGVector 文档](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)

Assuming the bot saved some memories, create a _new_ thread using the `+` icon. Then chat with the bot again - if you've completed your setup correctly, the bot should now have access to the memories you've saved!

You can review the saved memories by clicking the "memory" button.

![Memories Explorer](./static/memories.png)

## How it works

This chat bot reads from your memory graph's `Store` to easily list extracted memories. If it calls a tool, LangGraph will route to the `store_memory` node to save the information to the store.

## How to evaluate

Memory management can be challenging to get right, especially if you add additional tools for the bot to choose between.
To tune the frequency and quality of memories your bot is saving, we recommend starting from an evaluation set, adding to it over time as you find and address common errors in your service.

We have provided a few example evaluation cases in [the test file here](./tests/integration_tests/test_graph.py). As you can see, the metrics themselves don't have to be terribly complicated, especially not at the outset.

We use [LangSmith's @unit decorator](https://docs.smith.langchain.com/how_to_guides/evaluation/unit_testing#write-a-test) to sync all the evaluations to LangSmith so you can better optimize your system and identify the root cause of any issues that may arise.

## How to customize

1. Customize memory content: we've defined a simple memory structure `content: str, context: str` for each memory, but you could structure them in other ways.
2. Provide additional tools: the bot will be more useful if you connect it to other functions.
3. Select a different model: We default to anthropic/claude-3-5-sonnet-20240620. You can select a compatible chat model using provider/model-name via configuration. Example: openai/gpt-4.
4. Customize the prompts: We provide a default prompt in the [prompts.py](src/memory_agent/prompts.py) file. You can easily update this via configuration.
