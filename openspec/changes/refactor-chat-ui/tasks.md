## 1. 修复重复消息问题
- [x] 1.1 修复 token 流和 output 消息重复创建 assistant 消息的问题
- [x] 1.2 统一消息处理逻辑：token 流只更新已存在的 assistant 消息，output 消息不再提取 AI 消息

## 2. 重构消息结构
- [x] 2.1 定义 Turn 和 NodeStep 类型
- [x] 2.2 在 ChatWindow 中组织消息为 Turn 结构（用户消息、节点步骤、AI 回复）

## 3. 创建时间轴组件
- [x] 3.1 创建 NodeStep 组件：单个节点步骤，支持展开/折叠
- [x] 3.2 创建 NodeTimeline 组件：纵向时间轴展示节点执行过程
- [x] 3.3 创建 TurnView 组件：整合用户消息、节点时间轴、AI 回复

## 4. UI 美化
- [x] 4.1 添加用户/助手头像组件
- [x] 4.2 添加消息时间戳显示
- [x] 4.3 优化消息气泡样式
- [x] 4.4 实现时间轴样式：连接线、节点图标、状态指示器

## 5. Sidebar 优化
- [x] 5.1 添加品牌标识（Logo + 标题）
- [x] 5.2 添加搜索功能
- [x] 5.3 添加线程分组（TODAY / OLDER）
- [x] 5.4 添加导航链接（LangSmith、Community Forum、Documentation）

## 6. 样式优化
- [x] 6.1 参考 Chat LangChain 设计，优化整体视觉风格
- [x] 6.2 添加响应式布局支持
- [x] 6.3 优化深色主题配色

## 7. 品牌与持久化
- [x] 7.1 更新应用品牌为 "GravAIty"，使用黑洞图标
- [x] 7.2 实现 localStorage 持久化（线程列表、活跃线程 ID）
- [x] 7.3 添加主题切换功能（暗黑/浅色模式）

## 8. UI 细节优化
- [x] 8.1 优化输入框：移除 Send 按钮，添加 Enter/Shift+Enter 提示
- [x] 8.2 统一消息颜色与侧边栏一致
- [x] 8.3 优化 New Chat 按钮样式
- [x] 8.4 优化用户信息区域（移除分隔线，更新默认用户信息）
- [x] 8.5 更新后端启动脚本 Logo 为 "GravAIty"

