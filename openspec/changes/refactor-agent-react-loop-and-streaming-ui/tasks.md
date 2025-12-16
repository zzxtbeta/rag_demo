## 1. Backend
- [x] 1.1 将工作流收敛为 Scheme A ReAct loop（`query_or_respond` ↔ `tools`）
- [x] 1.2 统一工具注册与 ToolNode 构建（按 request 开关启用 websearch）
- [x] 1.3 接入工具错误处理：异常转为 `ToolMessage(..., tool_call_id=...)`
- [x] 1.4 修复 async 工具调用路径：ToolNode 使用 `awrap_tool_call`，避免 sync 调用 async-only 工具
- [x] 1.5 修复 ASGI 阻塞：web_search 使用 `asyncio.to_thread()` 包装 Tavily 同步 `.invoke()`
- [x] 1.6 修复 history API：兼容 dict 序列化消息，正确 role/type 识别并过滤中间消息

## 2. Frontend
- [x] 2.1 修复实时渲染：避免把“工具调用草稿 assistant”当作最终回复
- [x] 2.2 token 流 assistant 绑定 nodeName，基于 output/tool_calls 回滚草稿并保留最终回答

## 3. Docs / Cleanup
- [x] 3.1 更新最佳实践文档：补充 ToolNode async wrapper 与 ASGI blocking 规避
- [x] 3.2 清理 `src/agent/` 未使用遗留代码（prompts/vectorstore/import）
