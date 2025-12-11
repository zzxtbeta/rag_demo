# Constraints: Document Upload with MarkItDown

## Technical Constraints

### File Handling
- **Max files**: 2 per request (enforced on both frontend and backend)
- **Max file size**: 50MB per file
- **Max total size**: 100MB per request
- **Conversion timeout**: 60 seconds per file
- **Supported formats**: Only listed formats (PDF, DOCX, PPTX, XLSX, Images, Audio, HTML, Text, ZIP, YouTube, EPUB)
- **Temp file cleanup**: Must delete temp files after conversion

### MarkItDown Integration
- **Installation**: Must use `markitdown[all]` for full format support
- **Python version**: Requires Python 3.10+
- **Dependencies**: All optional dependencies included (pdf, docx, pptx, xlsx, audio, youtube, etc.)
- **Plugins**: Disabled by default (enable_plugins=False)
- **No Azure Document Intelligence**: Not required for MVP

### API Design
- **Endpoint naming**: `/documents/process-markitdown` (clear, descriptive)
- **HTTP method**: POST (file upload)
- **Content-Type**: multipart/form-data
- **Response format**: JSON with DocumentUploadResponse schema
- **Error responses**: Standard HTTP status codes (400, 413, 422, 504)

### Chat Integration
- **Parameter name**: `documents` (optional, array of strings)
- **Document wrapping**: Use `<document index="i">` tags for clarity
- **Message combination**: Append documents after user message
- **No LangGraph changes**: Workflow remains unchanged
- **Backward compatible**: Documents parameter is optional

## Operational Constraints

### Configuration
- **Environment-based**: No hardcoded paths or limits
- **Timeout settings**: Configurable per environment
- **Logging**: All conversions logged with timing and status
- **Error tracking**: Failed conversions logged with details

### Performance
- **Conversion time**: Acceptable up to 60s per file
- **Total request time**: <30s for typical 2-file upload (with conversion)
- **Parallel processing**: Convert multiple files concurrently
- **Memory usage**: Stream large files, don't load entirely into memory
- **No blocking**: All operations async

### Reliability
- **Graceful degradation**: If conversion fails, return error, don't crash
- **Retry logic**: No automatic retries (user can re-upload)
- **Timeout handling**: Return 504 on timeout, don't hang
- **Error messages**: User-friendly, not technical jargon

## Security Constraints

### File Validation
- **MIME type checking**: Validate file type matches extension
- **Format whitelist**: Only accept listed formats
- **Size limits**: Enforce max file size before processing
- **Filename sanitization**: Remove path traversal attempts
- **No code execution**: MarkItDown only converts, doesn't execute

### Data Handling
- **Temp file security**: Use secure temp directory, delete after use
- **No persistence**: Don't store uploaded files permanently
- **No logging of content**: Don't log file content, only metadata
- **User isolation**: Documents only used for current request

### API Security
- **Authentication**: Inherit from parent API (if any)
- **Rate limiting**: Respect API rate limits
- **Input validation**: Validate all parameters
- **Error messages**: Don't expose internal paths or errors

## Code Quality Constraints

### Style & Structure
- **Naming**: Clear, descriptive names (process-markitdown, not convert-doc)
- **Type hints**: All functions must have complete type annotations
- **Docstrings**: All public functions must have docstrings
- **Comments**: Complex logic must be commented
- **No duplication**: Reuse existing patterns from codebase

### Testing
- **Unit test coverage**: Minimum 80% for conversion logic
- **Integration tests**: Test upload endpoint with real files
- **Error scenarios**: Test all error paths
- **Format coverage**: Test each supported format

### Documentation
- **API docs**: Clear endpoint description with examples
- **Supported formats**: List all formats with examples
- **Error codes**: Document all possible error responses
- **Usage guide**: Show how to use from frontend

## Compatibility Constraints

### Backward Compatibility
- **No breaking changes**: Existing chat API unchanged
- **Optional parameter**: Documents parameter is optional
- **Fallback behavior**: Chat works without documents
- **No schema changes**: Existing models not modified

### Version Compatibility
- **Python**: Must support Python 3.10+
- **FastAPI**: Compatible with current version
- **LangChain**: No changes to LangChain integration
- **Frontend**: No breaking changes to chat component

## Scope Constraints

### In Scope
- ✅ File upload endpoint with MarkItDown conversion
- ✅ Support for listed file formats
- ✅ Max 2 files per request
- ✅ Document wrapping and passing to chat
- ✅ Prompt enhancement for document handling
- ✅ Frontend upload UI with progress indicators
- ✅ Error handling and validation

### Out of Scope
- ❌ Document storage/persistence
- ❌ Document history or management
- ❌ Advanced document processing (OCR beyond MarkItDown)
- ❌ Document search/indexing
- ❌ Document sharing or collaboration
- ❌ Azure Document Intelligence
- ❌ Custom MarkItDown plugins
- ❌ Batch processing multiple requests

## Deployment Constraints

### Environment Setup
- **Virtual environment**: Must install in eigenflow venv
- **Dependencies**: Run `pip install 'markitdown[all]'`
- **Configuration**: Add to pyproject.toml
- **No system packages**: All Python packages, no system dependencies

### Rollout Strategy
- **Feature flag**: Optional, can be enabled/disabled
- **Gradual rollout**: Can enable for subset of users
- **Monitoring**: Track upload success rate and conversion time
- **Rollback plan**: Can disable endpoint without redeployment

## Assumptions

1. **MarkItDown reliability**: Assumes MarkItDown handles all formats correctly
2. **File availability**: Assumes uploaded files are immediately available
3. **Network stability**: Assumes stable connection for file upload
4. **LLM capability**: Assumes LLM can handle markdown content well
5. **User behavior**: Assumes users won't abuse upload with many large files
6. **Frontend framework**: Assumes React/TypeScript frontend

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Conversion timeout | Medium | Medium | Set 60s timeout, return 504 |
| Large file upload | Low | Medium | Enforce 50MB limit per file |
| Unsupported format | Low | Low | Validate format before conversion |
| Memory exhaustion | Low | High | Stream files, use temp storage |
| Malformed markdown | Low | Low | Validate output, handle gracefully |
| LLM context overflow | Medium | Medium | Limit document size, truncate if needed |
| UI progress not showing | Low | Low | Test UI thoroughly before deploy |
| Concurrent uploads | Low | Medium | Queue uploads, process sequentially |

## Success Metrics

- Upload success rate: >95%
- Average conversion time: <10s per file
- Error rate: <1%
- UI responsiveness: Progress indicators update within 1s
- LLM response quality: Improved for document-based questions
- No impact on existing chat functionality
- User satisfaction: Positive feedback on upload feature

## Future Enhancements

- Document preview before upload
- Document history/management
- Batch processing
- Custom conversion options
- Document search/indexing
- Integration with vector store
- Document comparison
- Export converted markdown
