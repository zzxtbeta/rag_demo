# Implementation Tasks: Add Knowledge Base Page

## 1. UX & Navigation

- [ ] 1.1 Add "Knowledge Base" entry to Sidebar
- [ ] 1.2 Add view switching in `App.tsx` (no router dependency)
- [ ] 1.3 Ensure switching views does not reset chat threads/messages

## 2. Embed Upload Tab

- [ ] 2.1 Create upload UI (drag/drop + file picker), max 4 files
- [ ] 2.2 Add collection name input (default to backend default if empty)
- [ ] 2.3 Implement request to `POST /agent/documents/embed` (multipart)
- [ ] 2.4 Render response table (per-file status + chunks)

## 3. MinerU Import Tab

- [ ] 3.1 Create form inputs: `source_path`, `embed` toggle, `collection_name`
- [ ] 3.2 Implement request to `POST /agent/documents/process-mineru`
- [ ] 3.3 Render response summary (images_copied, chunks_created, embedded)

## 4. Polish

- [ ] 4.1 Reuse existing document list UI where possible
- [ ] 4.2 Add basic error handling and inline validation
- [ ] 4.3 Manual test end-to-end against local backend
