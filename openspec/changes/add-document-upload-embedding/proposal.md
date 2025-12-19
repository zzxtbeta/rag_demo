# Change: Add Document Upload Embedding Endpoint

## Why

MinerU parsing yields high-quality chunks but is slow and resource-intensive. We need a lightweight indexing path that can embed user-uploaded documents into the existing PGVector store so they become retrievable via `retrieve_context`.

## What Changes

- **New API endpoint**: `POST /documents/embed` accepts uploaded file(s), parses them via existing lightweight loaders/converters, chunks text, and writes to PGVector.
- **Vector store reuse**: Uses existing `agent.vectorstore.get_vector_store(collection_name).add_documents(...)` so data lands in `langchain_pg_collection` / `langchain_pg_embedding` without custom SQL.
- **No redundant processing**: No MinerU image pipeline; focuses on text extraction + chunking + embedding.
 - **Supported formats (initial whitelist)**: `pdf`, `txt`, `md`, `docx`, `pptx`, `xlsx`, `xls`.
 - **Request limits**: Up to 4 files per request.
 - **Idempotency / dedup**: If a file has already been embedded to the target collection (by content hash), the system skips embedding and returns a "skipped" result.
 - **Parsing strategy**:
   - Prefer LangChain loaders where available (e.g. PDF)
   - Fallback to MarkItDown for office documents

## Impact

- **Affected specs**:
  - `document-processing` (modified / extended)
- **Affected code**:
  - `src/api/routes/documents.py` (add endpoint)
  - (optional) `src/utils/...` for loader/dispatch if needed
- **Breaking changes**: None

## Success Criteria

- [ ] Uploading a supported file and specifying `collection_name` results in new rows in PGVector-backed tables.
- [ ] Newly embedded content is retrievable via `retrieve_context`.
- [ ] Endpoint returns the number of chunks embedded and the effective collection name.
- [ ] No MinerU processing is required for this path.
 - [ ] Uploading more than 4 files returns a 400 error.
 - [ ] Re-uploading the same file content to the same collection does not create duplicate embeddings.
