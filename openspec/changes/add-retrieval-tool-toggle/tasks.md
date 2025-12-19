# Implementation Tasks: Add Retrieval Tool Toggle

## 1. Configuration

- [ ] 1.1 Add `RETRIEVAL_ENABLED` to `.env.example`
- [ ] 1.2 Add `retrieval_enabled` to `Settings` and load from env

## 2. API Surface

- [ ] 2.1 Add `enable_retrieval: Optional[bool]` to `ChatRequest`
- [ ] 2.2 Propagate effective `enable_retrieval` to LangGraph config

## 3. Tool Registry

- [ ] 3.1 Re-enable `retrieve_context` in `tools/toolkit.py`
- [ ] 3.2 Gate model tool exposure with `RETRIEVAL_ENABLED` + request-level `enable_retrieval`
- [ ] 3.3 Ensure ToolNode tool list remains a safe superset

## 4. Verification

- [ ] 4.1 Manual test with `RETRIEVAL_ENABLED=false`: agent never retrieves
- [ ] 4.2 Manual test with `RETRIEVAL_ENABLED=true` + `enable_retrieval=false`: request disables retrieval
- [ ] 4.3 Manual test with `RETRIEVAL_ENABLED=true`: retrieval available by default
