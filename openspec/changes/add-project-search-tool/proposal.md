# Change: Add Project Search Tool for Cross-Database RAG Enhancement

## Why

Current RAG system only retrieves from local PDF knowledge base, limiting answer quality when users ask about specific companies or projects. The project management system maintains a separate database with rich structured project metadata (company info, funding, team, technology stack, etc.).

By integrating a project search tool, we can:
- Provide accurate, up-to-date project information from the authoritative source
- Combine structured project data with document-based knowledge for comprehensive answers
- Support keyword extraction from user queries to trigger intelligent tool usage
- Maintain clear separation of concerns (black-box API integration)

## What Changes

- **New capability**: Project search tool that queries external project management API
- **New tool**: `search_projects` tool in LangGraph workflow
- **System prompt update**: Enhanced decision logic to trigger project search for company/project questions
- **Configuration**: API endpoint, authentication credentials, timeout settings
- **Error handling**: Graceful degradation when project search API is unavailable

## Impact

- **Affected specs**:
  - `rag-system` (modified - new tool integration)
  - `agent-workflow` (modified - updated system prompt)
- **Affected code**:
  - `src/tools/project_search.py` (new)
  - `src/agent/prompts.py` (modified - system prompt)
  - `src/agent/graph.py` (modified - tool registration)
  - `src/config/settings.py` (modified - API configuration)
  - `src/api/routes/chat.py` (modified - context passing)
- **Breaking changes**: None
- **Dependencies added**: None (uses existing `httpx`)
- **External dependencies**: Project management API (separate service)

## Design Principles

1. **Black-box integration**: Tool treats project search API as opaque service
   - No knowledge of database schema or query implementation
   - Only cares about input/output contract
   - Enables independent evolution of both systems

2. **Graceful degradation**: If project search fails, RAG continues with document retrieval alone
   - Timeout protection (10s max)
   - Clear error messages to LLM
   - No cascading failures

3. **Minimal coupling**: Tool is stateless and context-independent
   - Can be easily replaced or extended
   - No shared state with retrieval tool
   - Clear responsibility boundaries

## Success Criteria

- [ ] Tool successfully queries project management API with authentication
- [ ] LLM correctly decides when to use project search vs document retrieval
- [ ] Combined results (project data + documents) improve answer quality
- [ ] API failures don't break chat functionality
- [ ] Response time remains acceptable (<15s for combined search)
