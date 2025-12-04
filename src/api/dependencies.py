"""Common FastAPI dependencies."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from infra.redis_pubsub import RedisPublisher


def get_graph(request: Request):
    """从 FastAPI 应用状态中获取编译后的 LangGraph 工作流实例。

    ✅ 流程：
    1. 从 request.app.state 中获取 graph 属性
    2. 如果 graph 不存在，返回 503 错误
    3. 返回 graph 实例

    参数：
    - request: FastAPI Request 对象，包含应用状态

    返回：
    - graph: LangGraph 编译后的工作流实例

    异常：
    - HTTPException 503: 如果 graph 未初始化（服务未就绪）

    注意：
    - graph 在应用启动时通过 lifespan 事件初始化
    - 使用依赖注入模式，自动注入到路由处理函数
    """
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph is not ready yet",
        )
    return graph


def get_redis_publisher() -> RedisPublisher:
    """获取 Redis 发布器实例。

    ✅ 流程：
    1. 创建 RedisPublisher 实例
    2. 如果 REDIS_URL 未配置，抛出 RuntimeError
    3. 转换为 HTTPException 503 返回给客户端

    返回：
    - RedisPublisher: Redis 发布器实例

    异常：
    - HTTPException 503: 如果 REDIS_URL 未配置（服务未就绪）

    注意：
    - 使用依赖注入模式，自动注入到路由处理函数
    - RedisPublisher 内部使用单例 Redis 客户端
    """
    try:
        return RedisPublisher()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


__all__ = ["get_graph", "get_redis_publisher"]

