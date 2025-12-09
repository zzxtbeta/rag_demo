"""Document processing API endpoints."""

import logging
from fastapi import APIRouter, HTTPException, status

from utils.mineru_processor import MineruProcessor, ProcessingRequest, ProcessingResponse

logger = logging.getLogger(__name__)

router = APIRouter()


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
