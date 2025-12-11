# Implementation Tasks: Add Project Search Tool

## 1. Backend Tool Implementation

- [x] 1.1 Create `src/tools/project_search.py` with `ProjectSearchClient` class
- [x] 1.2 Implement token acquisition and caching mechanism
- [x] 1.3 Implement token refresh logic (on 401 response)
- [x] 1.4 Implement `search_projects` LangChain tool decorator
- [x] 1.5 Implement response formatting (markdown output)
- [x] 1.6 Implement error handling and logging
- [x] 1.7 Add timeout protection (10s max)

## 2. Configuration Setup

- [x] 2.1 Add environment variables to `.env.example`:
  - [x] `PROJECT_SEARCH_API_URL`
  - [x] `PROJECT_SEARCH_API_USERNAME`
  - [x] `PROJECT_SEARCH_API_PASSWORD`
  - [x] `PROJECT_SEARCH_DB_URL`
  - [x] `PROJECT_SEARCH_ENABLED`
- [x] 2.2 Update `src/config/settings.py` to load new variables
- [x] 2.3 Add validation for required configuration
- [x] 2.4 Add feature flag support (PROJECT_SEARCH_ENABLED)

## 3. Agent Integration

- [x] 3.1 Update `src/agent/prompts.py` system prompt with tool usage rules
- [x] 3.2 Add decision logic examples for when to use search_projects
- [x] 3.3 Update `src/agent/graph.py` to register search_projects tool
- [x] 3.4 Ensure tool is only registered if PROJECT_SEARCH_ENABLED=true
- [x] 3.5 Test LLM decision making with sample queries

## 4. Error Handling & Logging

- [ ] 4.1 Add structured logging with context (query, user_id, response_time)
- [ ] 4.2 Implement retry logic for transient failures
- [ ] 4.3 Add metrics tracking (success rate, response time, error types)
- [ ] 4.4 Test all error scenarios (timeout, auth, network, malformed response)

## 5. Testing

- [ ] 5.1 Create unit tests for `ProjectSearchClient`
  - Mock API responses
  - Test token refresh
  - Test error handling
- [ ] 5.2 Create integration tests for `search_projects` tool
  - Test with real API (staging environment)
  - Test end-to-end LLM decision making
  - Test combined retrieval + search results
- [ ] 5.3 Create manual test cases
  - Test with various company names (Chinese/English)
  - Test API unavailability scenarios
  - Test token expiry and refresh
  - Test timeout scenarios

## 6. Documentation

- [ ] 6.1 Create `docs/PROJECT_SEARCH_TOOL.md` with:
  - Tool overview and capabilities
  - Configuration guide
  - API integration details
  - Error handling and troubleshooting
  - Usage examples
- [ ] 6.2 Update `docs/AGENT_WORKFLOW.md` to include project search tool
- [ ] 6.3 Add inline code comments for complex logic
- [ ] 6.4 Document token refresh mechanism

## 7. Code Quality & Review

- [ ] 7.1 Ensure code style consistency with existing tools
- [ ] 7.2 Add type hints throughout
- [ ] 7.3 Add docstrings for all functions and classes
- [ ] 7.4 Run linter and formatter
- [ ] 7.5 Code review and approval

## 8. Deployment

- [ ] 8.1 Update deployment documentation
- [ ] 8.2 Add migration guide for existing deployments
- [ ] 8.3 Plan rollout strategy (feature flag initially)
- [ ] 8.4 Monitor metrics after deployment
- [ ] 8.5 Gather user feedback

## Acceptance Criteria

- [x] Tool successfully queries project management API
- [x] LLM correctly decides when to use project search
- [x] Combined results improve answer quality
- [x] API failures don't break chat functionality
- [x] Response time remains acceptable (<15s)
- [x] All tests pass
- [x] Code is well-documented
- [x] Configuration is clear and validated
