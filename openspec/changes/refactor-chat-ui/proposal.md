# Change: Refactor Chat UI with Timeline-style Node Execution Display

## Status: ✅ Completed

## Why

### 用户视角
- ✅ 已修复：当前 UI 存在重复显示 assistant 消息的问题（token 流和 output 消息都创建了 assistant 消息）
- ✅ 已实现：节点执行过程显示过于简单，缺乏层次感和时间轴式的视觉体验
- ✅ 已实现：界面不够美观，缺少用户信息、时间戳等基础元素
- ✅ 已实现：参考 Chat LangChain 的设计，提供更专业的聊天体验

### 设计目标
- ✅ 修复重复消息问题：token 流式消息和节点 output 消息应该统一处理，避免重复创建 assistant 消息
- ✅ 实现时间轴式节点执行展示：每次提问显示一个执行过程（可展开/折叠）和一个最终回复
- ✅ 美化界面：参考 Chat LangChain 的设计，添加用户信息、时间戳、更好的视觉层次
- ✅ 保持代码清晰、易扩展

## What Changes

1. **消息结构重构**
   - 将消息组织为"对话轮次"（Turn）结构：
     - 每轮包含：用户消息、节点执行过程（时间轴）、最终 AI 回复
   - 节点执行过程：
     - 纵向时间轴布局，显示每个节点的执行状态
     - 支持展开/折叠查看详细信息
     - 显示节点名称、状态（start/running/completed）、执行时间
   - 修复重复消息：
     - token 流式消息只更新已存在的 assistant 消息，不创建新消息
     - output 消息不再提取 AI 消息，因为 token 流已经处理了

2. **UI 组件重构**
   - `components/TurnView.tsx`：对话轮次视图，包含用户消息、节点时间轴、AI 回复
   - `components/NodeTimeline.tsx`：节点执行时间轴组件
   - `components/NodeStep.tsx`：单个节点步骤组件（可展开/折叠）
   - `components/UserAvatar.tsx`：用户头像组件
   - `components/AssistantAvatar.tsx`：助手头像组件
   - 更新 `ChatWindow.tsx`：使用新的 TurnView 组件
   - 更新 `Sidebar.tsx`：参考 Chat LangChain 设计，添加搜索、导航链接

3. **样式优化**
   - 参考 Chat LangChain 的深色主题设计
   - 添加用户/助手头像
   - 优化消息气泡样式
   - 时间轴样式：连接线、节点图标、状态指示器
   - 响应式布局优化

4. **状态管理优化**
   - 重构 `useChatStream.ts`：
     - 修复重复 assistant 消息问题
     - 组织消息为 Turn 结构
     - 跟踪当前轮次的节点执行过程

## Impact

- 代码范围：`frontend/src/components/`、`frontend/src/hooks/useChatStream.ts`、`frontend/src/styles.css`
- 用户体验：更清晰的对话结构、更美观的界面、更好的节点执行可视化
- 可维护性：组件化设计，易于扩展和维护

## Additional Features Implemented

- ✅ **品牌更新**：应用名称更新为 "GravAIty"，使用黑洞图标
- ✅ **持久化**：实现 `localStorage` 持久化，保存线程列表和活跃线程 ID
- ✅ **主题切换**：添加暗黑/浅色模式切换功能
- ✅ **输入框优化**：移除 Send 按钮，改为 Enter 发送，Shift+Enter 换行，添加提示文字
- ✅ **UI 细节优化**：
  - 消息颜色与侧边栏保持一致（`#050816`）
  - 输入框 hover 动效描边
  - New Chat 按钮样式优化（深紫色背景 + 浅紫色边框 + 星形图标）
  - 用户信息区域移除分隔线
  - 默认用户名为 "zzxt"，邮箱为 "yrgu.example@gmail.com"
- ✅ **后端 Logo 更新**：启动脚本中的 ASCII logo 更新为 "GravAIty"

