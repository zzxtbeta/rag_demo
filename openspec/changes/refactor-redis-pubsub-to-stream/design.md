# Design: Redis Stream Migration for Workflow Events

## Context

### 背景
Gravaity 项目使用 FastAPI + LangGraph 构建智能体工作流系统。当前通过 Redis Pub/Sub 实现节点级事件的实时推送，但存在消息丢失和无法续订的问题。

### 约束条件
1. **Redis 版本**：需要 5.0+（支持 Stream）
2. **向后兼容**：不能破坏现有 API 契约
3. **性能**：不能降低实时推送的延迟
4. **迁移**：需要支持平滑过渡，可与 Pub/Sub 并存

### 相关方
- 前端：需要接收完整的事件历史和实时更新
- 后端：需要发布和订阅事件
- 运维：需要管理 Redis 资源

## Goals / Non-Goals

### Goals
- ✅ 实现消息持久化，支持历史查询
- ✅ 支持断线续订，自动恢复未读消息
- ✅ 保持 WebSocket 接口兼容
- ✅ 支持自动清理，防止内存泄漏
- ✅ 提供迁移路径，支持灰度发布

### Non-Goals
- ❌ 不改变 API 契约（`/ws/{thread_id}` 保持不变）
- ❌ 不引入消费者组（Consumer Groups）
- ❌ 不支持跨 Redis 实例的分布式 Stream
- ❌ 不改变消息格式（保持 JSON 兼容）

## Decisions

### Decision 1: Stream Key 命名规范

**决策**：使用单一 Stream key 存储所有节点事件
```
workflow:execution:{thread_id}
```

**理由**：
- 简化订阅逻辑（一个 key 而非多个频道）
- 保证消息顺序（单个 Stream 内顺序保证）
- 便于历史查询（XRANGE 一次获取所有事件）

**替代方案**：
- 方案 A：多个 Stream key（`workflow:execution:{thread_id}:{node_name}`）
  - 优点：可并行读取不同节点的事件
  - 缺点：复杂度高，需要多次 XREAD，难以保证全局顺序
- 方案 B：单一全局 Stream（`workflow:events`）
  - 优点：简单
  - 缺点：无法隔离不同线程，性能差

**选择理由**：方案 1 最佳平衡了简洁性和功能性。

---

### Decision 2: 消息字段结构

**决策**：消息类型和节点名称放在 Stream 字段中
```python
{
    "node_name": "query_or_respond",
    "message_type": "token",
    "status": "streaming",
    "timestamp": "1705740000.123",
    "data": "{...json...}",
    "execution_time_ms": "1333"
}
```

**理由**：
- 保持与现有 StreamMessage 数据结构兼容
- 便于前端解析（相同的字段名）
- 支持灵活的查询和过滤

**替代方案**：
- 方案 A：嵌套 JSON（data 中包含所有字段）
  - 缺点：需要解析两层 JSON，性能差
- 方案 B：扁平化所有字段
  - 缺点：字段过多，难以维护

---

### Decision 3: 历史消息读取策略

**决策**：先读历史（XRANGE），再阻塞读新消息（XREAD）
```python
# 1. 读取所有历史消息
messages = await redis.xrange(stream_key)
for message_id, fields in messages:
    yield parse_event(fields)

# 2. 阻塞读取新消息
streams = await redis.xread({stream_key: last_id}, block=1000)
```

**理由**：
- 保证客户端收到完整的事件序列
- 避免竞态条件（历史 + 实时的时间窗口）
- 支持页面刷新后恢复历史

**替代方案**：
- 方案 A：只读新消息（XREAD from 0-0）
  - 缺点：客户端连接时错过历史事件
- 方案 B：使用消费者组（XREADGROUP）
  - 缺点：复杂度高，需要管理消费者状态

---

### Decision 4: 自动清理策略

**决策**：使用 XTRIM 和 EXPIRE 组合
```python
# 限制 Stream 长度
await redis.xtrim(stream_key, maxlen=1000, approximate=True)
# 设置过期时间（1 小时）
await redis.expire(stream_key, 3600)
```

**理由**：
- XTRIM：防止 Stream 无限增长
- EXPIRE：自动清理过期的 Stream key
- approximate=True：性能更好（不精确删除）

**参数选择**：
- maxlen=1000：足以存储 1 小时内的所有节点事件（通常 100-500 条）
- expire=3600：与工作流超时时间对齐（WORKFLOW_TIMEOUT_SECONDS）

---

### Decision 5: 迁移策略

**决策**：使用功能开关（Feature Flag）支持灰度迁移
```python
# 配置
REDIS_STREAM_ENABLED=true  # 默认 false

# 发布时同时支持两种方式
if settings.redis_stream_enabled:
    await redis.xadd(stream_key, event)
await redis.publish(channel, event_json)  # 保留 Pub/Sub

# 订阅时优先使用 Stream
if settings.redis_stream_enabled:
    # 使用 Stream 逻辑
else:
    # 使用 Pub/Sub 逻辑
```

**理由**：
- 支持平滑过渡，无需一次性切换
- 可观察两种方式的性能差异
- 快速回滚（禁用开关即可）

---

## Risks / Trade-offs

### Risk 1: Redis 版本兼容性
**风险**：某些环境 Redis < 5.0，不支持 Stream

**缓解**：
- 检查 Redis 版本，不支持时降级到 Pub/Sub
- 在启动时验证 Stream 支持
- 文档明确说明版本要求

**代码**：
```python
async def check_redis_stream_support():
    info = await redis.info()
    version = tuple(map(int, info['redis_version'].split('.')[:2]))
    if version < (5, 0):
        logger.warning("Redis Stream not supported, falling back to Pub/Sub")
        return False
    return True
```

---

### Risk 2: 内存占用增加
**风险**：Stream 持久化消息会占用更多内存

**缓解**：
- XTRIM 限制长度（maxlen=1000）
- EXPIRE 自动清理过期 key
- 监控 Redis 内存使用

**估算**：
- 每条消息 ~500 字节
- 1000 条消息 ~500KB
- 可接受的内存开销

---

### Risk 3: 性能下降
**风险**：XREAD 阻塞读取可能比 Pub/Sub 慢

**缓解**：
- Stream 性能与 Pub/Sub 相当（官方基准测试）
- 使用 block=1000 避免频繁轮询
- 监控延迟指标

---

### Risk 4: 前端兼容性
**风险**：前端需要适配新的消息格式

**缓解**：
- 保持消息格式兼容（StreamMessage 结构不变）
- 前端无需修改（消息字段相同）
- 新增 message_id 字段用于续订

---

## Latest Progress (2025-12-11)

- ✅ RedisPublisher `XADD` 现已在 `src/infra/redis_pubsub.py` 实装，并把 `message_id` 写入 Hash 以便前端续订。
- ✅ WebSocket 层 `src/api/routes/stream.py` 同时推送 `is_history` 标记，前端可跳过重复处理。
- ✅ `/chat/threads/{thread_id}/history` 已过滤带 `tool_calls` 的 AI 中间消息，刷新后只看到最终问答。
- ✅ `frontend/src/hooks/useChatStream.ts` 统一使用后端 ID，并在 WebSocket token 处理中移除 query_or_respond 的临时消息。
- 🔄 持续进行：集成测试脚本与性能基准（参考任务清单 #4 #5 #6）。

## Migration Plan

### Phase 1: 准备（1-2 天）
1. 创建 OpenSpec 提案（本文档）
2. 审核设计决策
3. 准备测试环境

### Phase 2: 实现（3-5 天）
1. **修改 RedisPublisher**
   - 添加 `publish_to_stream()` 方法
   - 保留 `publish_message()` 方法（Pub/Sub）
   - 添加功能开关支持

2. **修改 WebSocket 订阅**
   - 添加 Stream 读取逻辑
   - 保留 Pub/Sub 降级方案
   - 支持 last_id 续订参数

3. **添加配置和监控**
   - 添加 REDIS_STREAM_ENABLED 配置
   - 添加 Redis 版本检查
   - 添加性能监控

### Phase 3: 测试（2-3 天）
1. 单元测试：Stream 发布/订阅逻辑
2. 集成测试：完整工作流事件流
3. 性能测试：对比 Pub/Sub 和 Stream
4. 网络中断测试：验证续订能力

### Phase 4: 灰度发布（3-5 天）
1. 生产环境启用 REDIS_STREAM_ENABLED=false（默认）
2. 监控 1-2 天，确保无异常
3. 逐步提升开关比例（10% → 50% → 100%）
4. 监控内存、延迟、错误率

### Phase 5: 清理（1 天）
1. 移除 Pub/Sub 代码（如果完全迁移）
2. 更新文档
3. 存档 OpenSpec 变更

---

## Open Questions & Decisions

### Q1: 消费者组支持（已决策：不实现）
**决策**：当前不实现消费者组（Consumer Groups），标记为 Future Work。

**理由**：
- 当前场景：每个 WebSocket 独立消费自己线程的事件
- 不需要：多个 worker 共享任务队列或负载均衡
- 复杂度：消费者组增加显著的实现复杂度

**Future Work**：
- 当多个后端实例需要共享消息处理时再考虑
- 届时可使用 XREADGROUP 和消费者组管理

---

### Q2: 消息 TTL（已决策：配置化）
**决策**：使用环境变量配置 TTL 和 Stream 长度，默认值如下：
```python
STREAM_TTL_SECONDS = int(os.getenv("STREAM_TTL", "3600"))      # 1 小时
STREAM_MAX_LENGTH = int(os.getenv("STREAM_MAXLEN", "1000"))    # 1000 条消息
```

**理由**：
- 1 小时：与 WORKFLOW_TIMEOUT_SECONDS 对齐
- 1000 条：足以存储 10-20 个并发工作流（每个 50-100 条消息）
- 配置化：便于不同环境调整

---

### Q3: 前端续订实现（已决策：localStorage + URL 参数）
**决策**：使用 localStorage 保存 last_id，重连时通过 URL 参数传递。

**实现方案**：
```typescript
// 前端：保存 last_id
socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  localStorage.setItem(`last_id_${threadId}`, data.message_id);
};

// 重连时：从 localStorage 恢复
const lastId = localStorage.getItem(`last_id_${threadId}`);
const ws = new WebSocket(`/ws/${threadId}?last_id=${lastId}`);
```

**理由**：
- 简单：无需额外的状态管理
- 可靠：页面刷新后仍能恢复
- 灵活：支持跨标签页恢复（通过 localStorage）

**为什么不用其他方案**：
- ❌ 只用 URL 参数：页面刷新会丢失状态
- ❌ 只用 localStorage：页面刷新后需要手动恢复
- ✅ 结合两者：最佳实践

---

## Implementation Checklist

- [ ] 添加 REDIS_STREAM_ENABLED 配置
- [ ] 实现 Stream 版本检查
- [ ] 修改 RedisPublisher 支持 Stream
- [ ] 修改 WebSocket 订阅逻辑
- [ ] 添加单元测试
- [ ] 添加集成测试
- [ ] 性能基准测试
- [ ] 文档更新
- [ ] 灰度发布计划
