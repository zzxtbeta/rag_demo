---
description: Deploy Gravaity API on Alibaba Cloud ECS (reuse existing Postgres/Redis)
---

# Gravaity API 阿里云 ECS 部署（复用现有 Postgres / Redis）

本教程目标：在一台已运行 `cybernaut_postgres:5432`、`cybernaut_redis:6379` 的 ECS 上，**只部署一个新的 `gravaity-api` 容器**，且端口不冲突。

> 说明：本项目的 `docker-compose.yml` 已做成“默认只起 API 服务”。`langgraph-postgres` / `langgraph-redis` 仅在 `local` profile 下启动，服务器部署无需启用。

---

## 0. 前置条件

- ECS 系统：Ubuntu / Debian / CentOS 均可（示例命令以 Ubuntu 为主）
- ECS 已安装并运行 Docker
- ECS 已运行现有容器：
  - Postgres：对外暴露 `0.0.0.0:5432`
  - Redis：对外暴露 `0.0.0.0:6379`

你已经确认：
- `cybernaut_postgres` 映射 `5432:5432`
- `cybernaut_redis` 映射 `6379:6379`

---

## 1. 在 ECS 安装 Docker 与 Compose（如已安装可跳过）

### Ubuntu / Debian

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 重新登录一次 SSH 让组权限生效，然后确认
docker version

docker compose version
```

> 如果 `docker compose version` 不存在，通常是 Docker 版本过旧；建议升级 Docker 到 20.10+。

---

## 2. 准备部署目录与代码

任选一种：

### 方式 A：Git 拉取（推荐）

```bash
mkdir -p ~/workspace
cd ~/workspace

git clone <你的仓库地址> gravaity
cd gravaity
```

### 方式 B：本地打包上传

- 在本地把 `gravaity` 项目目录打包上传到 ECS
- 在 ECS 解压到 `~/workspace/gravaity`

---

## 3. 端口规划（避免冲突）

你服务器已有：
- `8001`（cybernaut_api）
- `5555`（flower）
- `5432`（postgres）
- `6379`（redis）

Gravaity API 容器内部固定监听 `8000`，对外映射由 `GRAVAITY_API_PORT` 控制。

推荐：
- `GRAVAITY_API_PORT=8123`（如果冲突就换 8124/8125…）

---

## 4. 创建 Gravaity 专用 `.env`（关键步骤）

在 ECS 的 `~/workspace/gravaity` 目录下创建 `.env`：

```bash
cd ~/workspace/gravaity
nano .env
```

### 4.1 必需环境变量（缺一个就会启动失败/不可用）

- `POSTGRES_CONNECTION_STRING`（必填）
  - 用于：LangGraph checkpointer + PGVector 向量库
- `DASHSCOPE_API_KEY`（必填）
  - 用于：LLM 调用 + DashScope Embeddings

> 注意：本项目当前 embeddings 使用的是 `DashScopeEmbeddings`（见 `src/agent/vectorstore.py`）。因此 **`OPENAI_EMBEDDINGS_API_KEY` 在当前代码路径里不会被读取**，你可以不填它。

### 4.2 强烈建议环境变量（不填会导致流式/stream 相关接口不可用）

- `REDIS_URL`（建议填）
  - 用于：`/chat/stream` 以及流式事件发布（`src/infra/redis_pubsub.py`）

### 4.3 可选环境变量

- LangSmith tracing（可选）：
  - `LANGCHAIN_API_KEY`
  - `LANGSMITH_PROJECT`
  - `LANGSMITH_TRACING`
  - `LANGSMITH_ENDPOINT`

- 模型/检索参数（可选，均有默认值）：
  - `CHAT_MODEL`（默认 `qwen-plus-latest`）
  - `DASHSCOPE_BASE_URL`（默认 `https://dashscope.aliyuncs.com/compatible-mode/v1`）
  - `EMBEDDINGS_MODEL`（默认 `text-embedding-v4`）
  - `VECTOR_COLLECTION`（默认 `bp_pdf`）
  - `CHUNK_SIZE` / `CHUNK_OVERLAP` / `RETRIEVER_TOP_K`
  - `RERANK_ENABLED` / `RERANK_MODEL` / `RERANK_TOP_N`
  - `REDIS_STREAM_ENABLED` / `STREAM_TTL_SECONDS` / `STREAM_MAX_LENGTH`
  - `WORKFLOW_TIMEOUT_SECONDS`
  - `FRONTEND_IMAGES_DIR` / `FRONTEND_IMAGE_PREFIX`
  - `PROJECT_SEARCH_*`
  - `TAVILY_API_KEY`

### 4.4 推荐 `.env` 模板（直接复制修改）

把下面内容粘贴到 `.env`，然后**把密码、库名、key 改成你的真实值**：

```env
# === Docker/Compose ===
GRAVAITY_API_PORT=8123

# === Database (Required) ===
# 复用本机 cybernaut_postgres 映射端口 5432
POSTGRES_CONNECTION_STRING=postgresql://postgres:<POSTGRES_PASSWORD>@host.docker.internal:5432/<DB_NAME>?sslmode=disable

# === Redis (Recommended) ===
# 复用本机 cybernaut_redis 映射端口 6379
REDIS_URL=redis://host.docker.internal:6379/0

# === LLM + Embeddings (Required) ===
DASHSCOPE_API_KEY=<YOUR_DASHSCOPE_API_KEY>
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CHAT_MODEL=qwen-plus-latest
EMBEDDINGS_MODEL=text-embedding-v4

# === Vector Store ===
VECTOR_COLLECTION=bp_pdf

# === LangSmith (Optional) ===
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_PROJECT=gravaity
LANGCHAIN_API_KEY=<YOUR_LANGSMITH_API_KEY>

# === Streaming switches (Optional) ===
REDIS_STREAM_ENABLED=false
STREAM_TTL_SECONDS=3600
STREAM_MAX_LENGTH=1000
WORKFLOW_TIMEOUT_SECONDS=300

# === Rerank (Optional) ===
RERANK_ENABLED=false
RERANK_MODEL=qwen3-rerank
RERANK_TOP_N=3

# === Document processing (Optional) ===
FRONTEND_IMAGES_DIR=./frontend/public/documents/images
FRONTEND_IMAGE_PREFIX=/documents/images

# === Web search (Optional) ===
TAVILY_API_KEY=

# === Project search (Optional) ===
PROJECT_SEARCH_ENABLED=false
PROJECT_SEARCH_API_URL=
PROJECT_SEARCH_API_USERNAME=
PROJECT_SEARCH_API_PASSWORD=
PROJECT_SEARCH_DB_URL=
```

---

## 5. 启动容器

在 ECS 上执行：

```bash
cd ~/workspace/gravaity

# 构建 + 启动（默认只启动 gravaity-api，因为 postgres/redis 都是 local profile）
docker compose up -d --build

# 查看状态
docker ps

# 看日志（确认没有缺少 env 的报错）
docker compose logs -f gravaity-api
```

---

## 6. 验证部署是否成功

### 6.1 容器内健康检查

`docker compose.yml` 里 healthcheck 会请求：
- `http://localhost:8000/docs`（容器内）

你也可以手动：

```bash
docker compose ps
```

看 `gravaity-api` 是否为 `healthy`。

### 6.2 从 ECS 宿主机访问

```bash
curl -f http://127.0.0.1:${GRAVAITY_API_PORT:-8123}/docs
```

### 6.3 从公网访问

确保 ECS 安全组放行 `GRAVAITY_API_PORT`（比如 8123/TCP）。然后访问：

- `http://<你的ECS公网IP>:8123/docs`

---

## 7. 常见问题排查

### 7.1 容器启动立刻退出：缺环境变量

最常见是缺少必填：
- `POSTGRES_CONNECTION_STRING`
- `DASHSCOPE_API_KEY`

查看日志：

```bash
docker compose logs --tail=200 gravaity-api
```

### 7.2 数据库连不上

确认宿主机端口可用：

```bash
# 如果 ECS 上装了 psql 客户端
psql -h 127.0.0.1 -p 5432 -U postgres -d <DB_NAME>
```

并确认你的 `POSTGRES_CONNECTION_STRING`：
- host 用 `host.docker.internal`
- 端口 5432
- 用户/密码/库名正确

### 7.3 Redis 报 REDIS_URL is not configured

说明你调用了需要 Redis 的功能（如 `/chat/stream`）但 `.env` 没填 `REDIS_URL`。

### 7.4 LangSmith key 不生效

本项目读取的是：
- `LANGCHAIN_API_KEY`

不是 `LANGSMITH_API_KEY`。

---

## 8. 生产化建议（可选）

- 使用反向代理（Nginx/Caddy）
  - 统一走 80/443
  - 把 `/` 反代到 `127.0.0.1:${GRAVAITY_API_PORT}`
- `.env` 里不要提交任何真实 key
- 定期更新镜像、开启日志收集
