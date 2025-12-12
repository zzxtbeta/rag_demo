"""PostgreSQL 支持的 checkpointer 管理器。"""

from __future__ import annotations

import logging
from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from config.settings import get_settings
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class CheckpointerManager:
    """LangGraph AsyncPostgresSaver 的单例包装器。"""

    _checkpointer: Optional[AsyncPostgresSaver] = None

    @classmethod
    async def initialize(cls, db_uri: Optional[str] = None) -> None:
        """初始化 Postgres 支持的 checkpointer。"""
        if cls._checkpointer is not None:
            logger.debug("Checkpointer already initialized")
            return

        settings = get_settings()
        await DatabaseManager.initialize(db_uri=db_uri)
        pool = await DatabaseManager.get_pool()

        try:
            saver = AsyncPostgresSaver(pool)
            await saver.setup()
            cls._checkpointer = saver
            logger.info("Checkpointer initialized successfully")
        except Exception as exc:
            logger.error("Failed to initialize checkpointer: %s", exc)
            raise

    @classmethod
    def get_checkpointer(cls) -> AsyncPostgresSaver:
        """返回活跃的 checkpointer 实例。"""
        if cls._checkpointer is None:
            raise RuntimeError("Checkpointer not initialized")
        return cls._checkpointer

    @classmethod
    async def close(cls) -> None:
        """清除 checkpointer 实例。"""
        if cls._checkpointer is not None:
            close = getattr(cls._checkpointer, "aclose", None)
            if callable(close):
                await close()
            cls._checkpointer = None
            logger.info("Checkpointer closed")


__all__ = ["CheckpointerManager"]
