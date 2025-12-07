"""LangSmith 客户端工具模块，用于查询 Trace 数据。"""

from __future__ import annotations

import logging
from typing import Optional

from langsmith import Client

from config.settings import get_settings

logger = logging.getLogger(__name__)


def get_langsmith_client() -> Optional[Client]:
    """
    创建 LangSmith 客户端实例。
    
    如果未配置 LANGCHAIN_API_KEY，返回 None。
    """
    settings = get_settings()
    if not settings.langsmith_api_key:
        logger.warning("LANGCHAIN_API_KEY not configured. LangSmith tracing disabled.")
        return None
    
    return Client(
        api_key=settings.langsmith_api_key,
        api_url=settings.langsmith_endpoint,
    )
