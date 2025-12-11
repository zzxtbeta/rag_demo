# Design: Project Search Tool Integration

## Architecture Overview

```
User Query
    ↓
LLM (System Prompt)
    ├─ Decides: Is this a company/project question?
    ├─ YES → Trigger search_projects tool
    └─ NO → Skip to document retrieval
    ↓
Tool Execution (Parallel)
    ├─ search_projects(query) → Project Management API
    └─ retrieve_context(query) → Vector Store (PDF)
    ↓
Result Combination
    ├─ Format project data
    ├─ Format document excerpts
    └─ Pass combined context to LLM
    ↓
Final Answer
```

## Tool Interface

### Input Contract

```python
@tool
async def search_projects(query: str) -> str:
    """
    Search project database by keyword.
    
    Args:
        query: Search keyword extracted from user question
               (e.g., "象量科技", "AI芯片", "融资")
    
    Returns:
        Formatted project information as markdown string
    """
```

### Output Contract

Tool returns formatted markdown string containing:
- Project name
- Company name
- Industry
- Core technology
- Description
- Team information (if available)

Example:
```
找到 1 个相关项目：

**AI+大数据投资研究智能体**
- 公司：象量科技 ELEQUANT
- 行业：人工智能
- 核心技术：大模型、AIGC、数据治理
- 描述：通过AI专业大模型技术，打造一体化的投资研究和融资对接智能体...
```

## API Integration Details

### External API Specification

**Endpoint**: `GET /api/projects/search`

**Authentication**: Bearer token (OAuth2)

**Request Parameters**:
```
query: str (required)     # Search keyword
limit: int (default: 10)  # Max results to return
offset: int (default: 0)  # Pagination offset
```

**Response Schema**:
```json
{
  "items": [
    {
      "id": "proj_xxx",
      "project_name": "string",
      "company_name": "string",
      "description": "string | null",
      "industry": "string | null",
      "core_technology": "string | null",
      "core_product": "string | null",
      "keywords": ["string"],
      "core_team": [
        {
          "name": "string",
          "role": "string",
          "background": "string"
        }
      ],
      "created_at": "ISO8601 datetime"
    }
  ],
  "total": int,
  "limit": int,
  "offset": int
}
```

**Error Responses**:
- `400`: Invalid query parameters
- `401`: Authentication failed
- `500`: Server error

### Authentication Flow

1. **Token Acquisition** (cached, refreshed on expiry):
   ```
   POST /api/auth/token
   - username: from config
   - password: from config
   → Returns: access_token (JWT)
   ```

2. **API Call with Token**:
   ```
   GET /api/projects/search?query=...
   Header: Authorization: Bearer {access_token}
   ```

3. **Token Refresh** (on 401):
   - Automatically re-authenticate
   - Retry original request
   - Max 1 retry to prevent infinite loops

## Configuration

### Environment Variables

```env
# Project Search API
PROJECT_SEARCH_API_URL=https://www.gravaity-cybernaut.top
PROJECT_SEARCH_API_USERNAME=B34
PROJECT_SEARCH_API_PASSWORD=12345678
PROJECT_SEARCH_API_TIMEOUT=10  # seconds
PROJECT_SEARCH_ENABLED=true    # Feature flag
```

### Settings Class

```python
@dataclass(frozen=True)
class Settings:
    project_search_api_url: str
    project_search_api_username: str
    project_search_api_password: str
    project_search_api_timeout: int = 10
    project_search_enabled: bool = True
```

## Tool Implementation Strategy

### File Structure

```
src/tools/
├── __init__.py
├── retrieval.py              # Existing: PDF retrieval
└── project_search.py         # New: Project search
```

### Key Components

1. **ProjectSearchClient** (Internal)
   - Manages API connection
   - Handles authentication and token caching
   - Implements retry logic
   - Timeout protection

2. **search_projects Tool** (LangChain Tool)
   - Accepts user query string
   - Calls ProjectSearchClient
   - Formats results for LLM
   - Returns markdown string

3. **Error Handling**
   - Network errors → Return helpful message
   - Auth errors → Log and retry
   - Timeout → Return "service unavailable"
   - Invalid response → Log and return empty

### Response Formatting

Tool formats API response into readable markdown:
- Top result only (limit to 1 for clarity)
- Key fields: name, company, industry, tech, team
- Omit null/empty fields
- Preserve original data integrity

## System Prompt Integration

### Decision Logic

Update `SYSTEM_PROMPT` in `src/agent/prompts.py`:

```python
SYSTEM_PROMPT = """...
Available tools:
- retrieve_context(query): Search PDF knowledge base
- search_projects(query): Search project database

TOOL USAGE RULES:
1. For company/project questions → ALWAYS use search_projects first
   Examples: "象量科技的xxx", "融资信息", "团队背景"
2. For document/knowledge questions → Use retrieve_context
   Examples: "PDF中提到的xxx", "文档内容"
3. For combined questions → Use BOTH tools
   Example: "象量科技的融资情况和相关文档"

When using search_projects:
- Extract company/project name from user query
- Pass as search keyword
- If tool returns results, cite them in answer
- If tool returns empty, acknowledge and use document knowledge
"""
```

## Error Handling Strategy

### Graceful Degradation

```
Tool Call Fails
    ↓
Log Error (with context)
    ↓
Return User-Friendly Message
    ↓
Continue with Document Retrieval
    ↓
Provide Best-Effort Answer
```

### Specific Scenarios

| Scenario | Behavior |
|----------|----------|
| API timeout | Return "Service temporarily unavailable" |
| Auth failure | Log error, don't retry (config issue) |
| Network error | Return "Connection failed, using document knowledge" |
| Empty results | Return "No projects found for this keyword" |
| Malformed response | Log error, return empty results |

## Performance Considerations

### Timeout Strategy
- API call timeout: 10 seconds
- Total tool execution: <15 seconds
- Parallel execution with retrieve_context

### Caching
- Token caching: Until expiry
- No result caching (always fresh data)
- Can add result caching in future if needed

### Rate Limiting
- No explicit rate limiting (external service responsibility)
- Single request per tool invocation
- No batch operations

## Testing Strategy

### Unit Tests
- Mock API responses
- Test error handling
- Test response formatting
- Test token refresh logic

### Integration Tests
- Real API calls (with test credentials)
- End-to-end LLM decision making
- Combined retrieval + search results

### Manual Testing
- Test with various company names
- Test with Chinese and English keywords
- Test API unavailability scenarios
- Test token expiry and refresh
