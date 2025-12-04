"""Database connection utilities."""

from __future__ import annotations

import logging
from typing import Optional

from psycopg_pool import ConnectionPool

from config.settings import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Synchronous connection pool manager for PostgreSQL."""

    _pool: Optional[ConnectionPool] = None

    @classmethod
    def initialize(cls, db_uri: Optional[str] = None, max_size: int = 20) -> None:
        """Initialize the global connection pool."""
        if cls._pool is not None:
            logger.debug("Database connection pool already initialized")
            return

        settings = get_settings()
        conninfo = db_uri or settings.postgres_connection_string

        try:
            cls._pool = ConnectionPool(
                conninfo=conninfo,
                max_size=max_size,
                kwargs={"autocommit": True, "prepare_threshold": 0},
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as exc:
            logger.error("Failed to initialize database pool: %s", exc)
            raise

    @classmethod
    def get_pool(cls) -> ConnectionPool:
        """Return the connection pool, initializing it if necessary."""
        if cls._pool is None:
            cls.initialize()
        return cls._pool

    @classmethod
    def close(cls) -> None:
        """Close the connection pool."""
        if cls._pool is not None:
            cls._pool.close()
            cls._pool = None
            logger.info("Database connection pool closed")


__all__ = ["DatabaseManager"]
