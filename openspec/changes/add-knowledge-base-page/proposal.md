# Change: Add Knowledge Base Page

## Why

Users need a dedicated place to manage knowledge base ingestion without mixing it into chat threads. Today, document ingestion exists in the backend (`/documents/embed` and `/documents/process-mineru`) but there is no standalone UI for:

- Selecting a target vector collection
- Uploading documents for embedding (fast path)
- Importing MinerU outputs for higher-quality parsing
- Seeing per-file results (embedded/skipped/errors)

## What Changes

### Frontend

- **New page/view**: "Knowledge Base" view, separate from Chat and accessible via a new Sidebar entry.
- **Two ingestion modes** (tabs):
  - **Embed Upload**: Upload up to 4 files and call `POST /agent/documents/embed`.
  - **MinerU Import**: Provide `source_path` and call `POST /agent/documents/process-mineru`.
- **No route conflicts**: View switching is isolated from chat state (threads/messages).

### Backend

- No changes required (reuses existing endpoints).

## Impact

- **Affected specs**:
  - `chat-interface` (modified: add UI navigation to Knowledge Base)
  - `document-processing` (modified: add UI for ingestion workflows)
- **Affected code**:
  - `frontend/src/App.tsx`
  - `frontend/src/components/Sidebar.tsx`
  - New/updated `frontend/src/pages/KnowledgeBase.tsx` (or equivalent)
  - Potentially new hooks for `/documents/embed` and `/documents/process-mineru`

## Success Criteria

- [ ] Sidebar has a Knowledge Base entry; switching does not disrupt chat threads.
- [ ] Embed Upload tab supports selecting collection name and uploading up to 4 files.
- [ ] Embed results display per-file status: embedded/skipped/error and chunks created.
- [ ] MinerU Import tab supports `source_path`, `embed` toggle, and optional `collection_name`.
- [ ] User can run ingestion without authentication (documents endpoints are public).
