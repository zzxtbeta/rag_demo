"""My projects listing tool - query external project management API."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Optional

import httpx
from langchain.tools import tool

from config.settings import get_settings
from infra.request_context import get_access_token

logger = logging.getLogger(__name__)

API_TIMEOUT = 10

STATUS_LABELS: dict[str, str] = {
    "received": "已接收",
    "accepted": "已受理",
    "initiated": "已立项",
    "invested": "已投资",
    "tracking": "跟踪中",
    "archived": "已归档",
    "rejected": "已拒绝",
}


async def _list_my_projects_with_token(*, api_url: str, token: str, status: Optional[str]) -> object:
    params: dict[str, str] = {}
    if status:
        params["status"] = status

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{api_url.rstrip('/')}/api/projects/my",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()


def _as_project_list(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if isinstance(payload, dict):
        for key in ("projects", "items", "data", "results"):
            items = payload.get(key)
            if isinstance(items, list):
                return [p for p in items if isinstance(p, dict)]
    return []


def _project_status(project: dict) -> Optional[str]:
    raw = project.get("status") or project.get("project_status")
    if isinstance(raw, str):
        return raw
    return None


def _format_project_brief(project: dict) -> str:
    project_id = project.get("id") or project.get("project_id")
    name = project.get("project_name") or project.get("name") or project.get("title")
    company = project.get("company_name") or project.get("company")
    status = _project_status(project)
    status_label = STATUS_LABELS.get(status, status or "unknown")

    brief = {
        "id": project_id,
        "project_name": name,
        "company_name": company,
        "status": status,
        "status_label": status_label,
    }
    return json.dumps(brief, ensure_ascii=False)


@tool
async def list_my_projects(status: Optional[str] = None) -> str:
    """列出当前用户的项目列表，可按状态筛选。

    当用户询问："我有哪些项目"、"哪些项目是已受理/已立项"、"按状态统计" 等问题时优先使用。

    参数:
        status: 项目状态筛选（可选）。支持：received, accepted, initiated, invested, tracking, archived, rejected

    返回:
        按状态分组的简洁项目列表（JSON 行），便于 LLM 进一步总结。
    """

    settings = get_settings()

    if not settings.project_search_enabled:
        return "项目工具未启用"

    if not settings.project_search_api_url:
        return "项目服务未配置"

    if status is not None and status not in STATUS_LABELS:
        allowed = ", ".join(sorted(STATUS_LABELS.keys()))
        return f"不支持的 status: {status}。可选值: {allowed}"

    try:
        user_token = get_access_token()

        if not user_token:
            return "请先登录（缺少访问令牌）"

        payload = await _list_my_projects_with_token(
            api_url=settings.project_search_api_url,
            token=user_token,
            status=status,
        )

        projects = _as_project_list(payload)

        if not projects:
            if status:
                return f"未找到状态为 {status}（{STATUS_LABELS.get(status)}）的项目"
            return "未找到任何项目"

        grouped: dict[str, list[dict]] = defaultdict(list)
        for p in projects:
            grouped[_project_status(p) or "unknown"].append(p)

        lines: list[str] = []
        if status:
            lines.append(f"共 {len(projects)} 个项目（status={status} {STATUS_LABELS.get(status)}）：")
            for p in projects[:50]:
                lines.append(_format_project_brief(p))
            return "\n".join(lines)

        # No filter: group by status for easy overview
        total = len(projects)
        lines.append(f"共 {total} 个项目（按状态分组）：")
        for st in sorted(grouped.keys()):
            label = STATUS_LABELS.get(st, st)
            lines.append(f"\n[{st}] {label}：{len(grouped[st])} 个")
            for p in grouped[st][:20]:
                lines.append(_format_project_brief(p))

        return "\n".join(lines)

    except httpx.TimeoutException:
        logger.error("[MY_PROJECTS] API timeout")
        return "项目服务响应超时"
    except httpx.HTTPError as e:
        logger.error("[MY_PROJECTS] HTTP error: %s", str(e))
        return "项目服务暂时不可用"
    except Exception as e:  # noqa: BLE001
        logger.error("[MY_PROJECTS] Unexpected error: %s", str(e), exc_info=True)
        return "项目列表查询失败，请稍后重试"


__all__ = ["list_my_projects"]
