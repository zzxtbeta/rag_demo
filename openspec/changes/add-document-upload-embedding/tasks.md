# Implementation Tasks: Add Document Upload Embedding Endpoint

## 1. Backend API

- [ ] 1.1 Add Pydantic request/response models for upload-embedding
- [ ] 1.2 Implement `POST /documents/embed` (multipart upload)
- [ ] 1.3 Implement loader/convert strategy:
  - Prefer LangChain loaders where available
  - Fallback to existing MarkItDown conversion where appropriate
- [ ] 1.4 Chunk with existing settings (`chunk_size`, `chunk_overlap`)
- [ ] 1.5 Call `get_vector_store(collection_name).add_documents(chunks)`
- [ ] 1.6 Return `chunks_created`, `embedded=true`, `collection_name`
 - [ ] 1.7 Implement idempotent dedup by file content hash (skip if already embedded to the same collection)

## 2. Validation & Limits

- [ ] 2.1 Enforce max 4 files per request
- [ ] 2.2 Enforce supported format whitelist: pdf/txt/md/docx/pptx/xlsx/xls
- [ ] 2.3 Reuse existing file size validation where possible
- [ ] 2.2 Error handling (unsupported format, conversion failure, embedding failure)

## 3. Verification

- [ ] 3.1 Manual test: upload a small PDF/TXT and embed into a new collection
- [ ] 3.2 Manual test: query via `/chat` or `retrieve_context` confirms retrieval
