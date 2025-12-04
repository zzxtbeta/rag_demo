# Project Context

## Purpose

本项目是一个基于 **LangGraph** 和 **PGVector** 的智能文档问答系统，实现多步推理的检索增强生成（RAG）。

核心功能：
- 🧠 **智能决策**: LLM 自主判断是否需要检索文档
- 🔍 **语义检索**: 使用 PGVector + OpenAI text-embedding-3-large 进行向量检索
- 💬 **DashScope Qwen**: 使用阿里云通义千问作为推理模型
- 💾 **短期记忆**: 使用 LangGraph Postgres checkpointer 支持基于 `thread_id` 的对话线程
- 📊 **可观测性**:（可选）支持 LangSmith 追踪和调试

项目参考 [LangGraph Agentic RAG 官方模式](https://docs.langchain.com/oss/python/langgraph/agentic-rag)，当前实现为**简化版 Agentic RAG**：只包含“是否检索→检索→生成答案”的主干流程，后续可按需求增量扩展文档评分与问题重写节点。

## Tech Stack

### 核心框架
- **LangGraph** (>=1.0.0,<1.1.0): 用于构建状态化的工作流和代理编排
- **LangChain** (>=1.0.0,<1.2.0): 提供 RAG 组件、工具集成和文档处理能力
- **LangChain Core** (>=1.0.0,<1.2.0): LangChain 核心抽象和接口

### LLM 集成
- **langchain-openai** (>=1.0.0,<1.2.0): OpenAI 兼容接口（用于 DashScope Qwen）
- **langchain-anthropic** (>=1.0.0,<1.3.0): Anthropic Claude 支持（可选）

### 向量存储和 RAG
- **langchain-postgres** (>=0.0.12,<0.1.0): PostgreSQL + pgvector 向量存储集成
- **langchain-text-splitters** (>=0.3.11,<1.1.0): 文档分块工具（RecursiveCharacterTextSplitter）
- **langchain-community** (>=0.4.0,<0.5.0): 社区集成（PDF 加载器等）

### 数据库
- **psycopg[binary]** (>=3.1.0): PostgreSQL 驱动（psycopg3）
- **PostgreSQL**: 需要启用 pgvector 扩展，同时作为 LangGraph checkpointer/store 的持久化后端

### 文档处理
- **pypdf** (>=5.1.0): PDF 文档解析

### API 与前端
- **fastapi** (>=0.115.0,<0.116.0): Web 框架，提供 REST API 和 WebSocket 端点
- **uvicorn** (>=0.30.0,<0.31.0): ASGI 服务器
- **redis** (>=5.0.0): Redis 客户端，用于 Pub/Sub 流式消息传递
- **React + TypeScript + Vite**: 前端聊天界面（`frontend/` 目录）

### 开发工具
- **Python** (>=3.10): 编程语言
- **ruff** (>=0.6.1): 代码格式化和 linting
- **mypy** (>=1.11.1): 类型检查
- **pytest** (>=8.3.5): 测试框架
- **langgraph-cli[inmem]** (>=0.1.71): LangGraph CLI 工具

## Project Conventions

### Code Style

- **格式化工具**: 使用 `ruff` 进行代码格式化和 linting
- **代码风格**: 遵循 PEP 8，使用 pycodestyle (E) 和 pyflakes (F) 规则
- **导入排序**: 使用 isort (I) 规则自动排序导入
- **文档字符串**: 使用 Google 风格文档字符串（pydocstyle，convention=google）
- **类型提示**: 使用 mypy 进行类型检查（当前设置为 ignore_errors=true）
- **命名约定**: 
  - 模块名：小写，下划线分隔（如 `init_vectorstore.py`）
  - 类名：PascalCase（如 `Context`, `State`）
  - 函数名：小写，下划线分隔（如 `get_retriever`, `index_documents`）
  - 常量：大写，下划线分隔（如 `SYSTEM_PROMPT`）

### Architecture Patterns

#### LangGraph 工作流模式
- 使用 `StateGraph` 构建状态化工作流
- 使用 `MessagesState` 管理对话消息状态
- 节点函数为 `async def`，接收 `state` 参数并返回状态更新字典，结合 LangChain 异步模型 `ainvoke`
- 使用 `tools_condition` 进行条件路由（检查是否有 tool_calls）
- 通过 `thread_id` + Postgres checkpointer 持久化线程级短期记忆

#### RAG 工具模式
- 使用 `@tool` 装饰器创建检索工具
- 工具使用 `response_format="content_and_artifact"` 返回序列化内容和原始文档对象
- 检索工具直接调用 `vector_store.similarity_search()` 进行语义搜索

#### 向量存储模式
- 使用 `PGVector` 作为向量存储后端
- 连接字符串格式：`postgresql://...`，在代码中统一转换为 `postgresql+psycopg://...`（使用 psycopg3 驱动）
- 文档分块使用 `RecursiveCharacterTextSplitter`，默认 chunk_size=1000, chunk_overlap=200
- 使用 `OpenAIEmbeddings` 生成文档嵌入（text-embedding-3-large 模型）

#### 模型加载模式
- 通过环境变量配置模型（`MODEL_NAME`, `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL`）
- 使用 `ChatOpenAI` 兼容接口访问 DashScope Qwen 模型
- 默认模型：`qwen-plus-latest`

#### 持久化与记忆模式
- 短期记忆：使用 `langgraph.checkpoint.postgres.PostgresSaver`，通过 `thread_id` 控制对话线程的状态恢复
- 长期记忆：预留 `AsyncPostgresStore` 封装（`src/db/memory_store.py`），未来可按 LangGraph 官方 Memory 模式接入跨线程记忆

#### 流式处理与实时通信模式
- **Redis Pub/Sub**: 使用 `workflow:{thread_id}:{node_name}:{message_type}` 频道命名，实现节点级实时推送
- **WebSocket**: 通过 `/ws/{thread_id}` 端点代理 Redis 消息到前端，支持多客户端订阅
- **消息序列化**: 使用 `message_to_dict()` 处理 LangChain `AIMessage` 对象，避免 JSON 序列化错误
- **前端消息解析**: 从 `data.messages` 数组中提取 AI 回复，节点输出可折叠显示 JSON 详情

### Testing Strategy

- **测试框架**: pytest
- **测试位置**: `tests/` 目录
- **集成测试**: 使用 LangSmith 的 `@unit` 装饰器进行可追踪的评估测试
- **测试覆盖**: 当前项目包含集成测试示例（`tests/integration_tests/test_graph.py`）

### Git Workflow

- 使用标准的 Git 工作流
- 遵循 OpenSpec 变更管理流程（见 `openspec/AGENTS.md`）
- 变更提案需要创建 `changes/[change-id]/` 目录并包含 `proposal.md`, `tasks.md` 和 spec deltas

## Domain Context

### RAG（检索增强生成）概念
- **向量检索**: 将文档转换为向量嵌入，使用相似度搜索找到相关文档
- **文档分块**: 将长文档分割成较小的块，便于检索和上下文管理
- **语义搜索**: 基于语义相似度而非关键词匹配的搜索方式

### LangGraph 核心概念
- **StateGraph**: 定义状态化工作流的图结构
- **MessagesState**: 预构建的状态类型，用于管理对话消息
- **节点 (Node)**: 工作流中的执行单元，接收状态并返回更新
- **边 (Edge)**: 定义节点之间的连接和路由逻辑
- **条件边 (Conditional Edge)**: 根据状态动态决定下一个节点

### Agentic RAG vs 简单 RAG
- **简单 RAG**: LLM 总是检索文档，然后生成答案（单步流程）
- **Agentic RAG**: LLM 自主决定是否需要检索，可以跳过检索直接回答（多步决策流程）
- 本项目实现的是简化版的 Agentic RAG，只包含基本的检索决策和文档工具调用，不包含文档评分和问题重写等高级功能

### 文档处理流程
1. **加载**: 使用 `PyPDFLoader` 从 PDF 文件加载文档
2. **分块**: 使用 `RecursiveCharacterTextSplitter` 将文档分割成块
3. **嵌入**: 使用 `OpenAIEmbeddings` 生成每个块的向量嵌入
4. **存储**: 将嵌入向量和元数据存储到 PostgreSQL（pgvector）
5. **检索**: 根据查询生成嵌入向量，使用相似度搜索找到相关文档块

## Important Constraints

### 技术约束
- **Python 版本**: 必须 >= 3.10
- **PostgreSQL**: 必须启用 pgvector 扩展
- **API 密钥**: 需要配置以下环境变量：
  - `OPENAI_EMBEDDINGS_API_KEY`: OpenAI Embeddings API 密钥（用于文档嵌入）
  - `DASHSCOPE_API_KEY`: DashScope API 密钥（用于 Qwen 模型）
  - `DASHSCOPE_BASE_URL`: DashScope API 基础 URL
  - `POSTGRES_CONNECTION_STRING`: PostgreSQL 连接字符串（格式：`postgresql://...`，内部会转换为 `postgresql+psycopg://...`）

### 架构约束
- **向量存储**: 必须使用 PostgreSQL + pgvector，不支持其他向量数据库
- **文档格式**: 当前仅支持 PDF 格式文档
- **模型兼容性**: 使用 OpenAI 兼容接口，需要模型支持工具调用（tool calling）
- **执行模型**: 推荐使用 LangGraph v1 的异步执行（`ainvoke/astream`），节点函数采用 `async def`

### 性能约束
- **文档分块大小**: 默认 1000 字符，可根据需要调整
- **检索数量**: 默认检索 top-2 文档（可在工具中配置）
- **并发**: LangGraph 支持流式处理和并发执行，结合 Postgres checkpointer 可安全地管理多线程会话

## External Dependencies

### 外部服务

#### DashScope（阿里云）
- **用途**: 提供 Qwen 大语言模型服务
- **配置**: 通过 `DASHSCOPE_API_KEY` 和 `DASHSCOPE_BASE_URL` 环境变量配置
- **模型**: 默认使用 `qwen-plus-latest`
- **文档**: [DashScope 文档](https://help.aliyun.com/zh/model-studio/)

#### OpenAI（或兼容服务）
- **用途**: 提供文本嵌入模型服务（text-embedding-3-large）
- **配置**: 通过 `OPENAI_EMBEDDINGS_API_KEY` 环境变量配置
- **可选**: 可通过 `LITELLM_BASE_URL` 使用 LiteLLM 等代理服务
- **文档**: [OpenAI Embeddings 文档](https://platform.openai.com/docs/guides/embeddings)

#### PostgreSQL + pgvector
- **用途**: 向量数据库，存储文档嵌入向量
- **要求**: 
  - PostgreSQL >= 14（推荐）
  - 必须启用 pgvector 扩展：`CREATE EXTENSION IF NOT EXISTS vector;`
- **连接**: 使用 psycopg3 驱动（`postgresql+psycopg://...`）
- **文档**: [pgvector 文档](https://github.com/pgvector/pgvector)

#### LangSmith（可选）
- **用途**: 追踪、调试和评估 LangChain/LangGraph 应用
- **配置**: 通过 `LANGSMITH_PROJECT` 和 `LANGSMITH_API_KEY` 环境变量配置
- **文档**: [LangSmith 文档](https://docs.smith.langchain.com/)

### 关键依赖版本约束
- LangGraph: 1.0.x（稳定版本，API 稳定）
- LangChain: 1.0.x - 1.1.x（与 LangGraph v1 兼容）
- langchain-postgres: 0.0.12+（支持 PGVector）
- psycopg: 3.1.0+（psycopg3，异步支持）

### 参考资源
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph Agentic RAG 教程](https://docs.langchain.com/oss/python/langgraph/agentic-rag)
- [LangChain RAG 教程](https://docs.langchain.com/oss/python/langchain/rag)
- [PGVector 文档](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings 文档](https://platform.openai.com/docs/guides/embeddings)
