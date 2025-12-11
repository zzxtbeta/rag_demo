# Design: Document Upload with MarkItDown Conversion

## Architecture Overview

```
Frontend Upload UI
    ↓
[POST /documents/process-markitdown]
    ├─ Validate file type & count (max 2)
    ├─ Convert each file to Markdown
    └─ Stream results back to frontend
    ↓
Frontend receives converted markdown
    ├─ Show success checkmark for each file
    └─ Store markdown content
    ↓
User sends message with documents
    ↓
[POST /chat/stream]
    ├─ Receive: message + documents array
    ├─ Combine: wrap documents + append to query
    └─ Pass to LangGraph
    ↓
LangGraph workflow
    ├─ query_or_respond: LLM sees full context (documents + query)
    ├─ tools: Execute retrieval/search as needed
    └─ generate: Answer based on all available context
    ↓
Stream response back to frontend
```

## Backend API Design

### 1. Document Upload Endpoint

**Endpoint**: `POST /documents/process-markitdown`

**Request**:
```python
class DocumentUploadRequest(BaseModel):
    """Upload and convert documents to Markdown."""
    pass  # Files sent as multipart/form-data

# Multipart form fields:
# - files: List[UploadFile] (max 2 files)
```

**Response**:
```python
class DocumentConversionResult(BaseModel):
    """Result of converting a single document."""
    filename: str
    format: str  # "pdf", "docx", "pptx", etc.
    markdown_content: str
    size_bytes: int
    conversion_time_ms: float
    error: Optional[str] = None

class DocumentUploadResponse(BaseModel):
    """Response containing converted documents."""
    documents: List[DocumentConversionResult]
    total_time_ms: float
```

**Supported Formats**:
```
✅ PDF
✅ PowerPoint (.pptx)
✅ Word (.docx)
✅ Excel (.xlsx, .xls)
✅ Images (.jpg, .png, .gif, .webp - with OCR)
✅ Audio (.mp3, .wav - with transcription)
✅ HTML (.html, .htm)
✅ Text-based (.csv, .json, .xml, .txt)
✅ ZIP files (iterates over contents)
✅ YouTube URLs
✅ EPub (.epub)
```

**Constraints**:
- Max 2 files per request
- Max 50MB per file
- Max 100MB total
- Timeout: 60 seconds per file
- Supported MIME types only

**Error Handling**:
- `400`: Invalid file type or too many files
- `413`: File too large
- `422`: Conversion failed
- `504`: Timeout

### 2. Stream Chat Enhancement

**Endpoint**: `POST /chat/stream` (modified)

**Request** (add new optional parameter):
```python
class DocumentMetadata(BaseModel):
    """Document metadata for chat."""
    filename: str
    format: str
    markdown_content: str

class ChatStreamRequest(BaseModel):
    thread_id: str
    user_id: Optional[str] = None
    message: str
    chat_model: Optional[str] = None
    documents: Optional[List[DocumentMetadata]] = None  # NEW: Array of document metadata
```

**Processing**:
```python
# Combine documents with query
if documents:
    doc_section = "\n\n<uploaded_documents>\n"
    for idx, doc in enumerate(documents):
        # Include metadata in markers for frontend extraction
        doc_section += f'<document index="{idx}" filename="{doc.filename}" format="{doc.format}">\n{doc.markdown_content}\n</document>\n'
    doc_section += "</uploaded_documents>"
    combined_message = message + doc_section
else:
    combined_message = message

# Pass to LangGraph
payload = {"messages": [{"role": "user", "content": combined_message}]}
```

**Document Wrapping Format** (Enhanced):
```
<uploaded_documents>
<document index="0" filename="example.pdf" format="pdf">
[First document markdown content]
</document>
<document index="1" filename="data.xlsx" format="xlsx">
[Second document markdown content]
</document>
</uploaded_documents>
```

**Advantages of Enhanced Format**:
- Frontend can extract document metadata from message content
- No need for separate document storage in history
- Supports document preview/modal functionality
- Enables document tag display in chat history

## Frontend Implementation

### 1. Upload Component

**Features**:
- Drag-and-drop zone
- Click-to-upload button
- File preview with format icon
- Progress indicator (spinner → checkmark)
- Error message display
- Max 2 files validation

**UI States**:
```
[Empty] → [Dragging] → [Uploading] → [Success] → [Ready to send]
```

**File Status Indicator**:
- 🔄 Loading (spinner, semi-transparent)
- ✅ Success (checkmark, semi-transparent)
- ❌ Error (red X, semi-transparent)

### 2. Upload Hook

**Interface**:
```typescript
interface UploadedDocument {
  filename: string
  format: string
  markdown_content: string
  status: 'loading' | 'success' | 'error'
  error?: string
}

function useDocumentUpload() {
  const [documents, setDocuments] = useState<UploadedDocument[]>([])
  const [isUploading, setIsUploading] = useState(false)
  
  const uploadFiles = async (files: File[]) => {
    // Validate: max 2 files, correct format
    // Call POST /documents/process-markitdown
    // Update state with results
    // Return markdown content
  }
  
  return { documents, isUploading, uploadFiles }
}
```

### 3. Chat Integration

**Flow**:
1. User uploads files → shows progress indicators
2. Files convert → show checkmarks
3. User types message
4. User sends message with documents
5. Frontend passes `DocumentMetadata[]` to `/chat/stream`
6. Backend combines documents with message using enhanced format
7. LLM receives full context
8. Chat history displays document tags (clickable)
9. User can click tags to view full document content in modal

**Document Display in Chat History**:
- User messages show only typed text + document tags
- Document tags display filename with 📎 icon
- Clicking tag opens modal with full Markdown content
- Frontend extracts metadata from message content using regex
- No separate document storage needed in history

## Prompt Enhancement

### System Prompt Update

Add to `SYSTEM_PROMPT`:

```python
UPLOADED_DOCUMENTS_INSTRUCTION = """
When the user provides uploaded documents in the <uploaded_documents> section:
1. Read and understand the document content
2. Use the document content to answer the user's question
3. Cite specific sections or pages when referencing document content
4. If the question is about the document, prioritize document content over general knowledge
5. If the document doesn't contain relevant information, say so explicitly

Document format:
<uploaded_documents>
<document index="0">
[Markdown content of first document]
</document>
<document index="1">
[Markdown content of second document]
</document>
</uploaded_documents>
"""
```

### Updated SYSTEM_PROMPT

```python
SYSTEM_PROMPT = """You are a helpful AI assistant with access to:
1. PDF document knowledge base (via retrieve_context tool)
2. Project database (via search_projects tool)
3. User-uploaded documents (provided directly in the message)

CRITICAL RULES:
- When user provides uploaded documents, use them as primary source
- For company/project questions, use search_projects + retrieve_context
- Combine all available sources for comprehensive answers
- Always cite sources when using document content

{uploaded_documents_instruction}

Available tools:
- search_projects(query): Search project database
- retrieve_context(query): Search PDF knowledge base

Current time: {time}"""
```

## MarkItDown Integration

### Installation

```bash
# In eigenflow virtual environment
pip install 'markitdown[all]'
```

### Python API Usage

```python
from markitdown import MarkItDown
import io

# Initialize converter
md = MarkItDown(enable_plugins=False)

# Convert uploaded file
async def convert_file(file_path: str) -> str:
    """Convert file to markdown."""
    try:
        result = md.convert(file_path)
        return result.text_content
    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}")
        raise

# For file objects (from FastAPI UploadFile)
async def convert_upload_file(upload_file: UploadFile) -> str:
    """Convert uploaded file to markdown."""
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=upload_file.filename) as tmp:
        content = await upload_file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        result = md.convert(tmp_path)
        return result.text_content
    finally:
        os.unlink(tmp_path)
```

## Error Handling Strategy

### File Validation
```python
SUPPORTED_FORMATS = {
    'pdf': 'application/pdf',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'jpg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'mp3': 'audio/mpeg',
    'wav': 'audio/wav',
    'html': 'text/html',
    'csv': 'text/csv',
    'json': 'application/json',
    'xml': 'application/xml',
    'txt': 'text/plain',
    'epub': 'application/epub+zip',
}

MAX_FILES = 2
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB
CONVERSION_TIMEOUT = 60  # seconds
```

### Conversion Errors
- Invalid format → Return 400 with message
- File too large → Return 413
- Conversion timeout → Return 504
- Conversion failed → Return 422 with error details

## Performance Considerations

### Conversion Time
- PDF (10 pages): ~2-5s
- DOCX (10 pages): ~1-3s
- PPTX (10 slides): ~2-4s
- Images (OCR): ~3-10s per image
- Audio (transcription): ~1-2x audio length

### Optimization
- Parallel conversion for multiple files
- Stream results to frontend as they complete
- Cache converted content in session (optional)
- Set reasonable timeouts to prevent hanging

## Testing Strategy

### Unit Tests
- File validation (format, size, count)
- MarkItDown conversion for each format
- Error handling for invalid files
- Document wrapping format

### Integration Tests
- End-to-end upload → conversion → chat
- Multiple file handling
- Error scenarios (timeout, invalid format)
- LLM receives and uses document content

### Manual Testing
- Upload various file types
- Verify UI progress indicators
- Test max 2 files constraint
- Test chat with documents
- Verify LLM response quality
