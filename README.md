# GravAIty - 智能文档问答系统

基于 **LangGraph v1** 和 **PGVector** 的智能文档问答系统，实现异步、可持久化的检索增强生成（RAG）Agent。

**核心特性**：
- 🧠 **Agentic RAG**：LLM 自主决策是否需要检索文档
- 🖼️ **多模态支持**：通过 MinerU 解析 PDF，支持文本 + 图片显示
- 🔍 **语义检索**：PGVector + OpenAI embeddings
- 💬 **推理模型**：DashScope Qwen（OpenAI 兼容接口）
- 💾 **对话记忆**：基于 `thread_id` 的线程隔离
- 🎨 **现代化前端**：React + Markdown 渲染，支持图片、表格、代码块

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

## 项目结构

```text
gravaity/
├── backend/
│   ├── src/
│   │   ├── agent/              # LangGraph 工作流
│   │   │   ├── graph.py        # 主工作流定义
│   │   │   ├── state.py        # 状态管理
│   │   │   ├── prompts.py      # LLM 提示词
│   │   │   └── vectorstore.py  # 向量存储操作
│   │   ├── api/                # FastAPI 接口
│   │   │   ├── app.py          # 应用入口
│   │   │   └── routes/
│   │   │       ├── chat.py     # 聊天接口
│   │   │       └── documents.py # 文档处理接口
│   │   ├── tools/              # LLM 工具
│   │   │   └── retrieval.py    # 检索工具
│   │   ├── utils/              # 工具函数
│   │   │   ├── llm.py          # 模型加载
│   │   │   └── mineru_processor.py  # MinerU 文档处理
│   │   ├── config/             # 配置管理
│   │   │   └── settings.py     # 环境变量加载
│   │   └── db/                 # 数据库
│   │       ├── database.py     # 连接池
│   │       └── checkpointer.py # 对话持久化
│   ├── .env.example            # 环境变量示例
│   ├── pyproject.toml          # Python 依赖
│   └── start_backend.py        # 启动脚本
│
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/         # React 组件
│   │   ├── hooks/              # 自定义 hooks
│   │   ├── styles.css          # 样式表
│   │   └── main.tsx            # 入口
│   ├── package.json            # Node 依赖
│   └── vite.config.ts          # Vite 配置
│
├── data/                       # MinerU 解析结果存放
├── docs/                       # 文档
│   └── DOCUMENT_PROCESSING.md  # 文档处理指南
└── openspec/                   # 变更提案
```

## 快速开始

### 0. 前置要求

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ (with pgvector extension)
- API Keys: OpenAI (embeddings), DashScope (Qwen)

### 1. 后端安装与配置

#### 1.1 安装 Python 依赖

```bash
# 进入项目根目录
cd gravaity

# 安装后端依赖
pip install -e .
```

#### 1.2 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 填写必要配置：

```env
# OpenAI Embeddings (用于向量化文档)
OPENAI_EMBEDDINGS_API_KEY=sk-...

# DashScope Qwen (推理模型)
DASHSCOPE_API_KEY=sk-...
CHAT_MODEL=qwen-plus-latest

# PostgreSQL (需启用 pgvector)
POSTGRES_CONNECTION_STRING=postgresql://user:password@localhost:5432/gravaity

# 文档处理
FRONTEND_IMAGES_DIR=./frontend/public/documents/images
FRONTEND_IMAGE_PREFIX=/documents/images
VECTOR_COLLECTION=pdf_documents
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

#### 1.3 初始化数据库

```bash
# 确保 pgvector 已启用
psql -U postgres -d gravaity -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### 1.4 启动后端

```bash
python ./start_backend.py
```

后端运行在 `http://0.0.0.0:8000`

### 2. 前端安装与运行

#### 2.1 安装 Node 依赖

```bash
cd frontend
npm install
```

#### 2.2 启动开发服务器

```bash
npm run dev
```

前端运行在 `http://localhost:5173`

### 3. 文档处理与向量嵌入

#### 3.1 使用 MinerU 解析 PDF

使用 MinerU 解析 PDF 文件（生成 Markdown + 图片）：

```bash
# MinerU 安装与使用详见: https://github.com/opendatalab/MinerU
mineru --pdf /path/to/document.pdf --output-dir ./data/ocr/
```

输出结构：
```
data/ocr/document_name/
├── auto/
│   ├── document.md          # 解析后的 Markdown
│   └── images/              # 提取的图片
│       ├── xxx.jpg
│       └── yyy.jpg
```

#### 3.2 通过 API 处理文档并嵌入向量

```bash
curl -X POST http://localhost:8000/documents/process-mineru \
  -H "Content-Type: application/json" \
  -d '{
    "source_path": "./data/ocr/document_name",
    "embed": true,
    "collection_name": "pdf_documents"
  }'
```

**参数说明**：
- `source_path`: MinerU 输出目录的**父目录**（包含 `auto/` 子目录）
- `embed`: 是否嵌入向量库（true/false）
- `collection_name`: 向量集合名称

**响应示例**：
```json
{
  "status": "success",
  "message": "Document processed successfully",
  "images_copied": 15,
  "chunks_created": 23,
  "collection_name": "pdf_documents"
}
```

#### 3.3 验证嵌入结果

在聊天界面提问，系统会自动检索相关文档并显示（包括图片）。

### 4. 对话与检索

#### 4.1 通过 Web UI 对话

打开 `http://localhost:5173`，输入问题。系统会：
1. 自动判断是否需要检索文档
2. 从向量库检索相关内容
3. 基于检索结果生成答案
4. 支持 Markdown 渲染（包括图片、表格、代码块）

#### 4.2 通过 API 对话

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "user-123",
    "message": "文档中提到了什么关键技术？"
  }'
```

#### 4.3 查看对话历史

```bash
curl http://localhost:8000/chat/threads/user-123/history
```

## 后续扩展方向

- **Agentic RAG 完整流程**：增加 `grade_documents` / `rewrite_question` 等节点（参考官方教程）
- **长期记忆（跨线程 Store）**：基于 `src/db/memory_store.py` 注入 `AsyncPostgresStore`，在节点中通过 `store: BaseStore` + `config: RunnableConfig` 做用户记忆的读写（参考官方 [Add Memory 文档](https://docs.langchain.com/oss/python/langgraph/add-memory)）
- **API 层**：在 `src/api/` 中使用 FastAPI 封装对 `graph` 的 `ainvoke/astream` 调用

## 常见问题

### Q: 如何处理 JSON 路径转义错误？

在 curl 中使用正斜杠或双反斜杠：

```bash
# ✅ 推荐：使用正斜杠
curl -X POST http://localhost:8000/documents/process-mineru \
  -H "Content-Type: application/json" \
  -d '{"source_path": "./data/ocr/document_name", "embed": true}'

# ✅ 也可以：Windows 双反斜杠
curl -X POST http://localhost:8000/documents/process-mineru \
  -H "Content-Type: application/json" \
  -d "{\"source_path\": \"D:\\\\code\\\\gravaity\\\\data\\\\ocr\\\\document_name\", \"embed\": true}"
```

### Q: 图片没有显示？

检查以下几点：
1. 确保 `FRONTEND_IMAGES_DIR` 指向正确的目录（`./frontend/public/documents/images`）
2. 确保后端从项目根目录启动（使用 `python ./start_backend.py`）
3. 检查前端是否已安装 `react-markdown` 依赖

### Q: 向量嵌入失败？

常见原因：
1. OpenAI API Key 无效或配额不足
2. 网络连接问题（特别是 tiktoken 下载）
3. 文档过大导致 token 超限

解决方案：
```bash
# 预先缓存 tiktoken 编码
python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"
```

## 参考资源

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph Agentic RAG 教程](https://docs.langchain.com/oss/python/langgraph/agentic-rag)
- [MinerU 项目](https://github.com/opendatalab/MinerU)
- [PGVector 文档](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)

## 许可证

MIT License
