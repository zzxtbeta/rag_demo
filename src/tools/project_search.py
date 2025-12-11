"""Project search tool - Query external project management API."""

from __future__ import annotations

import logging
from typing import Optional
import httpx
from langchain.tools import tool

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# Tool configuration
API_TIMEOUT = 10
MAX_RETRIES = 1
RESULT_LIMIT = 1


class ProjectSearchClient:
    """Client for project management API with token caching."""

    def __init__(self, api_url: str, username: str, password: str):
        self.api_url = api_url.rstrip("/")
        self.username = username
        self.password = password
        self.token: Optional[str] = None

    async def _get_token(self) -> str:
        """Acquire or refresh authentication token."""
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
        Search projects by keyword.

        Args:
            query: Search keyword
            limit: Max results to return

        Returns:
            API response dict with 'items' and 'total' keys
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
                # Token expired, clear and retry once
                self.token = None
                logger.debug("[PROJECT_SEARCH] Token expired, refreshing...")
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
    """Format single project for LLM consumption."""
    lines = []
    lines.append(f"**{project.get('project_name', 'N/A')}**")

    if company := project.get("company_name"):
        lines.append(f"- 公司：{company}")

    if industry := project.get("industry"):
        lines.append(f"- 行业：{industry}")

    if tech := project.get("core_technology"):
        # Truncate if too long
        tech = tech[:200] + "..." if len(tech) > 200 else tech
        lines.append(f"- 核心技术：{tech}")

    if team := project.get("core_team"):
        if isinstance(team, list) and team:
            team_names = [t.get("name") for t in team if t.get("name")]
            if team_names:
                lines.append(f"- 团队：{', '.join(team_names)}")

    return "\n".join(lines)


async def _search_projects_impl(query: str) -> str:
    """Internal implementation of project search."""
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

        # Format top result
        formatted = f"找到 {result.get('total', 1)} 个相关项目：\n\n"
        formatted += _format_project(projects[0])

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
    Search project database by keyword.

    Use this tool when user asks about specific companies or projects.
    Examples: "象量科技的xxx", "融资信息", "团队背景"

    Args:
        query: Search keyword (e.g., company name, project name)

    Returns:
        Formatted project information or error message
    """
    return await _search_projects_impl(query)


__all__ = ["search_projects", "ProjectSearchClient"]
