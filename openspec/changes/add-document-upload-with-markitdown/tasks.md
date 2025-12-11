# Implementation Tasks: Add Document Upload with MarkItDown

## 1. Backend Setup

- [x] 1.1 Add `markitdown[all]` to `pyproject.toml` dependencies
- [x] 1.2 Install markitdown in eigenflow virtual environment
- [x] 1.3 Create `src/utils/markitdown_converter.py` with conversion logic
- [x] 1.4 Add MarkItDown initialization and caching

## 2. Document Upload Endpoint

- [x] 2.1 Create Pydantic models in `src/api/routes/documents.py`:
  - `DocumentConversionResult`
  - `DocumentMetadata`
- [x] 2.2 Implement `POST /documents/process-markitdown` endpoint
- [x] 2.3 Add file validation (format, size, count)
- [x] 2.4 Implement async file conversion with timeout
- [x] 2.5 Add error handling and logging
- [x] 2.6 Add API documentation with supported formats
- [x] 2.7 Test endpoint with various file types

## 3. Chat Stream Enhancement

- [x] 3.1 Update `ChatRequest` model to include optional `documents` parameter
- [x] 3.2 Modify `POST /chat/stream` endpoint to accept documents
- [x] 3.3 Implement document wrapping logic:
  - Wrap each document in `<document index="i" filename="x" format="y">` tags
  - Combine with user message
- [x] 3.4 Pass combined message to LangGraph
- [x] 3.5 Test chat with and without documents

## 4. Prompt Enhancement

- [x] 4.1 Update system prompt to handle uploaded documents
- [x] 4.2 Add uploaded documents instruction section
- [x] 4.3 Update tool usage rules to prioritize uploaded documents
- [x] 4.4 Test prompt with sample documents

## 5. Frontend Upload UI

- [x] 5.1 Create `frontend/src/components/DocumentUpload.tsx` component
- [x] 5.2 Implement drag-and-drop functionality
- [x] 5.3 Implement click-to-upload button
- [x] 5.4 Add file validation (format, size, count)
- [x] 5.5 Add visual indicators (loading spinner, checkmark, error)
- [x] 5.6 Add file preview with format icon
- [x] 5.7 Integrate into `ChatInputWithUpload` component

## 6. Frontend Upload Hook

- [x] 6.1 Create `frontend/src/hooks/useDocumentUpload.ts`
- [x] 6.2 Implement file upload logic
- [x] 6.3 Call `POST /documents/process-markitdown`
- [x] 6.4 Handle conversion results and errors
- [x] 6.5 Return markdown content for chat

## 7. Frontend Chat Integration

- [x] 7.1 Modify chat message sending to include documents
- [x] 7.2 Pass documents array to `POST /chat/stream`
- [x] 7.3 Clear documents after sending
- [x] 7.4 Test end-to-end flow

## 8. Frontend Document Display

- [x] 8.1 Display document tags in chat history
- [x] 8.2 Extract document metadata from message content
- [x] 8.3 Implement document content modal/preview
- [x] 8.4 Support both real-time and history messages
- [x] 8.5 Add document tag click handler

## 9. Testing

- [x] 9.1 Manual testing with various file types
- [x] 9.2 Manual testing of UI progress indicators
- [x] 9.3 End-to-end upload → conversion → chat flow
- [x] 9.4 Document display in chat history
- [x] 9.5 Document modal/preview functionality

## 10. Documentation

- [x] 10.1 Update design.md with actual implementation details
- [x] 10.2 Document enhanced document wrapping format
- [x] 10.3 Document frontend document extraction mechanism
- [x] 10.4 Add usage examples

## Acceptance Criteria

- [x] MarkItDown installed in eigenflow environment
- [x] Document upload endpoint works for all supported formats
- [x] Frontend shows loading/success indicators
- [x] Documents passed to chat stream endpoint
- [x] LLM receives and uses document content
- [x] Max 2 files enforced
- [x] All error cases handled gracefully
- [x] Response time acceptable (<30s for 2 documents)
- [x] No breaking changes to existing functionality
- [x] Document tags display in chat history
- [x] Document content viewable in modal
- [x] Document metadata extractable from message content
