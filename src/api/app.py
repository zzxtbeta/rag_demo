"""暴露 LangGraph 工作流的 FastAPI 应用。"""

from __future__ import annotations

import sys

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Windows 需要选择器事件循环以实现 psycopg/asyncio 兼容性
if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from agent.graph import build_graph
from db.checkpointer import CheckpointerManager
from db.database import DatabaseManager
from api.routes.chat import router as chat_router
from api.routes.stream import router as stream_router
from api.routes.documents import router as documents_router


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

    # 为前端启用 CORS（例如，5173 上的 Vite 开发服务器）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router, prefix="/chat", tags=["chat"])
    app.include_router(stream_router, tags=["stream"])
    app.include_router(documents_router, prefix="/documents", tags=["documents"])
    return app


app = create_app()

__all__ = ["app", "create_app"]

