# Change: Add MinerU Document Processor for PDF Parsing and Embedding

## Why

The existing PyPDF-based document processing is limited:
- Cannot preserve document structure (titles, tables, images)
- No support for multimodal content (text + images)
- Lower accuracy due to rule-based parsing

MinerU provides high-precision document parsing with Markdown output and image extraction, enabling better semantic understanding and richer content representation in the RAG system.

## What Changes

- **New capability**: MinerU document processor with image handling and path management
- **New API endpoint**: `POST /documents/process-mineru` for processing MinerU outputs
- **Configuration**: Environment variables for frontend image directories and paths
- **Frontend enhancement**: Markdown rendering with image support in chat messages
- **Documentation**: Comprehensive guide for MinerU workflow

## Impact

- **Affected specs**: 
  - `document-processing` (new)
  - `chat-interface` (modified - now supports image rendering)
- **Affected code**: 
  - `src/utils/mineru_processor.py` (new)
  - `src/api/routes/documents.py` (new)
  - `frontend/src/components/TurnView.tsx` (modified)
  - `src/agent/prompts.py` (modified)
  - `src/config/settings.py` (modified)
- **Breaking changes**: None
- **Dependencies added**: `react-markdown`, `remark-gfm` (frontend)
