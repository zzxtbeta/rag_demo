"""memory_store.py"""

from typing import Optional, cast, Any
from langgraph.store.postgres.aio import AsyncPostgresStore
from psycopg.rows import dict_row
import logging
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class MemoryStoreManager:
    """Workflow memory store manager"""

    _instance: Optional["MemoryStoreManager"] = None
    _store: Optional[AsyncPostgresStore] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(cls, db_uri: str = None, max_size: int = 20) -> None:
        """
        Initialize the memory store manager

        Args:
            db_uri: database connection URI (unused, kept for compatibility)
            max_size: maximum number of connections (unused, kept for compatibility)
        
        Note:
            DatabaseManager must be initialized before calling this method.
            The db_uri and max_size parameters are kept for backward compatibility
            but are no longer used.
        """
        if cls._store is not None:
            logger.debug("Memory store already initialized, skipping")
            return

        try:
            # Get the already initialized pool from DatabaseManager
            pool = await DatabaseManager.get_pool()
            conn = await pool.getconn()
            conn.row_factory = dict_row

            # initialize the memory store
            # Cast the pool to the expected type to satisfy mypy
            cls._store = AsyncPostgresStore(conn)
            await cls._store.setup()
            logger.info("Memory store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize memory store: {str(e)}")
            raise

    @classmethod
    async def get_store(cls) -> AsyncPostgresStore:
        """
        Get the memory store instance

        Returns:
            AsyncPostgresStore: memory store instance

        Raises:
            RuntimeError: if the memory store is not initialized
        """
        if cls._store is None:
            raise RuntimeError("Memory store not initialized. Call initialize() first.")
        return cls._store

    @classmethod
    async def close(cls) -> None:
        """Close the memory store manager"""
        cls._store = None
        logger.info("Memory store closed successfully") 