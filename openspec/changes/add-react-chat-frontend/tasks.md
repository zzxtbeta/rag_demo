## 1. 前端项目初始化
- [x] 1.1 使用 Vite 创建 `frontend/`（React + TypeScript），配置基础别名与 eslint/prettier。
- [x] 1.2 添加基础布局（深色主题）：左侧 Sidebar（线程列表）+ 中间聊天区域 + 底部输入框。

## 2. 与后端 API 对接
- [x] 2.1 封装 HTTP 客户端，支持配置 `VITE_API_BASE_URL`，实现调用 `/chat/stream`。
- [x] 2.2 实现 WebSocket 客户端，连接 `ws://<API_HOST>/ws/{thread_id}`，处理自动重连与关闭。

## 3. Chat 组件与状态管理
- [x] 3.1 定义前端消息模型（区分 user / assistant / 节点输出），维护 per-thread 消息列表。
- [x] 3.2 实现 `useChatStream` hook：发送问题、接收 WebSocket 消息、按 `node_name/message_type` 更新 UI。
- [x] 3.3 在 `ChatWindow` 中按消息类型渲染（普通对话气泡 + 节点状态/输出条目）。

## 4. 线程列表与会话切换
- [x] 4.1 Sidebar 展示当前已存在的 `thread_id` 列表，支持切换激活线程。
- [x] 4.2 新建对话时生成/选择 `thread_id`，并在 UI 中高亮当前线程。

## 5. UI 优化与消息解析
- [x] 5.1 优化消息显示逻辑：从 Redis 消息中提取 AI 回复，避免重复显示。
- [x] 5.2 节点消息默认折叠显示 JSON，助手消息清晰展示。
- [x] 5.3 添加流式指示器和自动滚动功能。

## 6. 配置与文档
- [x] 6.1 在根 README 中添加前端启动说明与环境变量说明。
- [x] 6.2 确保与现有 FastAPI + LangGraph 流程一致，前端示例中演示从输入到流式展示的完整链路。
- [x] 6.3 更新 OpenSpec 文档，反映 UI 优化和消息解析改进。


