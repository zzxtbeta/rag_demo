"""暴露 LangGraph 工作流的 FastAPI 应用。"""

from __future__ import annotations

import sys

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

# Windows 需要选择器事件循环以实现 psycopg/asyncio 兼容性
if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from agent.graph import build_graph
from api.dependencies import require_user, verify_jwt_token
from db.checkpointer import CheckpointerManager
from db.database import DatabaseManager
from api.routes.chat import router as chat_router
from api.routes.stream import router as stream_router
from api.routes.documents import router as documents_router
from config.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """管理 API 生命周期的资源。"""
    await DatabaseManager.initialize()
    await CheckpointerManager.initialize()

    checkpointer = CheckpointerManager.get_checkpointer()
    app.state.graph = build_graph(checkpointer=checkpointer)

    try:
        yield
    finally:
        await CheckpointerManager.close()
        await DatabaseManager.close()


def create_app() -> FastAPI:
    """为 FastAPI 应用程序的工厂。"""
    app = FastAPI(title="RAG Agent API", version="1.0.0", lifespan=lifespan)

    @app.middleware("http")
    async def _protect_docs(request: Request, call_next):
        settings = get_settings()
        if settings.auth_enabled:
            path = request.url.path
            if path == "/openapi.json" or path.startswith("/docs") or path.startswith("/redoc"):
                auth = request.headers.get("authorization")
                if not auth or not auth.lower().startswith("bearer "):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Missing bearer token",
                    )
                token = auth.split(" ", 1)[1].strip()
                verify_jwt_token(token)
        return await call_next(request)

    # 为前端启用 CORS（例如，5173 上的 Vite 开发服务器）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(
        chat_router,
        prefix="/chat",
        tags=["chat"],
        dependencies=[Depends(require_user)],
    )
    app.include_router(
        stream_router,
        tags=["stream"],
    )
    app.include_router(
        documents_router,
        prefix="/documents",
        tags=["documents"],
    )
    return app


_agent_app = create_app()


@asynccontextmanager
async def _outer_lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with _agent_app.router.lifespan_context(_agent_app):
        yield

# NOTE:
# `root_path` 仅用于反向代理场景（例如由网关把 /agent 前缀剥离后转发到本服务）。
# 如果你希望本服务自身就以 /agent 前缀对外暴露路由（包括 /agent/docs），
# 需要使用 mount。
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=_outer_lifespan)
app.mount("/agent", _agent_app)

__all__ = ["app", "create_app"]

