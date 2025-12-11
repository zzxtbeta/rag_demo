# Change: Add Document Upload with MarkItDown Conversion

## Why

Users need to upload documents directly in the chat interface to ask questions about them. Current system only supports PDF knowledge base retrieval. By adding document upload capability with MarkItDown conversion, we enable:

- Direct document upload (drag-and-drop or click-to-upload)
- Multi-format support (PDF, PPTX, DOCX, XLSX, Images, Audio, HTML, etc.)
- Real-time conversion to Markdown
- Progressive UI feedback (loading → success indicator)
- Seamless integration with existing RAG workflow

## What Changes

### Backend
- **New API endpoint**: `POST /documents/process-markitdown` for converting uploaded files to Markdown
- **New dependency**: `markitdown[all]` for multi-format document conversion
- **Stream chat enhancement**: Add optional `documents` parameter to `POST /chat/stream`
- **Prompt enhancement**: Update system prompt to handle user-provided documents
- **Configuration**: Add markitdown-related settings

### Frontend
- **Document upload UI**: Drag-and-drop or click-to-upload interface
- **File validation**: Support only specified formats, max 2 files
- **Progress indicators**: Show loading spinner → checkmark for each file
- **Document preview**: Display uploaded files with status
- **Chat integration**: Pass converted markdown to chat stream endpoint

## Impact

- **Affected specs**:
  - `document-processing` (enhanced - now supports user uploads)
  - `chat-interface` (modified - new documents parameter)
  - `rag-system` (modified - can use user-provided documents)
- **Affected code**:
  - `src/api/routes/documents.py` (new endpoint)
  - `src/api/routes/chat.py` (modified stream endpoint)
  - `src/agent/prompts.py` (modified system prompt)
  - `pyproject.toml` (new dependency)
  - `frontend/src/components/ChatInput.tsx` (new upload UI)
  - `frontend/src/hooks/useDocumentUpload.ts` (new upload logic)
- **Breaking changes**: None (documents parameter is optional)
- **Dependencies added**: `markitdown[all]` (~50MB with all optional deps)

## Design Principles

1. **Progressive enhancement**: Documents are optional, chat works without them
2. **User-friendly feedback**: Real-time conversion progress with visual indicators
3. **Minimal coupling**: Upload and chat are separate concerns
4. **Format flexibility**: Support wide range of document types
5. **Performance**: Stream conversion results to frontend as they complete
6. **Safety**: Validate file types, limit to 2 files max, set reasonable timeouts

## Success Criteria

- [x] Document upload endpoint accepts and converts files correctly
- [x] Frontend shows loading/success indicators for each file
- [x] Converted markdown is passed to chat stream endpoint
- [x] LLM receives and uses document content in responses
- [x] All supported formats convert without errors
- [x] Max 2 files enforced on both frontend and backend
- [x] Response time acceptable (<30s for 2 typical documents)
- [x] No breaking changes to existing chat functionality
- [x] Document tags display in chat history
- [x] Document content viewable in modal
- [x] Document metadata extractable from message content
