# 文档处理指南

## 概述

Gravaity RAG 系统采用 **MinerU** 作为主要的文档处理方法，用于将 PDF 转换为结构化的 Markdown 和图片，然后进行向量嵌入和检索。

## 核心概念

### 什么是 MinerU？

MinerU 是一个高精度的文档解析工具，能够：
- 将 PDF 转换为结构化的 Markdown 格式
- 自动提取和保存图片
- 保留原始文档的逻辑结构（标题、表格、列表等）
- 支持复杂排版和多模态内容

### 为什么选择 MinerU？

相比传统的 PyPDF 方法：

| 特性 | MinerU | PyPDF |
|------|--------|-------|
| 结构保留 | ✅ 完整保留 | ❌ 丢失 |
| 图片处理 | ✅ 自动提取 | ❌ 无法处理 |
| 表格识别 | ✅ 转为 HTML | ❌ 无法识别 |
| 语义理解 | ✅ Markdown 格式 | ❌ 纯文本 |
| 准确度 | ✅ 高（深度学习） | ⚠️ 一般（规则解析） |

## 处理流程

```
PDF 文件
    ↓
[MinerU 解析]
    ├─ 输出: Markdown 文件
    └─ 输出: 图片目录
    ↓
[MineruProcessor 处理]
    ├─ 复制图片到前端目录
    ├─ 更新 Markdown 中的图片路径
    ├─ 按 Markdown 结构分块
    └─ 嵌入到向量库（可选）
    ↓
[向量库 (PGVector)]
    ├─ 存储文档块
    └─ 支持语义检索
    ↓
[RAG Agent]
    ├─ 接收用户问题
    ├─ 检索相关文档
    └─ 生成答案
```

## 使用方法

### 第一步：安装 MinerU

```bash
# 参考官方文档
# https://github.com/opendatalab/MinerU?tab=readme-ov-file
uv pip install -U "mineru[core]"
```

### 第二步：解析 PDF

```bash
# 使用 MinerU 解析 PDF
mineru -p <input_path> -o <output_path>
```

输出结构：
```
mineru_output/
└── auto/
    ├── your_document.md          # 解析后的 Markdown
    └── images/                   # 提取的图片
        ├── image1.jpg
        ├── image2.jpg
        └── ...
```

### 第三步：调用处理 API

**关键概念**：`source_path` 是指 MinerU 输出的**父目录**（包含 `auto/` 子目录的目录）

以你的具体例子为例：
```
d:\code\gravaity\data\ocr\象量科技项目介绍20250825/     ← 这是 source_path
└── auto/                                              ← 处理器会自动查找这个子目录
    ├── 象量科技项目介绍20250825.md                     ← Markdown 文件
    └── images/                                        ← 图片目录
        ├── image1.jpg
        ├── image2.jpg
        └── ...
```

#### 使用 Python

```python
import requests

# 处理并嵌入到向量库
response = requests.post(
    "http://localhost:8000/documents/process-mineru",
    json={
        "source_path": "d:\\code\\gravaity\\data\\ocr\\象量科技项目介绍20250825",
        "embed": True,
        "collection_name": "my_documents"
    }
)

result = response.json()
print(f"复制图片: {result['images_copied']} 张")
print(f"创建文档块: {result['chunks_created']} 个")
print(f"嵌入到集合: {result['collection_name']}")
```

或使用相对路径（相对于项目根目录）：
```python
response = requests.post(
    "http://localhost:8000/documents/process-mineru",
    json={
        "source_path": "./data/ocr/象量科技项目介绍20250825",
        "embed": True,
        "collection_name": "my_documents"
    }
)
```

#### 使用 cURL

```bash
curl -X POST http://localhost:8000/documents/process-mineru \
  -H "Content-Type: application/json" \
  -d '{
    "source_path": "d:\\code\\gravaity\\data\\ocr\\象量科技项目介绍20250825",
    "embed": true,
    "collection_name": "my_documents"
  }'
```

或使用相对路径：
```bash
curl -X POST http://localhost:8000/documents/process-mineru \
  -H "Content-Type: application/json" \
  -d '{
    "source_path": "./data/ocr/象量科技项目介绍20250825",
    "embed": true,
    "collection_name": "my_documents"
  }'
```

### 第四步：验证

```bash
# 检查向量库中的文档数量
# 使用 RAG Agent 进行查询测试
POST /chat
{
  "thread_id": "test",
  "message": "文档中提到了什么？"
}
```

## API 端点详解

### POST /documents/process-mineru

**功能**：处理 MinerU 解析的文档，包括图片复制、路径更新、分块和可选的向量嵌入。

**请求参数**：

```json
{
  "source_path": "/path/to/mineru/output",  // 必需：MinerU 输出的父目录（包含 auto/ 子目录）
  "embed": true,                             // 可选：是否进行向量嵌入（默认 false）
  "collection_name": "my_documents"          // 可选：向量库集合名（不指定则使用默认）
}
```

**source_path 说明**：

指向 MinerU 解析输出的**父目录**，该目录应包含 `auto/` 子目录。

例如：
```
source_path = "d:\code\gravaity\data\ocr\象量科技项目介绍20250825"
    ↓
    包含以下结构：
    ├── auto/
    │   ├── document.md
    │   └── images/
    │       ├── image1.jpg
    │       └── ...
```

处理器会自动：
1. 查找 `source_path/auto/` 目录
2. 读取其中的 `.md` 文件
3. 复制 `auto/images/` 中的所有图片

**响应**：

```json
{
  "status": "success",
  "message": "Document processed successfully",
  "images_copied": 30,           // 复制的图片数量
  "chunks_created": 150,         // 创建的文档块数量
  "embedded": true,              // 是否已嵌入
  "collection_name": "my_documents"  // 使用的集合名
}
```

**错误响应**：

```json
{
  "status": "error",
  "message": "Document processing failed",
  "error": "Source directory not found: /invalid/path"
}
```

## 处理步骤详解

### 1. 图片复制

- **源**：`source_path/auto/images/`
- **目标**：`FRONTEND_IMAGES_DIR`（环境变量配置）
- **作用**：使前端能够访问和显示图片

### 2. 路径更新

- **原始**：`![](images/xxx.jpg)`
- **更新后**：`![]({FRONTEND_IMAGE_PREFIX}/xxx.jpg)`
- **作用**：确保前端能正确加载图片

### 3. 内容分块

- **方法**：`RecursiveCharacterTextSplitter`
- **优先级**：按 Markdown 标题结构分割
  - 一级标题 `\n# `
  - 二级标题 `\n## `
  - 三级标题 `\n### `
  - 段落 `\n\n`
  - 行 `\n`
  - 词 ` `
  - 字符 ``
- **参数**：
  - `chunk_size`：块大小（默认 1000 字符）
  - `chunk_overlap`：块重叠（默认 200 字符）

### 4. 向量嵌入（可选）

- **条件**：`embed=true`
- **模型**：OpenAI text-embedding-3-large
- **存储**：PGVector（PostgreSQL）
- **集合**：指定的 `collection_name`

## 配置说明

### 环境变量

在 `.env` 文件中配置：

```env
# 文档处理配置
FRONTEND_IMAGES_DIR=./frontend/public/documents/images
FRONTEND_IMAGE_PREFIX=/documents/images

# 向量库配置
VECTOR_COLLECTION=pdf_documents
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
RETRIEVER_TOP_K=4

# PostgreSQL 配置
POSTGRES_CONNECTION_STRING=postgresql://user:password@host:5432/db
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `FRONTEND_IMAGES_DIR` | 前端图片存储目录 | `./frontend/public/documents/images` |
| `FRONTEND_IMAGE_PREFIX` | 前端图片访问前缀 | `/documents/images` |
| `CHUNK_SIZE` | 文档块大小（字符） | 1000 |
| `CHUNK_OVERLAP` | 块重叠大小（字符） | 200 |
| `RETRIEVER_TOP_K` | 检索返回的文档数 | 4 |

## 代码位置

- **处理器**：`src/utils/mineru_processor.py`
  - `MineruProcessor` 类：核心处理逻辑
  - `ProcessingRequest` 类：请求数据模型
  - `ProcessingResponse` 类：响应数据模型

- **API 路由**：`src/api/routes/documents.py`
  - `POST /documents/process-mineru` 端点

- **向量存储**：`src/agent/vectorstore.py`
  - `get_vector_store()` 函数：获取向量库实例
  - `get_embeddings()` 函数：获取嵌入模型

## 常见问题

### Q: 调用 API 时出现 "JSON decode error: Invalid \escape"？

A: 这是 JSON 转义问题。在 JSON 中，反斜杠 `\` 需要转义为 `\\`。

**错误示例**：
```json
{
  "source_path": "D:\code\gravaity\data\ocr\象量科技项目介绍20250825"
}
```

**正确示例**（三选一）：

1. **转义反斜杠**：
```json
{
  "source_path": "D:\\code\\gravaity\\data\\ocr\\象量科技项目介绍20250825",
  "embed": false,
  "collection_name": "pdf_documents"
}
```

2. **使用相对路径**（推荐）：
```json
{
  "source_path": "./data/ocr/象量科技项目介绍20250825",
  "embed": false,
  "collection_name": "pdf_documents"
}
```

3. **使用正斜杠**（Windows 也支持）：
```json
{
  "source_path": "D:/code/gravaity/data/ocr/象量科技项目介绍20250825",
  "embed": false,
  "collection_name": "pdf_documents"
}
```

### Q: 为什么要分离 `embed` 参数？

A: 有时你只想处理文档（复制图片、更新路径、分块），但不想立即嵌入。这样可以：
- 先预览处理结果
- 批量处理多个文档后再统一嵌入
- 分离关注点，提高灵活性

### Q: 图片在前端如何显示？

A: 处理器会：
1. 复制图片到 `FRONTEND_IMAGES_DIR`
2. 更新 Markdown 中的图片路径
3. 前端可以直接访问 `{FRONTEND_IMAGE_PREFIX}/image.jpg`

### Q: 支持哪些图片格式？

A: MinerU 支持 PDF 中的所有图片格式（JPG、PNG、GIF 等），处理器会原样复制。

### Q: 如何处理多个 PDF？

A: 对每个 PDF：
1. 用 MinerU 解析
2. 调用 API 处理
3. 可以指定不同的 `collection_name` 来分类存储

### Q: 向量库中的文档如何更新？

A: 当前系统支持追加（`add_documents`）。如需更新或删除，可以：
- 删除整个集合重新创建
- 或使用 PostgreSQL 直接操作

## 后续扩展

如果需要支持其他文档处理方法（如 Unstructured），可以：

1. 在 `src/utils/` 中创建新的 processor（如 `unstructured_processor.py`）
2. 实现相同的接口（`process()` 方法）
3. 在 `src/api/routes/documents.py` 中添加新的 API 端点
4. 更新本文档

## 遗留方法（不推荐）

### PyPDF 方法（已弃用）

**位置**：`scripts/init_vectorstore.py`

**状态**：仅用于向后兼容，不推荐用于新项目

**使用**：
```bash
python -m scripts.init_vectorstore --pdf-dir ./data
```

**限制**：
- 无法保留文档结构
- 无法处理图片
- 无法识别表格
- 准确度较低

## 总结

- ✅ 使用 MinerU 处理 PDF
- ✅ 调用 `/documents/process-mineru` API
- ✅ 可选择是否嵌入到向量库
- ✅ Agent 自动使用向量库进行检索
- ✅ 前端可以显示图片和结构化内容
