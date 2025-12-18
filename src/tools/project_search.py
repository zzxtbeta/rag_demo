"""项目搜索工具 - 查询外部项目管理 API。"""

from __future__ import annotations

import logging
import httpx
from langchain.tools import tool

from config.settings import get_settings
from infra.request_context import get_access_token

logger = logging.getLogger(__name__)

# 工具配置
API_TIMEOUT = 10
RESULT_LIMIT = 5


def _format_project(project: dict) -> str:
    """以格式化 JSON 字符串的形式返回完整的项目数据供 LLM 使用。"""
    import json
    return json.dumps(project, ensure_ascii=False, indent=2)


async def _search_projects_impl(query: str) -> str:
    """项目搜索的内部实现。"""
    settings = get_settings()

    if not settings.project_search_enabled:
        return "项目搜索功能未启用"

    if not settings.project_search_api_url:
        logger.warning("[PROJECT_SEARCH] API URL not configured")
        return "项目搜索服务未配置"

    user_token = get_access_token()
    if not user_token:
        return "请先登录（缺少访问令牌）"

    try:
        logger.info(f"[PROJECT_SEARCH] Searching for: {query}")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.project_search_api_url.rstrip('/')}/api/projects/search",
                params={"query": query, "limit": RESULT_LIMIT, "offset": 0},
                headers={"Authorization": f"Bearer {user_token}"},
                timeout=API_TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()

        projects = result.get("items", [])
        if not projects:
            logger.info(f"[PROJECT_SEARCH] No results found for: {query}")
            return f"未找到与 '{query}' 相关的项目"

        # Format all results
        formatted = f"找到 {result.get('total', len(projects))} 个相关项目：\n\n"
        for i, project in enumerate(projects, 1):
            formatted += f"【项目 {i}】\n"
            formatted += _format_project(project)
            if i < len(projects):
                formatted += "\n\n---\n\n"

        logger.info(f"[PROJECT_SEARCH] Found {len(projects)} result(s)")
        return formatted

    except httpx.TimeoutException:
        logger.error("[PROJECT_SEARCH] API timeout")
        return "项目搜索服务响应超时"
    except httpx.HTTPError as e:
        logger.error(f"[PROJECT_SEARCH] HTTP error: {str(e)}")
        return "项目搜索服务暂时不可用"
    except Exception as e:
        logger.error(f"[PROJECT_SEARCH] Unexpected error: {str(e)}", exc_info=True)
        return "项目搜索失败，请稍后重试"


@tool
async def search_projects(query: str) -> str:
    """
    按关键词搜索项目数据库。支持单个或多个搜索关键词。

    当用户询问特定公司或项目时使用此工具。无需多次调用，可在单次调用中传入多个关键词。
    示例提问："象量科技的xxx"、"融资信息"、"团队背景"

    参数：
        query: 搜索关键词，支持单个关键词或多个关键词（例如，公司名称、项目名称）

    返回：
        格式化的项目信息或错误消息
    """
    return await _search_projects_impl(query)


__all__ = ["search_projects"]
