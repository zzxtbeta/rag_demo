# 消息持久化修复完整方案

## 问题诊断

### 原始问题
1. **消息 ID 不同步**：前端自己生成 ID（时间戳格式），后端返回 UUID ID
2. **中间消息混乱**：历史加载时包含了中间节点的输出（query_or_respond、tools）
3. **消息丢失**：刷新后某些消息无法恢复
4. **顺序错乱**：历史消息和新消息混淆导致显示顺序错误

### 根本原因
- 后端 `/history` 接口返回了所有消息，包括中间过程
- 前端自己生成 ID，与后端返回的 ID 不一致
- localStorage 保存的 ID 格式混乱

---

## 解决方案

### 1. 后端修复

#### 修改：`src/api/routes/chat.py` - `/history` 接口

**关键改动**：过滤掉中间消息，只返回最终消息

```python
# 过滤规则：
# 1. 跳过 tool 消息（中间过程）
# 2. 跳过有 tool_calls 的 AI 消息（query_or_respond 节点的输出）
# 3. 保留所有 user 消息
# 4. 保留没有 tool_calls 的 AI 消息（最终回复）

if msg_type == "tool":
    continue

if msg_type == "ai":
    tool_calls = getattr(msg, "tool_calls", [])
    if tool_calls:
        continue
```

**效果**：
- ✅ 历史加载只返回最终消息
- ✅ 避免重复显示中间过程
- ✅ 刷新后显示清晰的对话历史

#### 修改：`src/infra/redis_pubsub.py` - Redis Stream 发布

**关键改动**：保存 message_id 映射

```python
# 发布到 Stream 后，保存 message_id 映射
await self._client.hset(
    f"stream_message_ids:{message.thread_id}",
    message_id,
    message_id
)
```

**效果**：
- ✅ 前端和后端使用相同的 ID 系统
- ✅ WebSocket 推送的 message_id 与历史查询的 ID 一致

---

### 2. 前端修复

#### 修改：`frontend/src/hooks/useChatStream.ts` - 历史加载

**关键改动**：
1. 直接使用后端返回的 ID
2. 简化历史消息重构逻辑
3. 不再需要检查 tool_calls

```typescript
// 后端已过滤，只返回最终消息
data.messages.forEach((msg: any) => {
  const baseId = msg.id || `${threadId}_history_${index}`;
  
  if (msg.role === 'user') {
    // 保存用户消息
  } else if (msg.role === 'assistant') {
    // 保存最终 assistant 消息（后端已确保没有 tool_calls）
  }
});
```

**效果**：
- ✅ 历史加载使用后端 ID
- ✅ localStorage 保存的 ID 与后端一致
- ✅ 刷新后消息恢复正确

#### 修改：`frontend/src/hooks/useChatStream.ts` - WebSocket 处理

**关键改动**：使用后端返回的 ID

```typescript
// 创建新的 assistant 消息时
{
  id: data.id || data.message_id || fallback_id,
  // ...
}
```

**效果**：
- ✅ 实时消息使用后端 ID
- ✅ 前后端 ID 系统统一

#### 修改：`frontend/src/hooks/useChatStream.ts` - localStorage 自动保存

**关键改动**：重新启用 useEffect，只保存最终消息

```typescript
useEffect(() => {
  if (activeThreadId && messages.length > 0) {
    // 过滤出用户和助手消息（排除节点消息）
    const chatMessages = messages.filter(
      (msg) => msg.role === "user" || msg.role === "assistant"
    );
    if (chatMessages.length > 0) {
      saveMessagesToStorage(activeThreadId, chatMessages);
    }
  }
}, [messages, activeThreadId]);
```

**效果**：
- ✅ 每条新消息都自动保存
- ✅ 刷新时完整恢复
- ✅ 只保存最终消息，不保存节点消息

---

## 数据流

### 实时对话流程

```
用户发送消息
    ↓
WebSocket 连接
    ↓
后端推送所有事件：
  - query_or_respond 节点开始
  - query_or_respond 节点完成（含思考过程）← 实时显示
  - tools 节点执行 ← 实时显示
  - generate 节点开始
  - generate 节点流式输出 ← 实时累积显示
  - generate 节点完成
    ↓
前端处理：
  1. 接收 WebSocket 消息
  2. 使用后端返回的 message_id 创建消息
  3. 累积 token 到消息
  4. 自动保存到 localStorage
    ↓
消息状态：
  - messages 数组：包含所有消息（user + assistant）
  - localStorage：保存最终消息
```

### 刷新后恢复流程

```
页面刷新
    ↓
前端初始化
    ↓
1. 从 localStorage 加载消息（快速恢复）
    ↓
2. GET /chat/threads/{thread_id}/history
    ↓
后端返回过滤后的消息：
  - User: "简单介绍..."
  - Assistant: "根据提供的..." ← 只有最终消息
    ↓
前端合并：
  - 使用后端消息覆盖 localStorage（确保一致性）
  - 使用后端返回的 ID
    ↓
显示：清晰的对话历史，无重复无混乱
```

---

## 验证清单

### 1. 单轮对话测试

```
步骤：
1. 新建对话
2. 发送：" 简单介绍一下象量科技的技术架构"
3. 等待完成

验证：
✅ 实时显示中间过程（可选）
✅ 最终显示完整回复
✅ localStorage 保存了消息
✅ 消息 ID 格式一致（UUID）
```

### 2. 多轮对话测试

```
步骤：
1. 继续发送多条消息
2. 观察消息列表

验证：
✅ 每条消息都有唯一 ID
✅ 消息顺序正确
✅ 没有重复消息
✅ localStorage 包含所有消息
```

### 3. 刷新恢复测试

```
步骤：
1. 完成多轮对话
2. 按 F5 刷新页面
3. 观察消息恢复

验证：
✅ 所有消息都恢复
✅ 消息顺序正确
✅ 没有重复消息
✅ 没有中间过程消息
✅ 消息 ID 与刷新前一致
```

### 4. API 响应验证

```bash
# 查询历史消息
curl http://localhost:8000/chat/threads/{thread_id}/history

# 验证响应
✅ 只包含 user 和 assistant 消息
✅ assistant 消息没有 tool_calls
✅ 没有 tool 消息
✅ 消息 ID 是 UUID 格式
```

### 5. localStorage 验证

```javascript
// 在浏览器控制台执行
const key = 'chat_messages_thread_zzxt_1765422633549';
const messages = JSON.parse(localStorage.getItem(key));
console.log(messages);

// 验证
✅ 只包含 user 和 assistant 消息
✅ 消息 ID 是 UUID 格式
✅ 消息数量与 API 返回一致
```

---

## 修复总结

| 问题 | 原因 | 解决方案 | 状态 |
|------|------|---------|------|
| 消息 ID 不同步 | 前端自己生成 ID | 使用后端返回的 ID | ✅ |
| 中间消息混乱 | 历史加载包含中间过程 | 后端过滤中间消息 | ✅ |
| 消息丢失 | localStorage 保存不完整 | 重新启用自动保存 | ✅ |
| 顺序错乱 | 历史和实时消息混淆 | 后端区分，前端统一处理 | ✅ |
| 重复显示 | 中间消息被当作最终消息 | 后端过滤 tool_calls | ✅ |

---

## 后续优化（可选）

### 1. 节点执行过程持久化

如果需要在刷新后也显示节点执行过程，可以：
- 在后端添加 `/history-with-nodes` 接口
- 返回节点事件列表
- 前端在实时显示时使用节点信息

### 2. 消息搜索和过滤

- 添加消息搜索功能
- 支持按时间、内容过滤
- 使用后端 ID 作为唯一标识

### 3. 消息编辑和删除

- 支持编辑已发送的消息
- 支持删除消息
- 使用后端 ID 进行操作

---

## 技术细节

### 消息 ID 格式

**后端生成的 ID**：
- LangGraph 内部 ID：`lc_run--xxx` 或 UUID 格式
- Redis Stream ID：`1765422640213-0` 格式
- 后端返回给前端：UUID 格式（如 `402ff032-a1af-4f18-8876-dd2f6e1a9e2d`）

**前端使用的 ID**：
- 直接使用后端返回的 ID
- 兜底：时间戳 + 随机数格式

### 消息过滤逻辑

**后端过滤**：
```python
# 保留：user 消息 + 没有 tool_calls 的 assistant 消息
# 跳过：tool 消息 + 有 tool_calls 的 assistant 消息
```

**前端保存**：
```typescript
// 保留：user 消息 + assistant 消息
// 跳过：节点消息（如果有 nodeName 属性）
```

### localStorage 结构

```json
{
  "chat_messages_thread_zzxt_1765422633549": [
    {
      "id": "402ff032-a1af-4f18-8876-dd2f6e1a9e2d",
      "threadId": "thread_zzxt_1765422633549",
      "role": "user",
      "content": "简单介绍一下象量科技的技术架构",
      "timestamp": 1765423085491
    },
    {
      "id": "lc_run--4e9925c7-3a1a-4866-8666-8f02a5237f03",
      "threadId": "thread_zzxt_1765422633549",
      "role": "assistant",
      "content": "根据提供的《象量科技项目介绍20250825》文档...",
      "timestamp": 1765423088491
    }
  ]
}
```

---

## 常见问题

### Q: 为什么要过滤中间消息？
A: 中间消息（如 query_or_respond 的思考过程）是工作流的内部状态，不是用户可见的最终结果。刷新后显示这些消息会造成混乱。

### Q: 为什么要统一 ID 格式？
A: 统一 ID 格式可以确保前后端使用相同的消息标识，避免刷新后消息不匹配。

### Q: localStorage 为什么要自动保存？
A: 自动保存可以确保每条新消息都被持久化，刷新时可以快速恢复，同时减少对后端的查询。

### Q: 如何处理离线场景？
A: localStorage 中的消息可以在离线时显示，当网络恢复后，前端会自动同步后端的最新消息。

---

## 部署检查清单

- [ ] 后端代码已修改：`src/api/routes/chat.py`
- [ ] 后端代码已修改：`src/infra/redis_pubsub.py`
- [ ] 前端代码已修改：`frontend/src/hooks/useChatStream.ts`
- [ ] 后端已重启
- [ ] 前端已热更新或重新加载
- [ ] 已执行验证清单中的所有测试
- [ ] 没有控制台错误
- [ ] localStorage 数据正确
- [ ] API 响应正确

