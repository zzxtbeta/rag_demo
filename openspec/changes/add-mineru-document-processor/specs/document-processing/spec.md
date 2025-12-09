# Document Processing Specification

## ADDED Requirements

### Requirement: MinerU Document Processing
The system SHALL process MinerU-parsed PDF outputs (Markdown + images) and integrate them into the RAG system through a dedicated API endpoint.

#### Scenario: Process document without embedding
- **WHEN** user calls `POST /documents/process-mineru` with `embed=false`
- **THEN** system copies images to frontend directory, updates image paths in Markdown, and splits content into chunks
- **AND** returns processing metadata (images_copied, chunks_created) without storing in vector database

#### Scenario: Process document with embedding
- **WHEN** user calls `POST /documents/process-mineru` with `embed=true`
- **THEN** system performs all processing steps AND embeds document chunks to specified vector collection
- **AND** returns processing metadata including collection_name

#### Scenario: Handle missing images directory
- **WHEN** MinerU output lacks `auto/images/` subdirectory
- **THEN** system logs warning and continues processing
- **AND** returns images_copied=0

### Requirement: Image Path Management
The system SHALL automatically copy images from MinerU output and update Markdown references to frontend-accessible paths.

#### Scenario: Copy images to frontend
- **WHEN** processing MinerU output with images
- **THEN** all images are copied from `source_path/auto/images/` to `FRONTEND_IMAGES_DIR`
- **AND** no duplicate images are created on repeated processing

#### Scenario: Update image URLs in Markdown
- **WHEN** Markdown contains local image references `![](images/xxx.jpg)`
- **THEN** system updates them to `![](/documents/images/xxx.jpg)` (or configured prefix)
- **AND** updated Markdown is used for chunking and embedding

### Requirement: Document Chunking
The system SHALL split MinerU Markdown content into semantic chunks using Markdown structure as primary separator.

#### Scenario: Split by Markdown hierarchy
- **WHEN** splitting content with multiple heading levels
- **THEN** system prioritizes splitting at `# `, `## `, `### ` boundaries
- **AND** falls back to paragraph (`\n\n`), line (`\n`), word (` `), and character (``) separators
- **AND** respects configured chunk_size (default 1000) and chunk_overlap (default 200)

#### Scenario: Preserve image references in chunks
- **WHEN** splitting content containing updated image URLs
- **THEN** image Markdown syntax is preserved in document chunks
- **AND** chunks are suitable for both embedding and frontend rendering

### Requirement: Configuration Management
The system SHALL support environment variables for flexible deployment and frontend integration.

#### Scenario: Configure image directories
- **WHEN** system starts
- **THEN** it reads `FRONTEND_IMAGES_DIR` and `FRONTEND_IMAGE_PREFIX` from environment
- **AND** uses defaults if not specified: `./frontend/public/documents/images` and `/documents/images`

#### Scenario: Handle relative paths
- **WHEN** relative paths are configured
- **THEN** system resolves them relative to project root (not script directory)
- **AND** works correctly regardless of startup directory

## MODIFIED Requirements

### Requirement: Vector Store Integration
The system SHALL support adding processed documents to vector store with optional embedding.

#### Scenario: Embed documents to vector store
- **WHEN** `embed=true` is specified
- **THEN** system embeds document chunks using OpenAI embeddings
- **AND** stores them in specified collection (or default collection)
- **AND** repeated calls append documents (not replace)

#### Scenario: Skip embedding for preview
- **WHEN** `embed=false` is specified
- **THEN** system processes documents without calling embedding API
- **AND** documents are not added to vector store
- **AND** user can review processing results before committing to embedding
