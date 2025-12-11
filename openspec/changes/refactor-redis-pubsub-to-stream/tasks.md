# Tasks: Redis Stream Migration Implementation

## 1. 准备和验证

- [ ] 1.1 检查 Redis 版本支持（5.0+）
- [ ] 1.2 添加 REDIS_STREAM_ENABLED 配置到 settings.py
- [ ] 1.3 实现 Redis Stream 版本检查函数
- [ ] 1.4 创建测试 Redis 环境

## 2. 修改 RedisPublisher（src/infra/redis_pubsub.py）

- [ ] 2.1 添加 `_stream_key()` 静态方法生成 Stream key
- [ ] 2.2 实现 `publish_to_stream()` 方法（XADD）
- [ ] 2.3 实现 `_trim_stream()` 方法（XTRIM + EXPIRE）
- [ ] 2.4 修改 `publish_node_output()` 支持 Stream 发布
- [ ] 2.5 修改 `publish_workflow_complete()` 支持 Stream 发布
- [ ] 2.6 修改 `publish_workflow_error()` 支持 Stream 发布
- [ ] 2.7 保留 Pub/Sub 发布逻辑（向后兼容）
- [ ] 2.8 添加功能开关判断（if settings.redis_stream_enabled）

## 3. 修改 WebSocket 订阅（src/api/routes/stream.py）

- [ ] 3.1 实现 `_read_stream_history()` 方法（XRANGE）
- [ ] 3.2 实现 `_read_stream_new()` 方法（XREAD 阻塞）
- [ ] 3.3 修改 `websocket_stream()` 支持 Stream 订阅
- [ ] 3.4 添加 `last_id` 查询参数支持（续订）
- [ ] 3.5 添加错误处理和重试逻辑
- [ ] 3.6 保留 Pub/Sub 降级逻辑
- [ ] 3.7 添加功能开关判断

## 4. 单元测试（tests/unit_tests/）

- [ ] 4.1 创建 test_redis_stream.py
- [ ] 4.2 测试 `_stream_key()` 生成
- [ ] 4.3 测试 `publish_to_stream()` 发布消息
- [ ] 4.4 测试 `_trim_stream()` 自动清理
- [ ] 4.5 测试消息序列化（JSON 兼容性）
- [ ] 4.6 测试 XRANGE 历史查询
- [ ] 4.7 测试 XREAD 阻塞读取
- [ ] 4.8 测试续订逻辑（from last_id）

## 5. 集成测试（tests/integration_tests/）

- [ ] 5.1 创建 test_stream_workflow.py
- [ ] 5.2 测试完整工作流事件流
- [ ] 5.3 测试页面刷新后恢复历史
- [ ] 5.4 测试网络中断和续订
- [ ] 5.5 测试多个并发工作流
- [ ] 5.6 测试消息顺序保证
- [ ] 5.7 测试自动清理（XTRIM）

## 6. 性能测试（tests/performance/）

- [ ] 6.1 创建 benchmark_stream_vs_pubsub.py
- [ ] 6.2 测试发布延迟（Pub/Sub vs Stream）
- [ ] 6.3 测试订阅延迟（Pub/Sub vs Stream）
- [ ] 6.4 测试内存占用（Stream 持久化）
- [ ] 6.5 测试高并发场景（100+ 并发工作流）
- [ ] 6.6 生成性能报告

## 7. 文档和配置

- [ ] 7.1 更新 .env.example 添加 REDIS_STREAM_ENABLED
- [ ] 7.2 更新 README.md 说明 Redis Stream 功能
- [ ] 7.3 更新 docs/REDIS_STREAMING.md（如存在）
- [ ] 7.4 添加迁移指南文档
- [ ] 7.5 添加故障排查指南

## 8. 灰度发布准备

- [ ] 8.1 准备灰度发布计划文档
- [ ] 8.2 准备监控告警规则
- [ ] 8.3 准备回滚方案
- [ ] 8.4 准备客户沟通方案

## 9. 代码审查和优化

- [ ] 9.1 代码审查（RedisPublisher 改动）
- [ ] 9.2 代码审查（WebSocket 改动）
- [ ] 9.3 性能优化（如需要）
- [ ] 9.4 安全审查（Redis 连接、权限）

## 10. 部署和验证

- [ ] 10.1 在测试环境部署（REDIS_STREAM_ENABLED=false）
- [ ] 10.2 验证 Pub/Sub 功能正常
- [ ] 10.3 启用 Stream（REDIS_STREAM_ENABLED=true）
- [ ] 10.4 验证 Stream 功能正常
- [ ] 10.5 对比性能指标
- [ ] 10.6 生产环境灰度发布（10% → 50% → 100%）
- [ ] 10.7 监控 1 周，确保稳定

## 11. 清理和存档

- [ ] 11.1 如果完全迁移，移除 Pub/Sub 代码
- [ ] 11.2 更新 OpenSpec 规范
- [ ] 11.3 存档 OpenSpec 变更
- [ ] 11.4 发布发布说明（Release Notes）

---

## 预期工作量

| 阶段 | 任务数 | 预期时间 |
|------|--------|---------|
| 准备 | 4 | 1-2 天 |
| 实现 | 14 | 3-5 天 |
| 测试 | 14 | 2-3 天 |
| 文档 | 5 | 1 天 |
| 部署 | 7 | 3-5 天 |
| **总计** | **44** | **10-16 天** |

---

## 依赖关系

```
准备 (1-2天)
    ↓
实现 (3-5天)
    ├─ RedisPublisher 改动
    └─ WebSocket 改动
    ↓
单元测试 (1-2天)
    ↓
集成测试 (1-2天)
    ↓
性能测试 (1天)
    ↓
文档 (1天)
    ↓
灰度发布 (3-5天)
    ↓
清理和存档 (1天)
```

---

## 风险和缓解

| 风险 | 缓解措施 | 负责人 |
|------|---------|--------|
| Redis 版本不支持 | 版本检查 + 降级方案 | 开发 |
| 性能下降 | 基准测试 + 监控 | QA |
| 内存占用增加 | XTRIM 限制 + 监控 | 运维 |
| 前端兼容性问题 | 保持消息格式 + 测试 | 前端 |
| 灰度发布失败 | 快速回滚方案 | 运维 |

---

## 成功标准

- ✅ 所有单元测试通过
- ✅ 所有集成测试通过
- ✅ 性能不低于 Pub/Sub
- ✅ 内存占用在预期范围内
- ✅ 生产环境运行 1 周无异常
- ✅ 用户反馈积极（页面刷新恢复历史）
