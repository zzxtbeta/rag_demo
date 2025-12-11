# Change: Refactor Redis Pub/Sub to Stream for Persistent Workflow Events

## Why

### 问题背景
当前系统使用 Redis Pub/Sub 实现工作流节点事件的实时推送。虽然满足基本的实时需求，但存在以下关键问题：

1. **消息丢失**：Pub/Sub 不持久化消息。如果客户端在事件发布时网络中断或页面刷新，会错过这些事件。特别是在生产环境中，用户无法看到完整的执行轨迹。

2. **无法续订**：断线重连后，系统无法知道从哪个位置继续读取消息。用户必须重新执行工作流才能获得新的事件。

3. **无历史查询**：无法回溯已执行的节点，用户无法查看完整的执行历史和调试信息。

4. **竞态条件**：当前的"历史 + 实时"混合方案存在时间窗口问题，可能导致消息重复或丢失。

### 机会
Redis Stream（Redis 5.0+）专门为解决这类问题而设计，提供：
- 原生消息持久化
- 自动续订支持（通过消息 ID）
- 完整的历史查询能力
- 自动清理机制（XTRIM）
- 消费者组支持（未来扩展）

这是一个**架构优化**，提升系统可靠性和用户体验，无需改变 API 契约。

## What Changes

### 核心改动
1. **发布机制**：从 `PUBLISH` 改为 `XADD`
   - 消息自动持久化到 Stream
   - 自动生成唯一的消息 ID
   - 支持 XTRIM 自动清理

2. **订阅机制**：从 `SUBSCRIBE` 改为 `XREAD` + `XRANGE`
   - 先读取历史消息（XRANGE）
   - 再阻塞读取新消息（XREAD）
   - 支持从任意位置续订

3. **频道命名**：统一为 Stream key
   - 从：`workflow:{thread_id}:{node_name}:{message_type}`
   - 到：`workflow:execution:{thread_id}`
   - 消息类型和节点名称放在消息字段中

4. **消息格式**：保持兼容，字段放在 Stream 字段中
   - `node_name`、`message_type`、`status`、`timestamp`、`data` 等

### 不破坏性改动
- WebSocket 接口保持不变（`/ws/{thread_id}`）
- 前端接收的消息格式保持兼容
- 现有 API 端点无需修改
- 逐步迁移，可与 Pub/Sub 并存

## Impact

### 受影响的代码
- `src/infra/redis_pubsub.py`：RedisPublisher 实现
- `src/api/routes/stream.py`：WebSocket 订阅逻辑
- `src/api/routes/chat.py`：事件发布调用（无需改动）
- 配置：可选的 REDIS_STREAM_ENABLED 开关

### 受影响的规范
- `specs/workflow-streaming/spec.md`：新增 Redis Stream 持久化要求

### 部署影响
- Redis 版本要求：5.0+（大多数环境已满足）
- 无数据迁移需求（Stream 和 Pub/Sub 可并存）
- 无性能影响（Stream 性能与 Pub/Sub 相当）

### 用户体验改进
- ✅ 页面刷新后可恢复历史事件
- ✅ 网络中断后自动续订
- ✅ 支持查看完整执行历史
- ✅ 支持工作流执行回放
