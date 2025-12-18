# Change: Add "My Projects" Listing Tool + Temporarily Disable Retrieval Tool

## Why

Users frequently ask questions like:
- “当前我有哪些项目？”
- “哪些项目还没受理 / 已受理 / 已立项？”

The current `search_projects` tool is optimized for keyword-based full-text search and returning details for specific projects, but it is not the best entrypoint for listing a user’s projects by status.

Additionally, the current `retrieve_context` tool implies a vector-embedding workflow that is not yet integrated with the frontend document upload UX; temporarily disabling it keeps the toolset clean and avoids confusing behavior.

## What Changes

- **New tool**: `list_my_projects(status: str | None)`
  - Calls: `GET https://www.gravaity-cybernaut.top/api/projects/my`
  - Optional query param: `status` (when omitted, fetch all statuses)
    - Allowed values: `received`, `accepted`, `initiated`, `invested`, `tracking`, `archived`, `rejected`
  - Auth: requires the current end-user bearer token from the incoming Agent request (request-scoped, not exposed to the LLM)
  - Returns a concise, structured summary for LLM (grouped or list with key fields)
  - Response parsing: supports common response shapes including `{ "projects": [...] }` and `{ "items": [...] }`

- **Prompt update**: Update `src/agent/prompts.py` so the agent:
  - Uses `list_my_projects` as the **first choice** for “我的项目/项目状态列表” queries
  - Uses `search_projects` for “查某个项目具体内容/关键词/全文搜索” queries

- **Temporarily disable**: `retrieve_context` tool registration
  - Keep code present but comment out registration in `tools/toolkit.py`
  - This is reversible when frontend embedding flow is ready

## Impact

- **Affected code**:
  - `src/tools/` (new tool module)
  - `src/tools/toolkit.py` (tool registry changes)
  - `src/agent/prompts.py` (decision rules updated)

- **Breaking changes**: None (toolset behavior changes, but API contracts unchanged)

## Open Questions

- None.

## Success Criteria

- [ ] Asking “我有哪些项目？” triggers `list_my_projects`.
- [ ] Asking status-filtered questions (received/accepted/initiated/invested/tracking/archived/rejected) returns a clear grouped answer.
- [ ] Asking “查某个项目的 xxx 细节/关键词” triggers `search_projects`.
- [ ] `retrieve_context` is not available to the model (temporarily), reducing irrelevant tool calls.
