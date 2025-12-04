"""Initialize the vector store by indexing PDF documents.

Run this script to load PDF files from the data directory and index them
into the PostgreSQL vector store with pgvector.

Usage:
    python -m scripts.init_vectorstore
    
Or with custom parameters:
    python -m scripts.init_vectorstore --pdf-dir ./my_pdfs --chunk-size 1500
"""

import argparse
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config.settings import get_settings
from agent.vectorstore import index_documents

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main function to initialize the vector store."""
    parser = argparse.ArgumentParser(
        description="Initialize vector store by indexing PDF documents"
    )
    settings = get_settings()
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default="./data",
        help="Directory containing PDF files (default: ./data)",
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default=settings.default_collection,
        help=f"Name of the collection in vector store (default: {settings.default_collection})",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=settings.chunk_size,
        help=f"Maximum size of each chunk in characters (default: {settings.chunk_size})",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=settings.chunk_overlap,
        help=f"Number of overlapping characters between chunks (default: {settings.chunk_overlap})",
    )
    
    args = parser.parse_args()
    
    # Validate required configuration
    try:
        settings = get_settings()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
    
    # Check if PDF directory exists
    pdf_dir_path = Path(args.pdf_dir)
    if not pdf_dir_path.exists():
        logger.error(f"PDF directory does not exist: {args.pdf_dir}")
        sys.exit(1)
    
    # Check if there are PDF files
    pdf_files = list(pdf_dir_path.glob("*.pdf"))
    if not pdf_files:
        logger.error(f"No PDF files found in directory: {args.pdf_dir}")
        sys.exit(1)
    
    logger.info(f"Found {len(pdf_files)} PDF file(s) in {args.pdf_dir}")
    for pdf_file in pdf_files:
        logger.info(f"  - {pdf_file.name}")
    
    # Index documents
    logger.info("Starting document indexing...")
    logger.info(f"  Collection name: {args.collection_name}")
    logger.info(f"  Chunk size: {args.chunk_size}")
    logger.info(f"  Chunk overlap: {args.chunk_overlap}")
    
    try:
        vector_store = index_documents(
            pdf_dir=args.pdf_dir,
            collection_name=args.collection_name,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        
        logger.info("✓ Successfully indexed all documents into the vector store")
        logger.info(f"✓ Collection '{args.collection_name}' is ready for queries")
        
    except Exception as e:
        logger.error(f"Failed to index documents: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
