# Document Processing Specification

## ADDED Requirements

### Requirement: Upload Document Embedding
The system SHALL provide an API endpoint that accepts uploaded files, extracts text, splits it into chunks, and stores embeddings in the existing PGVector-backed tables.

#### Scenario: Embed uploaded document to default collection
- **WHEN** user calls `POST /documents/embed` without providing `collection_name`
- **THEN** system uses the configured default collection
- **AND** system stores embedded chunks in PGVector
- **AND** response includes `chunks_created` and the effective `collection_name`

#### Scenario: Embed uploaded document to specified collection
- **WHEN** user calls `POST /documents/embed` providing `collection_name`
- **THEN** system stores embedded chunks into that collection
- **AND** response includes the effective `collection_name`

#### Scenario: Extract text with minimal processing
- **WHEN** the uploaded file is supported by a lightweight loader/converter
- **THEN** system extracts text without running MinerU image processing
- **AND** system avoids redundant transformations not required for embedding

#### Scenario: Supported formats whitelist
- **WHEN** user uploads a file
- **THEN** system only accepts: `pdf`, `txt`, `md`, `docx`, `pptx`, `xlsx`, `xls`
- **AND** any other format returns an error

#### Scenario: Max 4 files per request
- **WHEN** user uploads more than 4 files in a single request
- **THEN** system returns a 400 error

#### Scenario: Unsupported format
- **WHEN** user uploads a file with an unsupported format
- **THEN** system returns a 400 error describing supported formats

#### Scenario: Idempotent embedding skip
- **WHEN** user uploads a file that has already been embedded to the target collection
- **THEN** system skips embedding for that file
- **AND** returns a per-file result indicating the file was skipped

### Requirement: Chunking Consistency
The system SHALL chunk extracted text using configured `chunk_size` and `chunk_overlap` to remain consistent with retrieval settings.

#### Scenario: Chunk with configured settings
- **WHEN** splitting extracted text
- **THEN** system uses `chunk_size` and `chunk_overlap` from configuration
- **AND** each stored chunk includes metadata identifying the source file

## MODIFIED Requirements

### Requirement: Vector Store Integration
The system SHALL support adding processed documents to the vector store via a lightweight upload pipeline in addition to MinerU processing.

#### Scenario: Add uploaded chunks to vector store
- **WHEN** upload embedding is performed
- **THEN** system calls `get_vector_store(collection_name).add_documents(...)`
- **AND** embeddings are persisted in the existing PGVector schema
