# Tasks: Fix Frontend Persistence & Split Brain

## Backend

- [x] **Update Schema**: Modify `src/api/schemas.py` `HistoryMessage` to include `id`, `type`, `tool_calls`, `tool_call_id`, `name`.
- [x] **Enhance History API**: Update `src/api/routes/chat.py` `get_thread_history` to:
    - [x] Return all message types (including `tool`).
    - [x] Generate stable, deterministic IDs if missing.
    - [x] Populate new schema fields.

## Frontend

- [x] **Refactor `useChatStream`**:
    - [x] Remove LocalStorage message merging and deduplication logic.
    - [x] Implement `loadThreadHistory` to fetch directly from API.
- [x] **Implement Timeline Synthesis**:
    - [x] Create logic to iterate backend messages.
    - [x] Synthesize `NodeStart` and `NodeOutput` events for `assistant` messages.
    - [x] Synthesize `NodeStart` and `NodeOutput` events for `tool` messages.
    - [x] Ensure correct timestamp sorting for the synthesized timeline.
