# Redis Stream 完整流程图

## 1. 实时对话流程（WebSocket + Redis Stream）

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as 前端<br/>(React)
    participant Backend as 后端<br/>(FastAPI)
    participant LangGraph as LangGraph<br/>工作流
    participant Redis as Redis Stream

    User->>Frontend: 输入消息，按Enter
    Frontend->>Backend: POST /chat/stream<br/>(thread_id, message)
    Backend->>LangGraph: 启动工作流执行
    Backend->>Frontend: 返回 thread_id
    
    Frontend->>Backend: WebSocket连接<br/>ws://{thread_id}?last_id=...
    Backend->>Redis: XRANGE 读取历史消息
    Redis-->>Backend: 返回历史消息列表
    Backend->>Frontend: 推送历史消息<br/>(is_history=true)
    
    Frontend->>Frontend: 加载历史消息到状态<br/>（忽略 is_history=true）
    
    par 工作流执行与消息推送
        LangGraph->>LangGraph: query_or_respond 节点
        LangGraph->>Redis: XADD 发布节点输出
        Redis-->>Backend: message_id_1
        Backend->>Frontend: 推送节点消息<br/>(node_name, is_history=false)
        Frontend->>Frontend: 显示节点执行状态
        
        LangGraph->>LangGraph: tools 节点
        LangGraph->>Redis: XADD 发布工具调用
        Redis-->>Backend: message_id_2
        Backend->>Frontend: 推送工具消息
        Frontend->>Frontend: 更新UI
        
        LangGraph->>LangGraph: generate 节点<br/>流式生成Token
        LangGraph->>Redis: XADD 发布每个Token
        Redis-->>Backend: message_id_3, message_id_4, ...
        Backend->>Frontend: 推送Token流<br/>(message_type=token)
        Frontend->>Frontend: 实时追加Token到消息
        Frontend->>Frontend: 保存 last_id 到 localStorage
    end
    
    LangGraph->>Redis: XADD 发布完成事件
    Backend->>Frontend: 推送完成信号
    Frontend->>Frontend: 标记消息完成
    Frontend->>Frontend: 保存消息到 localStorage
```

## 2. 页面刷新恢复流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as 前端<br/>(React)
    participant LocalStorage as LocalStorage
    participant Backend as 后端<br/>(FastAPI)
    participant Redis as Redis Stream

    User->>Frontend: F5 刷新页面
    Frontend->>LocalStorage: 读取 activeThreadId
    Frontend->>LocalStorage: 读取 chat_messages_*
    Frontend->>Frontend: 快速恢复消息到UI<br/>（毫秒级）
    
    Frontend->>Backend: GET /chat/threads/{thread_id}/history
    Backend->>Backend: 从 LangGraph Checkpoint<br/>读取所有消息
    Backend->>Backend: 过滤规则：<br/>- 跳过 tool 消息<br/>- 跳过有 tool_calls 的 AI 消息<br/>- 只保留最终消息
    Backend-->>Frontend: 返回过滤后的消息<br/>(user + assistant only)
    
    Frontend->>Frontend: 合并历史消息<br/>（后端数据覆盖 localStorage）
    Frontend->>Frontend: 显示清晰的对话历史<br/>（无中间过程）
    
    Frontend->>LocalStorage: 读取 stream_last_id_*
    Frontend->>Backend: WebSocket连接<br/>ws://{thread_id}?last_id=...
    Backend->>Redis: XREAD 从 last_id 开始<br/>读取新消息
    Redis-->>Backend: 返回新消息（如有）
    Backend->>Frontend: 推送新消息
    Frontend->>Frontend: 追加新消息到UI
```

## 3. Redis Stream 数据结构

```mermaid
graph TB
    subgraph "Redis Stream Key"
        Key["workflow:execution:thread_zzxt_1765423969845"]
    end
    
    subgraph "Stream Messages"
        M1["ID: 1765424008849-0<br/>node_name: query_or_respond<br/>message_type: output<br/>status: completed<br/>timestamp: 1765424008<br/>data: {...}"]
        M2["ID: 1765424009849-0<br/>node_name: tools<br/>message_type: output<br/>status: completed<br/>timestamp: 1765424009<br/>data: {...}"]
        M3["ID: 1765424010849-0<br/>node_name: generate<br/>message_type: token<br/>status: streaming<br/>timestamp: 1765424010<br/>data: {token: '根'}"]
        M4["ID: 1765424010849-1<br/>node_name: generate<br/>message_type: token<br/>status: streaming<br/>timestamp: 1765424010<br/>data: {token: '据'}"]
        M5["ID: 1765424011849-0<br/>node_name: generate<br/>message_type: output<br/>status: completed<br/>timestamp: 1765424011<br/>data: {...}"]
    end
    
    subgraph "Hash: stream_message_ids:thread_zzxt_1765423969845"
        H["1765424008849-0 → 1765424008849-0<br/>1765424009849-0 → 1765424009849-0<br/>1765424010849-0 → 1765424010849-0<br/>..."]
    end
    
    Key --> M1
    M1 --> M2
    M2 --> M3
    M3 --> M4
    M4 --> M5
    M5 -.->|保存 message_id| H
```

## 4. 前端状态管理流程

```mermaid
graph TD
    A["初始化"] --> B["从 localStorage 加载<br/>activeThreadId<br/>messages<br/>last_id"]
    
    B --> C["快速显示<br/>历史消息"]
    
    C --> D["GET /history<br/>获取后端消息"]
    
    D --> E["过滤后的消息<br/>user + assistant only"]
    
    E --> F["合并到状态<br/>setMessages"]
    
    F --> G["保存到 localStorage<br/>saveMessagesToStorage"]
    
    G --> H["WebSocket 连接<br/>with last_id"]
    
    H --> I["接收实时消息"]
    
    I --> J{消息类型?}
    
    J -->|token| K["追加到最后一条<br/>assistant 消息"]
    J -->|node_output| L["显示节点执行状态"]
    J -->|is_history=true| M["忽略<br/>已从 /history 加载"]
    
    K --> N["保存 last_id<br/>到 localStorage"]
    L --> N
    
    N --> O["自动保存消息<br/>到 localStorage"]
    
    O --> P["用户看到<br/>实时流式回复"]
```

## 5. 消息过滤逻辑（后端 /history）

```mermaid
graph TD
    A["从 LangGraph Checkpoint<br/>读取所有消息"] --> B["遍历消息"]
    
    B --> C{消息类型?}
    
    C -->|tool| D["❌ 跳过<br/>中间过程"]
    C -->|ai| E{有 tool_calls?}
    C -->|human| F["✅ 保留<br/>用户消息"]
    
    E -->|有| G["❌ 跳过<br/>query_or_respond 输出"]
    E -->|无| H{content 为空<br/>且无 artifact?}
    
    H -->|是| I["❌ 跳过<br/>中间消息"]
    H -->|否| J["✅ 保留<br/>最终 assistant 消息"]
    
    F --> K["返回过滤后的消息<br/>给前端"]
    J --> K
    
    D --> L["不返回"]
    G --> L
    I --> L
```

## 6. WebSocket 消息流向

```mermaid
graph LR
    subgraph "后端"
        A["LangGraph<br/>工作流执行"]
        B["RedisPublisher<br/>发布消息"]
        C["WebSocket<br/>推送消息"]
    end
    
    subgraph "Redis"
        D["Stream<br/>workflow:execution:*"]
        E["Hash<br/>stream_message_ids:*"]
    end
    
    subgraph "前端"
        F["WebSocket<br/>接收消息"]
        G["消息处理<br/>setMessages"]
        H["localStorage<br/>保存"]
        I["UI 渲染<br/>ChatWindow"]
    end
    
    A -->|发布事件| B
    B -->|XADD| D
    B -->|HSET| E
    D -->|推送到 WS| C
    C -->|JSON| F
    F -->|filter/map| G
    G -->|save| H
    G -->|update| I
    
    style D fill:#ff9999
    style E fill:#ff9999
    style F fill:#99ccff
    style G fill:#99ccff
    style H fill:#99ccff
    style I fill:#99ccff
```

## 7. 完整时序：从发送消息到显示回复

```
时间线：
├─ T0: 用户输入 "简单介绍象量科技的创始人"
│
├─ T1: 前端 POST /chat/stream
│       └─ 后端启动 LangGraph 工作流
│
├─ T2: 前端 WebSocket 连接
│       └─ 后端推送历史消息 (is_history=true)
│       └─ 前端加载历史（忽略 is_history）
│
├─ T3-T5: 工作流执行
│       ├─ query_or_respond 节点 (100ms)
│       │   └─ XADD → Redis Stream
│       │   └─ WebSocket 推送
│       │   └─ 前端显示"正在思考..."
│       │
│       ├─ tools 节点 (500ms)
│       │   └─ XADD → Redis Stream
│       │   └─ WebSocket 推送
│       │   └─ 前端显示"正在检索..."
│       │
│       └─ generate 节点 (2000ms)
│           ├─ Token 1: XADD → Redis
│           │   └─ WebSocket 推送
│           │   └─ 前端追加 "根"
│           │
│           ├─ Token 2: XADD → Redis
│           │   └─ WebSocket 推送
│           │   └─ 前端追加 "据"
│           │
│           └─ ... (更多 Token)
│               └─ 最终显示完整回复
│
├─ T6: 工作流完成
│       └─ 前端保存 last_id 到 localStorage
│       └─ 前端保存消息到 localStorage
│
└─ T7: 用户刷新页面
        ├─ 前端从 localStorage 快速恢复消息 (0ms)
        ├─ 前端 GET /history 获取最终消息 (100ms)
        │   └─ 后端返回过滤后的消息（只有用户提问 + 最终回复）
        ├─ 前端 WebSocket 连接 with last_id
        │   └─ 后端 XREAD 从 last_id 开始
        │   └─ 返回新消息（如有）
        └─ 用户看到完整的对话历史
```

## 关键特性

### ✅ 消息持久化
- Redis Stream 自动持久化所有消息
- XTRIM 限制长度（1000 条）
- EXPIRE 自动清理过期 key（1 小时）

### ✅ 消息续订
- 前端保存 `last_id` 到 localStorage
- 重连时通过 `?last_id=...` 参数传递
- 后端 XREAD 从指定位置开始读取

### ✅ 历史恢复
- 刷新后从 localStorage 快速恢复（毫秒级）
- 从后端 /history 获取最终消息
- 后端过滤中间消息，只返回最终问答

### ✅ 实时流式
- Token 级流式输出（message_type=token）
- 节点级完成事件（message_type=output）
- 前端实时追加 Token，用户看到逐字显示

### ✅ 无缝切换
- WebSocket 推送 `is_history` 标记
- 前端区分历史消息和新消息
- 避免重复处理和顺序混乱
