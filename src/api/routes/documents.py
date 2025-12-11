"""文档处理 API 端点."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.markitdown_converter import convert_upload_file
from utils.mineru_processor import MineruProcessor, ProcessingRequest, ProcessingResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# 常量配置
MAX_FILES = 2
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB
CONVERSION_TIMEOUT = 60  # 秒

SUPPORTED_FORMATS = {
    "pdf", "pptx", "docx", "xlsx", "xls",
    "jpg", "jpeg", "png", "gif", "webp",
    "mp3", "wav", "m4a",
    "html", "htm", "csv", "json", "xml", "txt",
    "zip", "epub",
}


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


def _get_file_format(filename: str) -> str:
    """从文件名提取文件格式."""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


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
    Process MinerU-parsed document (Markdown + images).

    This endpoint handles:
    1. Copying images from source to frontend public directory
    2. Updating image path references in markdown
    3. Splitting content into chunks
    4. Optionally embedding documents to vector store

    Args:
        request: ProcessingRequest with source_path and optional embed flag

    Returns:
        ProcessingResponse with processing results

    Example:
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
            message="Document processed successfully",
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


__all__ = ["router"]
