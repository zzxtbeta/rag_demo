"""FastAPI application exposing the LangGraph workflow."""

from __future__ import annotations

import sys

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI

# Windows needs selector event loop for psycopg/asyncio compatibility
if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from agent.graph import build_graph
from db.checkpointer import CheckpointerManager
from db.database import DatabaseManager
from api.routes.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage resources for the API lifecycle."""
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
    """Factory for FastAPI app."""
    app = FastAPI(title="RAG Agent API", version="1.0.0", lifespan=lifespan)
    app.include_router(chat_router, prefix="/chat", tags=["chat"])
    return app


app = create_app()

__all__ = ["app", "create_app"]

