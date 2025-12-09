# Implementation Tasks: Add MinerU Document Processor

## 1. Backend Implementation

- [x] 1.1 Create `MineruProcessor` class in `src/utils/mineru_processor.py`
- [x] 1.2 Implement image copying from MinerU output to frontend directory
- [x] 1.3 Implement Markdown image path updating (local → frontend-accessible)
- [x] 1.4 Implement content splitting using `RecursiveCharacterTextSplitter`
- [x] 1.5 Implement optional vector embedding to PGVector
- [x] 1.6 Create Pydantic schemas (`ProcessingRequest`, `ProcessingResponse`)

## 2. API Integration

- [x] 2.1 Create `POST /documents/process-mineru` endpoint in `src/api/routes/documents.py`
- [x] 2.2 Integrate endpoint into FastAPI app
- [x] 2.3 Add error handling and validation
- [x] 2.4 Test endpoint with actual MinerU output

## 3. Configuration

- [x] 3.1 Add `FRONTEND_IMAGES_DIR` environment variable
- [x] 3.2 Add `FRONTEND_IMAGE_PREFIX` environment variable
- [x] 3.3 Update `src/config/settings.py` to load new variables
- [x] 3.4 Update `.env.example` with new configuration
- [x] 3.5 Fix path resolution (use project root, not script directory)

## 4. LLM Prompt Enhancement

- [x] 4.1 Update `GENERATE_ANSWER_PROMPT` to guide image rendering
- [x] 4.2 Add explicit instructions for Markdown image syntax
- [x] 4.3 Prevent LLM from describing images as "unable to display"

## 5. Frontend Enhancement

- [x] 5.1 Install `react-markdown` and `remark-gfm` dependencies
- [x] 5.2 Update `TurnView.tsx` to use `ReactMarkdown` component
- [x] 5.3 Add custom styling for images (responsive, rounded, spacing)
- [x] 5.4 Add styling for other Markdown elements (headings, lists, tables, code)
- [x] 5.5 Test image rendering in chat interface

## 6. Documentation

- [x] 6.1 Create `docs/DOCUMENT_PROCESSING.md` with comprehensive guide
- [x] 6.2 Document MinerU installation and usage
- [x] 6.3 Document API endpoint and parameters
- [x] 6.4 Document configuration options
- [x] 6.5 Add troubleshooting section (JSON escaping, path issues)
- [x] 6.6 Add FAQ section

## 7. Code Cleanup

- [x] 7.1 Mark PyPDF functions as DEPRECATED in `src/agent/vectorstore.py`
- [x] 7.2 Mark `scripts/init_vectorstore.py` as DEPRECATED
- [x] 7.3 Update `pyproject.toml` to remove `document_processing` package
- [x] 7.4 Move startup script to project root for correct path resolution

## 8. Testing & Verification

- [x] 8.1 Test image copying with actual MinerU output
- [x] 8.2 Test image path updating in Markdown
- [x] 8.3 Test document chunking
- [x] 8.4 Test optional embedding (embed=false and embed=true)
- [x] 8.5 Test frontend image rendering
- [x] 8.6 Test Markdown rendering (headings, lists, tables, code blocks)
- [x] 8.7 Verify no duplicate embedding on repeated API calls
