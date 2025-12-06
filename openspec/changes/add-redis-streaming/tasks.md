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
- [x] 6.2 实现 `/chat/threads/{thread_id}/history` API，基于 thread_id 查询历史消息。
- [x] 6.3 实现 `/chat/threads/{thread_id}` (DELETE) API，删除线程的所有 checkpoint 数据。

## 7. 流式输出优化
- [x] 7.1 修复流式输出顺序问题，使用 `stream_mode=["updates", "messages"]` 混合模式
- [x] 7.2 确保节点状态更新（updates）和 token 流式输出（messages）正确分离处理
- [x] 7.3 修复前端消息显示顺序，确保节点步骤在 AI 回复之前显示

## 8. 动态模型选择
- [x] 8.1 后端支持通过 `chat_model` 参数动态选择模型
- [x] 8.2 统一模型命名（`CHAT_MODEL`），移除 `MODEL_NAME` 和 `AGENT_MODEL` 重复
- [x] 8.3 前端添加模型选择器，支持切换不同模型（qwen-plus-latest, qwen-max-latest, qwen-flash）

## 9. 工具使用优化
- [x] 9.1 优化系统提示词，明确要求使用 `retrieve_context` 工具
- [x] 9.2 更新工具描述，明确使用场景和调用时机
- [x] 9.3 在系统提示中列出所有可用工具

