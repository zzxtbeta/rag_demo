# Change: Add Retrieval Tool Toggle

## Why

The agent's vector retrieval tool (`retrieve_context`) should be controllable like web search:

- Operators need to disable retrieval globally via environment variable (e.g. during incidents, cost control, or when vector DB is unavailable).
- Callers need to enable/disable retrieval per request (e.g. some chats should be "no-RAG").

## What Changes

- **New env flag**: `RETRIEVAL_ENABLED` controls whether the retrieval tool is available at runtime.
- **New request flag**: `enable_retrieval` on `ChatRequest` controls whether a specific request exposes retrieval tools to the model.
- **Tool registry update**: `retrieve_context` becomes part of the tool registry again, gated by the above flags.

## Impact

- **Affected code**:
  - `src/config/settings.py` (+ `retrieval_enabled`)
  - `.env.example` (+ `RETRIEVAL_ENABLED`)
  - `src/api/schemas.py` (+ `enable_retrieval`)
  - `src/api/routes/chat.py` (propagate to graph config)
  - `src/agent/graph.py` (bind tools based on config)
  - `src/tools/toolkit.py` (register tool under flag)

- **Breaking changes**: None (default behavior controlled via env; request flag is optional)

## Success Criteria

- [ ] When `RETRIEVAL_ENABLED=false`, retrieval is never exposed and cannot be invoked.
- [ ] When `RETRIEVAL_ENABLED=true` and request omits `enable_retrieval`, retrieval is enabled by default.
- [ ] When `RETRIEVAL_ENABLED=true` and request sets `enable_retrieval=false`, retrieval is disabled for that request.
- [ ] When retrieval is disabled, the agent does not call `retrieve_context`.
