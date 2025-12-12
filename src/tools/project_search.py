"""项目搜索工具 - 查询外部项目管理 API。"""

from __future__ import annotations

import logging
from typing import Optional
import httpx
from langchain.tools import tool

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# 工具配置
API_TIMEOUT = 10
MAX_RETRIES = 1
RESULT_LIMIT = 5


class ProjectSearchClient:
    """项目管理 API 客户端，带有令牡缓存。"""

    def __init__(self, api_url: str, username: str, password: str):
        self.api_url = api_url.rstrip("/")
        self.username = username
        self.password = password
        self.token: Optional[str] = None

    async def _get_token(self) -> str:
        """获取或刷新认证令牡。"""
        if self.token:
            return self.token

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/api/auth/token",
                    data={
                        "grant_type": "password",
                        "username": self.username,
                        "password": self.password,
                    },
                    timeout=API_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
                self.token = data["access_token"]
                logger.debug("[PROJECT_SEARCH] Token acquired successfully")
                return self.token
        except Exception as e:
            logger.error(f"[PROJECT_SEARCH] Token acquisition failed: {str(e)}")
            raise

    async def search(self, query: str, limit: int = RESULT_LIMIT) -> dict:
        """
        按关键词搜索项目。

        参数：
            query: 搜索关键词
            limit: 返回的最大结果数

        返回：
            API 响应字典，包含 'items' 和 'total' 键
        """
        token = await self._get_token()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/api/projects/search",
                    params={"query": query, "limit": limit, "offset": 0},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=API_TIMEOUT,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # 令牡已过期，清除并重试一次
                self.token = None
                logger.debug("[PROJECT_SEARCH] 令牡已过期，正在刷新...")
                token = await self._get_token()
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.api_url}/api/projects/search",
                        params={"query": query, "limit": limit, "offset": 0},
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=API_TIMEOUT,
                    )
                    response.raise_for_status()
                    return response.json()
            raise
        except Exception as e:
            logger.error(f"[PROJECT_SEARCH] API call failed: {str(e)}")
            raise


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

    if not settings.project_search_api_username or not settings.project_search_api_password:
        logger.warning("[PROJECT_SEARCH] API credentials not configured")
        return "项目搜索服务认证信息未配置"

    try:
        client = ProjectSearchClient(
            api_url=settings.project_search_api_url,
            username=settings.project_search_api_username,
            password=settings.project_search_api_password,
        )

        logger.info(f"[PROJECT_SEARCH] Searching for: {query}")
        result = await client.search(query, limit=RESULT_LIMIT)

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


__all__ = ["search_projects", "ProjectSearchClient"]
