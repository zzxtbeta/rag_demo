# Change: Add Redis-based streaming pipeline

## Why
### 用户视角
- 现状：用户发起工作流（例如生成 margin check 报告）时，需要等待 3~5 秒才能看到最终结果。
- 痛点：流程包含多个 LangGraph 节点（查询仓位→AI 分析→生成报告），但前端无法感知节点级进度，体验类似“黑盒”。在关键任务（风控、合规）场景下，用户希望在 100~200ms 内看到“节点已完成”提示，以便确认系统正在工作。

### 技术视角
- LangGraph 支持 `astream()`/`stream()` 输出节点级 chunk，但当前 API 直接 `ainvoke()`，无法向前端推送中间结果。
- 我们需要一个生产级方案，使每个节点完成后立即将输出写入 message bus，并提供清晰的 channel/消息格式，方便多端订阅、监控与调试。
- Redis Pub/Sub 满足低延迟、多订阅者、顺序保证等需求，且团队已有 Redis 基础设施（`REDIS_URL=redis://:200105@172.26.18.38:6379/2`，db2 未被占用）。

## What Changes
1. **标识体系与频道命名（thread_id 为核心）**
   - 使用 `workflow:{thread_id}:{node_name}:{message_type}`，示例：
     - `workflow:thread_user123_session:fetch_position:output`
     - `workflow:thread_user123_session:workflow:complete`
   - `thread_id`：LangGraph 官方推荐的会话标识，与 checkpointer 紧密绑定，可重复执行/恢复历史。
   - `node_name`：映射 LangGraph 节点，便于前端精确渲染。
   - `message_type`：`output`/`progress`/`error` 等，区分不同事件。

2. **消息结构（JSON）**
   ```json
   {
     "thread_id": "thread_user_123_session_1",
     "node_name": "fetch_position",
     "message_type": "output",
     "status": "completed",
     "timestamp": 1705740000.123,
     "execution_time_ms": 1234,
     "data": { ...业务数据... }
   }
   ```
   - 统一字段，便于前端/日志/监控解析；`thread_id` 可用于 LangGraph 状态/历史查询。
   - **AIMessage 序列化处理**：
     - `data.messages` 数组中包含 LangChain `AIMessage` 对象时，使用 `message_to_dict()` 转换为 JSON 可序列化格式。
     - 转换后的格式：`{"type": "ai", "data": {"content": "...", ...}}`。
     - 前端从 `data.messages` 中提取 `type: "ai"` 的消息，显示为助手回复。
     - 使用 `__dict__.copy()` + `json.dumps(default=...)` 避免 `asdict()` 递归问题。

3. **LangGraph ↔ Redis 流式管道**
- 在 `/chat` 中调用 `graph.astream(...)`，传入 `{"configurable": {"thread_id": thread_id}}`，LangGraph 自动持久化会话状态。
- 每个 chunk 发布至 `workflow:{thread_id}:{node_name}:{message_type}`；完成/错误分别推送 `workflow:{thread_id}:workflow:complete` / `workflow:{thread_id}:workflow:error`。

4. **订阅接口**
- 新增 WebSocket（或 SSE）端点作为 Redis Pub/Sub 代理：后端订阅 `workflow:{thread_id}:*`，推送给前端。
- `/chat` 返回 `thread_id`，前端基于该标识订阅所有节点输出。

5. **配置与文档**
   - 在 `.env.example`、README 中说明 `REDIS_URL`、频道命名规则、消息格式、前端接入示例。
   - 脚本/启动说明补充 Redis 依赖检测。

## Impact
- 代码范围：`api/routes/chat.py`（流式执行）、新增 `api/routes/stream.py`（WebSocket）、`infra/redis.py`（pub/sub 工具）、配置/脚本/文档。
- 新依赖：`redis[asyncio]`（或 `redis` 4.x 带 asyncio 支持）。
- 部署：需要 Redis 可达性与适当的 channel 命名策略；DB 默认使用 2（避免与 db0/db1 冲突）。
- 行为变化：`/chat` 将返回 `thread_id`，前端基于该标识订阅频道，实现节点级实时显示；同时保留 LangGraph 原生状态恢复能力。

