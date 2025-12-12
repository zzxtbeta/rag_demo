"""memory_store.py - 工作流内存存储管理。"""

from typing import Optional, cast, Any
from langgraph.store.postgres.aio import AsyncPostgresStore
from psycopg.rows import dict_row
import logging
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class MemoryStoreManager:
    """工作流内存存储管理器"""

    _instance: Optional["MemoryStoreManager"] = None
    _store: Optional[AsyncPostgresStore] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(cls, db_uri: str = None, max_size: int = 20) -> None:
        """
        初始化内存存储管理器

        参数：
            db_uri: 数据库连接 URI（未使用，为兼容性保留）
            max_size: 最大连接数（未使用，为兼容性保留）
        
        注意：
            DatabaseManager 必须在调用此方法前初始化。
            db_uri 和 max_size 参数为了向后兼容性保留
            但不再使用。
        """
        if cls._store is not None:
            logger.debug("内存存储已经初始化，跳过")
            return

        try:
            # 从 DatabaseManager 获取已初始化的池
            pool = await DatabaseManager.get_pool()
            conn = await pool.getconn()
            conn.row_factory = dict_row

            # 初始化内存存储
            # 将池转换为预期的类型以满足 mypy
            cls._store = AsyncPostgresStore(conn)
            await cls._store.setup()
            logger.info("内存存储初始化成功")
        except Exception as e:
            logger.error(f"初始化内存存储失败：{str(e)}")
            raise

    @classmethod
    async def get_store(cls) -> AsyncPostgresStore:
        """
        获取内存存储实例

        返回：
            AsyncPostgresStore: 内存存储实例

        会扔出：
            RuntimeError: 如果内存存储未初始化
        """
        if cls._store is None:
            raise RuntimeError("内存存储未初始化。请先调用 initialize() 方法。")
        return cls._store

    @classmethod
    async def close(cls) -> None:
        """关闭内存存储管理器"""
        cls._store = None
        logger.info("内存存储已成功关闭")