# Implementation Tasks: Add "My Projects" Listing Tool

## 1. Tool Implementation

- [x] 1.1 Create `src/tools/my_projects.py` (or similar) with a small HTTP client
- [x] 1.2 Implement token acquisition (reuse the auth approach from `ProjectSearchClient`)
- [x] 1.3 Implement `list_my_projects(status: str | None)` tool
- [x] 1.4 Format output concisely (stable fields, easy to scan)

## 2. Tool Registration

- [x] 2.1 Register `list_my_projects` in `src/tools/toolkit.py`
- [x] 2.2 Ensure it is always available when project search is enabled (or add a dedicated feature flag if needed)

## 3. Prompt Update

- [x] 3.1 Update `src/agent/prompts.py` tool list and tool usage rules
- [x] 3.2 Add clear routing guidance:
  - “我的项目/状态列表” -> `list_my_projects`
  - “查具体项目内容/关键词” -> `search_projects`

## 4. Temporarily Disable Retrieval Tool

- [x] 4.1 Comment out `retrieve_context` registration in `src/tools/toolkit.py` (both model tools + tool node tools)
- [x] 4.2 Update prompt to remove references to `retrieve_context`

## 5. Validation

- [x] 5.1 Manual test: ask “我有哪些项目？” (returns user-scoped projects based on current bearer token)
- [x] 5.2 Manual test: ask status-filtered questions using one of: received/accepted/initiated/invested/tracking/archived/rejected
- [x] 5.3 Manual test: ask a specific keyword query and verify `search_projects` is used
