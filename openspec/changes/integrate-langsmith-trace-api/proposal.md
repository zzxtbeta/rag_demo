# Proposal: 集成 LangSmith Trace API 实现历史执行记录重构

**Status**: ✅ Completed  
**Date**: 2025-12-07  
**Author**: AI Assistant  
**Related Issues**: 前端刷新后丢失 Timeline、工具 artifact 显示不完整

---

## Summary

集成 LangSmith Trace API，使用真实的执行历史数据替代前端的"合成 Timeline"方案，实现原汁原味的历史记录展示。

---

## Motivation

### 问题背景

在之前的修复中（`fix-frontend-persistence-split-brain`），我们通过"合成 Timeline"的方式解决了刷新后 Timeline 消失的问题。但这个方案存在以下局限：

1. **硬编码节点名称**：假设所有 AI 消息都来自 `query_or_respond`
2. **猜测时间戳**：使用 `timestamp - 20` 等魔法数字
3. **伪造元数据**：无法显示真实的执行时间、Token 消耗
4. **不完整**：丢失了 LangSmith 中记录的丰富执行细节

### LangSmith 的优势

LangSmith 已经在后台自动记录了所有执行细节：
- ✅ 每个节点的真实开始和结束时间
- ✅ LLM 的 Token 消耗统计
- ✅ 工具调用的完整输入输出
- ✅ 节点之间的父子依赖关系
- ✅ 错误和重试信息

这些信息正是我们需要的，不应该通过"猜测"来重构。

---

## Design

### 方案选择

在研究文档（`docs/HISTORY_RECONSTRUCTION_RESEARCH.md`）中，我们提出了两个方案：

- **方案 A**：增强 LangGraph Checkpoint，在 State 中添加 `execution_history` 字段
- **方案 B**：集成 LangSmith Trace API（本提案）

选择方案 B 的原因：
1. **零侵入**：不需要修改任何节点代码
2. **准确性**：使用 LangSmith 自动记录的真实数据
3. **完整性**：包含所有 LangChain 组件的执行细节
4. **维护成本低**：自动记录，无需手动维护

### 架构设计

```
┌─────────────┐
│   Frontend  │
│   (React)   │
└──────┬──────┘
       │ GET /chat/threads/{thread_id}/history-with-trace
       ▼
┌─────────────────────────────────────────┐
│          FastAPI Backend                │
│  ┌────────────────────────────────────┐ │
│  │ /history-with-trace 接口            │ │
│  └────┬──────────────────────────┬────┘ │
│       │                          │       │
│       ▼                          ▼       │
│  ┌─────────────┐          ┌──────────┐  │
│  │ LangGraph   │          │LangSmith │  │
│  │ Checkpoint  │          │   API    │  │
│  │ (Messages)  │          │ (Traces) │  │
│  └─────────────┘          └──────────┘  │
└─────────────────────────────────────────┘
       │                          │
       ▼                          ▼
┌──────────────┐          ┌──────────────┐
│  PostgreSQL  │          │  LangSmith   │
│  (Checkpts)  │          │   Service    │
└──────────────┘          └──────────────┘
```

### 数据流

1. **前端请求**：`GET /chat/threads/{thread_id}/history-with-trace`
2. **后端处理**：
   - 从 LangGraph Checkpoint 获取 `messages`
   - 从 LangSmith API 查询该 `thread_id` 的所有 Runs
3. **数据合并**：
   - `messages`: 用户和助手的对话消息
   - `trace_runs`: 完整的节点执行历史
4. **前端重构**：
   - 遍历 `trace_runs`，为每个 Run 创建 Node Start/Output 事件
   - 使用真实的时间戳、节点名称、元数据
   - 按时间排序，展示完整 Timeline

---

## Implementation

### 1. 后端改动

#### 1.1 依赖安装
```toml
# pyproject.toml
dependencies = [
    # ... existing dependencies
    "langsmith>=0.2.0,<0.3.0",
]
```

#### 1.2 配置管理
```python
# src/config/settings.py
@dataclass(frozen=True)
class Settings:
    # ... existing fields
    langsmith_api_key: Optional[str]
    langsmith_endpoint: str
    langsmith_project: str
```

#### 1.3 LangSmith 客户端
```python
# src/utils/langsmith_client.py
def get_langsmith_client() -> Optional[Client]:
    settings = get_settings()
    if not settings.langsmith_api_key:
        return None
    return Client(
        api_key=settings.langsmith_api_key,
        api_url=settings.langsmith_endpoint,
    )
```

#### 1.4 API Schema
```python
# src/api/schemas.py
class TraceRun(BaseModel):
    run_id: str
    name: str
    run_type: str
    start_time: str
    end_time: Optional[str] = None
    latency_ms: Optional[float] = None
    total_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    error: Optional[str] = None
    inputs: Optional[dict] = None
    outputs: Optional[dict] = None
    parent_run_id: Optional[str] = None

class ThreadHistoryWithTrace(BaseModel):
    thread_id: str
    messages: list[HistoryMessage]
    total_messages: int
    trace_runs: list[TraceRun] = []
```

#### 1.5 新增历史接口
```python
# src/api/routes/chat.py
@router.get("/threads/{thread_id}/history-with-trace", response_model=ThreadHistoryWithTrace)
async def get_thread_history_with_trace(thread_id: str, graph=Depends(get_graph)):
    # 1. 获取消息历史
    state = await graph.aget_state(config)
    messages = state.values.get("messages", [])
    
    # 2. 查询 LangSmith Runs
    langsmith_client = get_langsmith_client()
    if langsmith_client:
        filter_string = (
            f'and(in(metadata_key, ["session_id","conversation_id","thread_id"]), '
            f'eq(metadata_value, "{thread_id}"))'
        )
        runs = langsmith_client.list_runs(
            project_name=settings.langsmith_project,
            filter=filter_string,
        )
        # 转换并排序
        trace_runs = [convert_to_trace_run(r) for r in sorted(runs, key=lambda r: r.start_time)]
    
    return ThreadHistoryWithTrace(...)
```

### 2. 前端改动

#### 2.1 历史加载逻辑
```typescript
// frontend/src/hooks/useChatStream.ts
const loadThreadHistory = useCallback(async (threadId: string) => {
  const response = await fetch(
    `${API_BASE}/chat/threads/${encodeURIComponent(threadId)}/history-with-trace`
  );
  const data = await response.json();
  
  // 使用真实的 Trace Runs 重构 Timeline
  const reconstructedMessages: ChatMessage[] = [];
  
  data.trace_runs.forEach((run: any) => {
    const startTime = new Date(run.start_time).getTime();
    const endTime = run.end_time ? new Date(run.end_time).getTime() : null;
    
    // Node Start Event（真实数据）
    reconstructedMessages.push({
      id: `${run.run_id}_start`,
      nodeName: run.name,  // ✅ 真实节点名称
      timestamp: startTime,  // ✅ 真实时间戳
      content: JSON.stringify({ 
        run_type: run.run_type,
        run_id: run.run_id,
      }),
    });
    
    // Node Output Event（如果有结束时间）
    if (endTime) {
      reconstructedMessages.push({
        id: `${run.run_id}_output`,
        nodeName: run.name,
        timestamp: endTime,
        content: JSON.stringify({
          execution_time_ms: run.latency_ms,  // ✅ 真实执行时间
          token_usage: {  // ✅ 真实 Token 消耗
            total_tokens: run.total_tokens,
            prompt_tokens: run.prompt_tokens,
            completion_tokens: run.completion_tokens,
          },
          error: run.error,  // ✅ 真实错误信息
        }),
      });
    }
  });
  
  // 按时间排序
  reconstructedMessages.sort((a, b) => a.timestamp - b.timestamp);
  setMessages(reconstructedMessages);
}, []);
```

---

## Testing

### 配置验证
```bash
$ python test_langsmith_config.py
=== LangSmith 配置 ===
API Key: lsv2_pt_3ecd89efbf2a...
Endpoint: https://api.smith.langchain.com
Project: gravaity
✅ LangSmith 客户端创建成功
```

### 环境变量
```env
LANGSMITH_PROJECT=gravaity
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your-api-key
```

### 端到端测试
1. 启动后端：`python scripts/start_backend.py`
2. 启动前端：`cd frontend && npm run dev`
3. 发送消息触发工作流
4. 刷新页面
5. 验证 Timeline 正确显示（节点名称、执行时间、Token 消耗）

---

## Impact

### 优势
1. ✅ **零侵入**：不需要修改节点代码
2. ✅ **准确性**：使用真实的执行时间和元数据
3. ✅ **完整性**：包含所有 LangChain 组件的执行
4. ✅ **可维护性**：自动记录，无需手动维护

### 劣势
1. ⚠️ **依赖外部服务**：需要 LangSmith 账号
2. ⚠️ **网络延迟**：需要额外的 HTTP 请求
3. ⚠️ **数据同步延迟**：LangSmith Trace 可能有轻微延迟

### 缓解措施
- 添加缓存机制（Redis）
- 添加 Loading 状态
- 如果 LangSmith 不可用，优雅降级为基本消息显示

---

## Alternatives Considered

### 方案 A：增强 LangGraph Checkpoint
- **优势**：无外部依赖，性能好
- **劣势**：需要修改所有节点，维护成本高
- **结论**：适合短期快速修复，不适合长期维护

### 方案 C：自建 Trace 系统
- **优势**：完全可控，无外部依赖
- **劣势**：开发成本极高，重复造轮子
- **结论**：不推荐，LangSmith 已经是成熟方案

---

## Migration Plan

### Phase 1: 实施（已完成）
- ✅ 后端集成 LangSmith API
- ✅ 前端使用新接口
- ✅ 配置验证

### Phase 2: 优化（可选）
- [ ] 添加缓存机制
- [ ] 添加"在 LangSmith 中查看"链接
- [ ] 优化错误处理和重试

### Phase 3: 监控（生产环境）
- [ ] 监控 LangSmith API 调用延迟
- [ ] 监控缓存命中率
- [ ] 收集用户反馈

---

## References

- [LangSmith 官方文档](https://docs.langchain.com/langsmith)
- [Trace Query Syntax](https://docs.langchain.com/langsmith/trace-query-syntax)
- [Run Data Format](https://docs.langchain.com/langsmith/run-data-format)
- 相关提案：`openspec/changes/fix-frontend-persistence-split-brain/`
- 研究文档：`docs/HISTORY_RECONSTRUCTION_RESEARCH.md`

---

## Conclusion

方案 B（集成 LangSmith Trace API）是最优的长期解决方案，提供了生产级别的历史记录重构能力。通过使用 LangSmith 自动记录的真实执行数据，我们彻底消除了"猜测"和"硬编码"，实现了原汁原味的 Timeline 展示。
