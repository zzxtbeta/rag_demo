# Document Upload with MarkItDown Conversion

## Overview

This change adds document upload capability to the chat interface, allowing users to upload files (PDF, DOCX, PPTX, XLSX, Images, Audio, HTML, etc.) and have them converted to Markdown for use in chat conversations.

## Key Features

- **Multi-format support**: PDF, PowerPoint, Word, Excel, Images (with OCR), Audio (with transcription), HTML, Text formats, ZIP, YouTube URLs, EPub
- **Real-time conversion**: MarkItDown converts files to Markdown on-the-fly
- **Progressive UI feedback**: Loading spinner → checkmark for each file
- **Max 2 files**: Enforced on both frontend and backend
- **Seamless integration**: Documents passed to chat stream endpoint
- **LLM-aware**: System prompt enhanced to use uploaded documents

## Architecture

### Backend Flow
```
Upload Files
    ↓
POST /documents/process-markitdown
    ├─ Validate (format, size, count)
    ├─ Convert to Markdown (async, parallel)
    └─ Return markdown content
    ↓
Frontend receives markdown
    ↓
User sends message with documents
    ↓
POST /chat/stream (with documents parameter)
    ├─ Wrap documents in tags
    ├─ Combine with user message
    └─ Pass to LangGraph
    ↓
LLM processes documents + query
```

### Frontend Flow
```
Drag-drop or click upload
    ↓
Show loading spinner for each file
    ↓
Call POST /documents/process-markitdown
    ↓
Receive markdown content
    ↓
Show checkmark for each file
    ↓
User types message
    ↓
Send message with documents array
    ↓
Chat stream processes with documents
```

## Files Changed

### Backend
- `src/api/routes/documents.py` - New endpoint `/documents/process-markitdown`
- `src/api/routes/chat.py` - Enhanced `/chat/stream` with documents parameter
- `src/agent/prompts.py` - Updated system prompt for document handling
- `src/utils/markitdown_converter.py` - New MarkItDown wrapper (to be created)
- `pyproject.toml` - Add `markitdown[all]` dependency

### Frontend
- `frontend/src/components/DocumentUpload.tsx` - New upload UI component
- `frontend/src/components/ChatInput.tsx` - Integrate upload component
- `frontend/src/hooks/useDocumentUpload.ts` - Upload logic hook
- `frontend/src/styles.css` - Styles for upload UI

## Configuration

### Environment
```bash
# Install in eigenflow virtual environment
pip install 'markitdown[all]'
```

### Limits
- Max files: 2
- Max file size: 50MB per file
- Max total size: 100MB
- Conversion timeout: 60 seconds per file

### Supported Formats
```
PDF, PPTX, DOCX, XLSX, XLS
JPG, PNG, GIF, WEBP (with OCR)
MP3, WAV (with transcription)
HTML, CSV, JSON, XML, TXT
ZIP, EPUB
YouTube URLs
```

## API Endpoints

### POST /documents/process-markitdown

Convert uploaded files to Markdown.

**Request**: multipart/form-data with files

**Response**:
```json
{
  "documents": [
    {
      "filename": "document.pdf",
      "format": "pdf",
      "markdown_content": "...",
      "size_bytes": 1024,
      "conversion_time_ms": 2500,
      "error": null
    }
  ],
  "total_time_ms": 2500
}
```

### POST /chat/stream (Enhanced)

**New parameter**:
```json
{
  "thread_id": "...",
  "message": "...",
  "documents": ["markdown1", "markdown2"]  // Optional
}
```

## Prompt Changes

System prompt now includes:
- Recognition of uploaded documents in `<uploaded_documents>` section
- Instructions to prioritize document content
- Citation guidance for document references

## Testing

### Backend Tests
- File validation (format, size, count)
- MarkItDown conversion for each format
- Error handling (timeout, invalid format)
- Document wrapping format

### Frontend Tests
- Upload UI interaction
- Progress indicator updates
- Max 2 files constraint
- Error message display

### Integration Tests
- End-to-end upload → conversion → chat
- LLM receives and uses document content
- Multiple file handling

## Rollout Plan

1. Install MarkItDown in eigenflow environment
2. Implement backend endpoint
3. Enhance chat stream endpoint
4. Update system prompt
5. Implement frontend upload UI
6. Integration testing
7. Deploy with feature flag (optional)

## Success Criteria

- ✅ All supported formats convert correctly
- ✅ Frontend shows loading/success indicators
- ✅ Documents passed to chat stream
- ✅ LLM receives and uses document content
- ✅ Max 2 files enforced
- ✅ Error handling works for all scenarios
- ✅ Response time acceptable (<30s for 2 documents)
- ✅ No breaking changes to existing functionality
- ✅ Document tags display in chat history
- ✅ Document content viewable in modal
- ✅ Document metadata extractable from message content
- ✅ Both real-time and history messages support document display

## References

- MarkItDown: https://github.com/microsoft/markitdown
- LangGraph: https://docs.langchain.com/oss/python/langgraph
- FastAPI: https://fastapi.tiangolo.com/
