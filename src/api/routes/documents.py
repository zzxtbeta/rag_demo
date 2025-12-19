"""文档处理 API 端点."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.vectorstore import get_vector_store
from config.settings import get_settings
from db.database import DatabaseManager
from utils.markitdown_converter import convert_upload_file
from utils.mineru_processor import MineruProcessor, ProcessingRequest, ProcessingResponse
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# /documents/process-markitdown 常量
# =============================================================================
MAX_FILES = 2
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB
CONVERSION_TIMEOUT = 60  # 秒

# =============================================================================
# /documents/embed 常量
# =============================================================================
EMBED_MAX_FILES = 4
EMBED_MAX_FILE_SIZE = MAX_FILE_SIZE
EMBED_MAX_TOTAL_SIZE = 200 * 1024 * 1024  # 200MB

EMBED_SUPPORTED_FORMATS = {
    "pdf",
    "txt",
    "md",
    "docx",
    "pptx",
    "xlsx",
    "xls",
}

# =============================================================================
# /documents/process-markitdown 支持格式
# =============================================================================
SUPPORTED_FORMATS = {
    "pdf", "pptx", "docx", "xlsx", "xls",
    "jpg", "jpeg", "png", "gif", "webp",
    "mp3", "wav", "m4a",
    "html", "htm", "csv", "json", "xml", "txt",
    "zip", "epub",
}


# =============================================================================
# /documents/process-markitdown 响应模型
# =============================================================================
class DocumentConversionResult(BaseModel):
    """单个文档转换结果."""

    index: int
    filename: str
    format: str
    status: str  # "success" 或 "error"
    markdown_content: Optional[str] = None
    size_bytes: Optional[int] = None
    conversion_time_ms: Optional[float] = None
    error: Optional[str] = None


class DocumentMetadata(BaseModel):
    """文档元数据（用于聊天消息中的文件引用）."""

    filename: str
    format: str
    markdown_content: str  # 完整的 Markdown 内容


# =============================================================================
# /documents/embed 响应模型
# =============================================================================
class EmbedFileResult(BaseModel):
    """单个文件的嵌入结果."""

    index: int
    filename: str
    format: str
    status: str  # "embedded" | "skipped" | "error"
    file_hash: str
    chunks_created: int = 0
    message: Optional[str] = None
    error: Optional[str] = None


class EmbedDocumentsResponse(BaseModel):
    """文档嵌入响应."""

    status: str
    message: str
    collection_name: str
    total_chunks_embedded: int = 0
    results: list[EmbedFileResult]


# =============================================================================
# Shared helpers
# =============================================================================
def _get_file_format(filename: str) -> str:
    """从文件名提取文件格式."""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


# =============================================================================
# /documents/process-markitdown 校验
# =============================================================================
def _validate_files(files: list[UploadFile]) -> None:
    """验证上传的文件."""
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"最多允许 {MAX_FILES} 个文件，当前 {len(files)} 个",
        )

    total_size = 0
    for file in files:
        # 检查格式
        fmt = _get_file_format(file.filename)
        if fmt not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的格式: {fmt}。支持的格式: {', '.join(sorted(SUPPORTED_FORMATS))}",
            )

        # 检查文件大小（从 content-length 头估算）
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件 {file.filename} 超过 {MAX_FILE_SIZE // 1024 // 1024}MB 限制",
            )

        total_size += file.size or 0

    if total_size > MAX_TOTAL_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"总大小超过 {MAX_TOTAL_SIZE // 1024 // 1024}MB 限制",
        )


# =============================================================================
# /documents/embed 校验
# =============================================================================
def _validate_embed_files(files: list[UploadFile]) -> None:
    """验证用于嵌入的上传文件."""
    if len(files) > EMBED_MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"最多允许 {EMBED_MAX_FILES} 个文件，当前 {len(files)} 个",
        )

    total_size = 0
    for file in files:
        fmt = _get_file_format(file.filename)
        if fmt not in EMBED_SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"不支持的格式: {fmt}。仅支持: {', '.join(sorted(EMBED_SUPPORTED_FORMATS))}"
                ),
            )

        if file.size and file.size > EMBED_MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件 {file.filename} 超过 {EMBED_MAX_FILE_SIZE // 1024 // 1024}MB 限制",
            )

        total_size += file.size or 0

    if total_size > EMBED_MAX_TOTAL_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"总大小超过 {EMBED_MAX_TOTAL_SIZE // 1024 // 1024}MB 限制",
        )


# =============================================================================
# /documents/embed 去重 & 解析 & chunking helpers
# =============================================================================
def _sha256_hex(data: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(data)
    return digest.hexdigest()


_pgvector_dedup_sql: Optional[str] = None


async def _get_pgvector_dedup_sql() -> str:
    global _pgvector_dedup_sql
    if _pgvector_dedup_sql is not None:
        return _pgvector_dedup_sql

    pool = await DatabaseManager.get_pool()

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'langchain_pg_collection'"
            )
            collection_cols = {row[0] for row in (await cur.fetchall())}

            await cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'langchain_pg_embedding'"
            )
            embedding_cols = {row[0] for row in (await cur.fetchall())}

    if "name" not in collection_cols:
        raise RuntimeError("langchain_pg_collection missing 'name' column")

    collection_pk = "uuid" if "uuid" in collection_cols else "id" if "id" in collection_cols else None
    if collection_pk is None:
        raise RuntimeError("langchain_pg_collection missing primary key column (uuid/id)")

    if "collection_id" not in embedding_cols:
        raise RuntimeError("langchain_pg_embedding missing 'collection_id' column")

    metadata_col = "cmetadata" if "cmetadata" in embedding_cols else "metadata" if "metadata" in embedding_cols else None
    if metadata_col is None:
        raise RuntimeError("langchain_pg_embedding missing metadata column (cmetadata/metadata)")

    _pgvector_dedup_sql = (
        "SELECT 1 "
        "FROM langchain_pg_embedding e "
        f"JOIN langchain_pg_collection c ON e.collection_id = c.{collection_pk} "
        f"WHERE c.name = %s AND e.{metadata_col} ->> 'file_hash' = %s "
        "LIMIT 1"
    )
    return _pgvector_dedup_sql


async def _is_file_already_embedded(collection_name: str, file_hash: str) -> bool:
    pool = await DatabaseManager.get_pool()
    sql = await _get_pgvector_dedup_sql()

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (collection_name, file_hash))
            row = await cur.fetchone()
            return row is not None


def _make_splitter(settings) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=[
            "\n# ",
            "\n## ",
            "\n### ",
            "\n\n",
            "\n",
            " ",
            "",
        ],
        add_start_index=True,
    )


def _enrich_chunk_metadata(
    chunks: list[Document],
    *,
    filename: str,
    fmt: str,
    file_hash: str,
) -> list[Document]:
    total = len(chunks)
    document_type = f"upload_{fmt}"
    for i, doc in enumerate(chunks):
        doc.metadata = {
            **(doc.metadata or {}),
            "source": filename,
            "filename": filename,
            "file_format": fmt,
            "file_hash": file_hash,
            "chunk_id": i,
            "total_chunks": total,
            "document_type": document_type,
        }
    return chunks


def _load_documents_from_bytes(file_bytes: bytes, filename: str, fmt: str) -> list[Document]:
    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / filename
        tmp_path.write_bytes(file_bytes)

        if fmt == "pdf":
            from langchain_community.document_loaders import PyPDFLoader

            return PyPDFLoader(str(tmp_path)).load()

        if fmt in {"txt", "md"}:
            from langchain_community.document_loaders import TextLoader

            return TextLoader(str(tmp_path), encoding="utf-8").load()

    raise ValueError(f"Unsupported loader format: {fmt}")


@router.post("/process-markitdown")
async def process_markitdown(files: list[UploadFile] = File(...)):
    """
    将上传的文档转换为 Markdown，支持实时流式返回.

    支持的格式：
    - **文档**: PDF, PPTX, DOCX, XLSX, XLS
    - **图片**: JPG, PNG, GIF, WEBP（含 OCR）
    - **音频**: MP3, WAV, M4A（含转录）
    - **网页**: HTML, CSV, JSON, XML, TXT
    - **压缩包**: ZIP, EPUB
    - **URL**: YouTube 链接

    约束条件：
    - 最多 2 个文件
    - 单文件最大 50MB
    - 总计最大 100MB
    - 超时时间: 60 秒/文件

    返回：
        Server-Sent Events 流，包含转换结果
    """
    # 验证文件
    _validate_files(files)

    # 在 StreamingResponse 之前一次性读完所有文件
    # 这是必要的，因为 FastAPI 会在响应开始后关闭 request body
    file_buffers = []
    for f in files:
        content = await f.read()
        file_buffers.append({
            "filename": f.filename,
            "content": content,
        })
        await f.close()

    async def generate():
        """流式返回转换结果（一个转化好立即返回）."""
        start_time = time.time()

        for idx, fb in enumerate(file_buffers):
            filename = fb["filename"]
            content = fb["content"]

            try:
                fmt = _get_file_format(filename)

                logger.info(f"[MARKITDOWN] 转换中 {filename} ({len(content)} 字节)")

                # 转换文件
                markdown, elapsed_ms = await convert_upload_file(content, filename, timeout=CONVERSION_TIMEOUT)

                # 发送成功结果
                result = DocumentConversionResult(
                    index=idx,
                    filename=filename,
                    format=fmt,
                    status="success",
                    markdown_content=markdown,
                    size_bytes=len(markdown),
                    conversion_time_ms=elapsed_ms,
                )

                yield f"data: {json.dumps(result.model_dump())}\n\n"

            except asyncio.TimeoutError:
                logger.error(f"[MARKITDOWN] 转换超时 {filename}")
                result = DocumentConversionResult(
                    index=idx,
                    filename=filename,
                    format=_get_file_format(filename),
                    status="error",
                    error="转换超时（>60秒）",
                )
                yield f"data: {json.dumps(result.model_dump())}\n\n"

            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                logger.error(f"[MARKITDOWN] 转换错误 {filename}: {error_msg}", exc_info=True)
                result = DocumentConversionResult(
                    index=idx,
                    filename=filename,
                    format=_get_file_format(filename),
                    status="error",
                    error=error_msg,
                )
                yield f"data: {json.dumps(result.model_dump())}\n\n"

        total_time = (time.time() - start_time) * 1000
        logger.info(f"[MARKITDOWN] 所有转换完成，耗时 {total_time:.1f}ms")

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/process-mineru", response_model=ProcessingResponse)
async def process_mineru_document(request: ProcessingRequest) -> ProcessingResponse:
    """
    处理 MinerU 解析的文档（Markdown + 图片）。

    本端点处理：
    1. 将图片从源目录复制到前端公共目录
    2. 更新 Markdown 中的图片路径引用
    3. 将内容分割成块
    4. 可选：将文档嵌入向量存储

    参数：
        request：ProcessingRequest，包含源路径和可选的嵌入标志

    返回：
        ProcessingResponse，包含处理结果

    示例：
        POST /documents/process-mineru
        {
            "source_path": "/path/to/mineru/output",
            "embed": true,
            "collection_name": "my_documents"
        }
    """
    try:
        processor = MineruProcessor()
        result = processor.process(
            source_path=request.source_path,
            embed=request.embed,
            collection_name=request.collection_name,
        )

        return ProcessingResponse(
            status="success",
            message="文档处理成功",
            images_copied=result["images_copied"],
            chunks_created=result["chunks_created"],
            embedded=result["embedded"],
            collection_name=result["collection_name"],
        )

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Document processing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}",
        )


@router.post("/embed", response_model=EmbedDocumentsResponse)
async def embed_documents(
    files: list[UploadFile] = File(...),
    collection_name: Optional[str] = Form(None),
) -> EmbedDocumentsResponse:
    _validate_embed_files(files)

    settings = get_settings()
    effective_collection = collection_name or settings.default_collection

    file_buffers = []
    for f in files:
        content = await f.read()
        file_buffers.append({
            "filename": f.filename,
            "content": content,
        })
        await f.close()

    vector_store = get_vector_store(effective_collection)
    splitter = _make_splitter(settings)

    total_chunks_embedded = 0
    results: list[EmbedFileResult] = []

    for idx, fb in enumerate(file_buffers):
        filename = fb["filename"]
        content = fb["content"]
        fmt = _get_file_format(filename)
        file_hash = _sha256_hex(content)

        try:
            if await _is_file_already_embedded(effective_collection, file_hash):
                results.append(
                    EmbedFileResult(
                        index=idx,
                        filename=filename,
                        format=fmt,
                        status="skipped",
                        file_hash=file_hash,
                        chunks_created=0,
                        message="File already embedded for this collection; skipped.",
                    )
                )
                continue

            try:
                docs = _load_documents_from_bytes(content, filename, fmt)
            except Exception:
                markdown, _elapsed_ms = await convert_upload_file(content, filename, timeout=CONVERSION_TIMEOUT)
                docs = [Document(page_content=markdown, metadata={"source": filename})]

            chunks = splitter.split_documents(docs)
            chunks = _enrich_chunk_metadata(
                chunks,
                filename=filename,
                fmt=fmt,
                file_hash=file_hash,
            )

            vector_store.add_documents(chunks)
            total_chunks_embedded += len(chunks)

            results.append(
                EmbedFileResult(
                    index=idx,
                    filename=filename,
                    format=fmt,
                    status="embedded",
                    file_hash=file_hash,
                    chunks_created=len(chunks),
                )
            )

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"[EMBED] Failed {filename}: {error_msg}", exc_info=True)
            results.append(
                EmbedFileResult(
                    index=idx,
                    filename=filename,
                    format=fmt,
                    status="error",
                    file_hash=file_hash,
                    chunks_created=0,
                    error=error_msg,
                )
            )

    return EmbedDocumentsResponse(
        status="success",
        message="Embedding completed",
        collection_name=effective_collection,
        total_chunks_embedded=total_chunks_embedded,
        results=results,
    )


__all__ = ["router"]
