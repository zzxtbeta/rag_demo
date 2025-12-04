## 1. Redis 集成
- [x] 1.1 引入 `redis.asyncio` 依赖，封装 Redis publisher/client，支持配置 `REDIS_URL`（默认 DB=2）。
- [x] 1.2 设计消息格式（字段含 `thread_id`/`node_name`/`message_type` 等）并提供发布工具函数。

## 2. LangGraph 流式发布
- [x] 2.1 在 `/chat/stream` 流程中使用 `thread_id` 调用 `graph.astream(...)`。
- [x] 2.2 对每个 chunk 推送 `workflow:{thread_id}:{node}:{message_type}`，完成/错误分别推送 `workflow:{thread_id}:workflow:complete` / `workflow:{thread_id}:workflow:error`。
- [x] 2.3 请求返回 `thread_id` 供前端订阅；保留最终同步返回逻辑。

## 3. 订阅接口
- [x] 3.1 新增 WebSocket 端点 `/ws/{thread_id}` 作为 Redis Pub/Sub 代理，后端订阅 `workflow:{thread_id}:*`。
- [x] 3.2 提供基础的订阅/取消逻辑，确保多客户端隔离（基于 thread_id）。

## 4. 消息序列化优化
- [x] 4.1 修复 AIMessage 序列化问题：使用 `__dict__.copy()` + `json.dumps(default=...)` 替代 `asdict()`。
- [x] 4.2 使用 `message_to_dict()` 处理 LangChain 消息对象，确保 JSON 可序列化。
- [x] 4.3 添加单元测试验证序列化功能。

## 5. 配置与文档
- [x] 5.1 在 `.env.example`、README 中说明 `REDIS_URL`、频道命名与消息结构。
- [x] 5.2 更新启动脚本/说明，确保 Redis 依赖检测与 thread_id 使用方式被记录。

## 6. 验证与历史能力
- [x] 6.1 编写单元测试验证节点→Redis→WebSocket 的实时链路。
- [ ] 6.2 演示如何使用 `graph.get_state_history` 基于 thread_id 查询历史，确保多次执行/恢复场景正常工作。

