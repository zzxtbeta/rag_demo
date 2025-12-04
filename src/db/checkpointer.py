"""PostgreSQL-backed checkpointer manager."""

from __future__ import annotations

import logging
from typing import Optional

from langgraph.checkpoint.postgres import PostgresSaver

from config.settings import get_settings
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class CheckpointerManager:
    """Singleton wrapper around LangGraph PostgresSaver."""

    _checkpointer: Optional[PostgresSaver] = None

    @classmethod
    def initialize(cls, db_uri: Optional[str] = None) -> None:
        """Initialize the Postgres-backed checkpointer."""
        if cls._checkpointer is not None:
            logger.debug("Checkpointer already initialized")
            return

        settings = get_settings()
        DatabaseManager.initialize(db_uri=db_uri)

        pool = DatabaseManager.get_pool()
        try:
            saver = PostgresSaver(pool)
            saver.setup()
            cls._checkpointer = saver
            logger.info("Checkpointer initialized successfully")
        except Exception as exc:
            logger.error("Failed to initialize checkpointer: %s", exc)
            raise

    @classmethod
    def get_checkpointer(cls) -> PostgresSaver:
        """Return the active checkpointer instance."""
        if cls._checkpointer is None:
            cls.initialize()
        assert cls._checkpointer is not None
        return cls._checkpointer

    @classmethod
    def close(cls) -> None:
        """Clear the checkpointer instance."""
        cls._checkpointer = None
        logger.info("Checkpointer closed")


__all__ = ["CheckpointerManager"]
