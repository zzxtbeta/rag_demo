# Change: Add React-based chat frontend with streaming UI

## Status: ✅ Completed

## Why

### 用户视角
- 目前只有后端 API（`/chat`、`/chat/stream` + WebSocket `/ws/{thread_id}`），缺少一个直观的可视化聊天界面，无法体验节点级流式反馈。
- 在复杂工作流（如 margin check 报告）场景中，用户希望：
  - 左侧看到历史会话（threads）列表，便于在不同会话间快速切换。
  - 中间区域以对话形式展示每轮用户提问和 Agent 回答。
  - 在 Agent 回答过程中，实时看到各节点状态/输出的“进度反馈”，而不是等待整条回复完成。

### 设计目标
- 提供一个简单但**接近截图风格**的 React 聊天前端，用于 PoC 和内部使用：
  - 深色主题、左侧线程列表、中间聊天区域、底部输入框。
  - 支持基于 `thread_id` 的会话切换，与 LangGraph/checkpointer 设计对齐。
  - 能通过 WebSocket 订阅 Redis 流式消息，实现“节点完成即刻展示”体验。

## What Changes

1. **前端技术栈与项目结构**
   - 使用 `React + TypeScript + Vite`（或 Next.js CSR 模式）创建 `frontend/` 子项目。
   - UI 库：尽量轻量（如 Tailwind 或基础 CSS），不引入重量级设计系统，保留自定义空间。
   - 基本结构：
     - `components/SidebarThreads`：左侧线程列表（模拟数据或从后端获取）。
     - `components/ChatWindow`：中间聊天区（消息气泡、滚动区域）。
     - `components/MessageInput`：底部输入框，支持回车发送。
     - `hooks/useChatStream`：封装与 `/chat/stream` + `/ws/{thread_id}` 的交互。

2. **与后端的协议对齐**
   - HTTP：
     - 调用 `/chat/stream`，传入 `thread_id`（可复用或新建）、`user_id`、`message`。
     - 响应体中使用现有 `ChatResponse`（至少包含 `thread_id` 和占位 `answer`）。
   - WebSocket：
     - 连接 `ws://<host>:8000/ws/{thread_id}`。
     - 服务端推送来自 Redis 的 JSON 消息，形如：
       ```json
       {
         "thread_id": "thread_user_123_session_1",
         "node_name": "fetch_position",
         "message_type": "output",
         "status": "completed",
         "timestamp": 1705740000.123,
         "execution_time_ms": 1234,
         "data": { ... }
       }
       ```
     - 前端根据 `node_name` 和 `message_type` 更新对应 UI 模块（如在聊天区域显示“[节点] 已完成”以及部分内容）。

3. **线程管理与 UI 行为**
   - 线程标识：
     - 优先使用后端已有的 `thread_id` 语义：`thread_{user_id}_...`。
     - 左侧 Sidebar 展示当前已打开的 threads（先可用内存状态维护）。
   - 行为：
     - 用户在当前线程中发送消息 → 前端调用 `/chat/stream` 开始一次工作流执行。
     - WebSocket 持续推送节点输出 → ChatWindow 实时追加“流式消息”。
     - 可在界面中简单标识节点名，例如“[fetch_position] 查询完成”。
   - **消息解析与显示优化**：
     - 从 Redis 消息的 `data.messages` 数组中提取 `type: "ai"` 的消息，显示为助手回复。
     - 节点输出（`role: "node"`）默认折叠显示，点击可展开查看详细 JSON（用于调试）。
     - 隐藏空的 `workflow:complete` 消息，避免界面冗余。
     - 自动滚动到最新消息，提升用户体验。

4. **界面风格要求**
   - 尽量贴近用户提供的截图：
     - 深色背景、左侧窄栏、右侧为主对话区域。
     - 顶部标题（如 “Chat LangGraph” 或项目名），底部有输入框与发送按钮。
   - 不追求 pixel-perfect，但整体布局、色调、交互和截图风格一致。
   - **UI 优化细节**：
     - 用户消息：右对齐，深色背景，突出显示。
     - 助手消息：左对齐，浅色背景，清晰易读。
     - 节点消息：虚线边框，紫色主题，可折叠显示 JSON 详情。
     - 流式指示器：底部显示 "Streaming..." 动画，提示用户系统正在处理。
     - 消息自动滚动：新消息到达时自动滚动到底部。

5. **工程与构建**
   - 在仓库根目录添加简要 README 片段，说明如何在 `frontend/` 下安装依赖与启动：
     ```bash
     cd frontend
     npm install
     npm run dev
     ```
   - 与后端通过环境变量或 `.env` 文件配置 API 基础 URL（例如 `VITE_API_BASE_URL`）。

## Impact

- ✅ 新增 `frontend/` React 项目，对后端代码无破坏性改动。
- ✅ 已在 README 中添加前端运行说明和简单的"接入指南"（如何与 `/chat/stream` + `/ws/{thread_id}` 对接）。
- ✅ 为后续更复杂的工作流可视化（节点图、进度条、错误高亮）打下基础。

## Implementation Details

### Streaming Mode
- ✅ 使用混合流式模式：`stream_mode=["messages", "updates"]`
- ✅ 支持 token 级流式输出（`message_type="token"`）和节点级更新（`message_type="output"`）
- ✅ 前端区分处理 token 消息（实时追加）和节点完成消息（更新节点状态）

### UI Components
- ✅ `TurnView`：对话轮次视图（用户消息 + 节点时间轴 + AI 回复）
- ✅ `NodeTimeline`：纵向时间轴展示节点执行过程
- ✅ `NodeStep`：单个节点步骤（可展开/折叠查看 JSON）
- ✅ `Sidebar`：线程列表、搜索、分组（TODAY/OLDER）、用户信息
- ✅ `SettingsMenu`：主题切换菜单
- ✅ `MessageInput`：优化的输入框（无 Send 按钮，Enter 发送）

### Backend Integration
- ✅ `/chat/stream`：启动工作流并返回 `thread_id`
- ✅ `/ws/{thread_id}`：WebSocket 实时接收流式消息
- ✅ `/chat/threads/{thread_id}/history`：获取历史消息
- ✅ 错误处理：区分 `CancelledError`、`TimeoutError` 和一般异常


