"""MinerU document processor for handling parsed PDF outputs."""

import logging
import re
import shutil
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from agent.vectorstore import get_vector_store
from config.settings import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# Schemas
# ============================================================================


class ProcessingRequest(BaseModel):
    """Request schema for document processing."""

    source_path: str = Field(
        ...,
        description="Local path to MinerU output directory (containing auto/ subdirectory)"
    )
    embed: bool = Field(
        default=False,
        description="Whether to perform vector embedding after processing"
    )
    collection_name: Optional[str] = Field(
        default=None,
        description="Vector store collection name (uses default if not specified)"
    )


class ProcessingResponse(BaseModel):
    """Response schema for document processing."""

    status: str = Field(description="Processing status: success or error")
    message: str = Field(description="Status message")
    images_copied: int = Field(default=0, description="Number of images copied")
    chunks_created: int = Field(default=0, description="Number of document chunks")
    embedded: bool = Field(default=False, description="Whether embedding was performed")
    collection_name: Optional[str] = Field(default=None, description="Vector store collection name")
    error: Optional[str] = Field(default=None, description="Error message if failed")


# ============================================================================
# Processor
# ============================================================================


class MineruProcessor:
    """Process MinerU-parsed documents (Markdown + images)."""

    def __init__(self):
        """Initialize processor with settings."""
        self.settings = get_settings()
        self.chunk_size = self.settings.chunk_size
        self.chunk_overlap = self.settings.chunk_overlap

    def process(
        self,
        source_path: str,
        embed: bool = False,
        collection_name: Optional[str] = None,
    ) -> dict:
        """
        Process MinerU output directory.

        Args:
            source_path: Path to MinerU output directory (containing auto/ subdirectory)
            embed: Whether to perform vector embedding
            collection_name: Vector store collection name (uses default if None)

        Returns:
            Dictionary with processing results
        """
        source_dir = Path(source_path)

        if not source_dir.exists():
            raise ValueError(f"Source directory not found: {source_path}")

        auto_dir = source_dir / "auto"
        if not auto_dir.exists():
            raise ValueError(f"MinerU auto directory not found: {auto_dir}")

        # Find markdown file
        md_files = list(auto_dir.glob("*.md"))
        if not md_files:
            raise ValueError(f"No markdown files found in: {auto_dir}")

        md_file = md_files[0]
        logger.info(f"Processing markdown file: {md_file.name}")

        # Step 1: Copy images
        images_copied = self._copy_images(auto_dir)

        # Step 2: Read and process markdown
        with open(md_file, "r", encoding="utf-8") as f:
            md_content = f.read()

        # Step 3: Update image paths
        updated_content = self._update_image_paths(md_content)

        # Step 4: Split content into chunks
        documents = self._split_content(updated_content, md_file.stem)

        # Step 5: Embed if requested
        if embed:
            if collection_name is None:
                collection_name = self.settings.default_collection
            self._embed_documents(documents, collection_name)
            logger.info(f"Documents embedded to collection: {collection_name}")

        return {
            "images_copied": images_copied,
            "chunks_created": len(documents),
            "embedded": embed,
            "collection_name": collection_name if embed else None,
        }

    def _copy_images(self, auto_dir: Path) -> int:
        """
        Copy images from MinerU output to frontend public directory.

        Args:
            auto_dir: Path to MinerU auto directory

        Returns:
            Number of images copied
        """
        images_src = auto_dir / "images"
        if not images_src.exists():
            logger.warning(f"Images directory not found: {images_src}")
            return 0

        # Create target directory in frontend
        # Convert to absolute path to avoid issues with relative paths
        images_target = Path(self.settings.frontend_images_dir).resolve()
        images_target.mkdir(parents=True, exist_ok=True)

        copied_count = 0
        for image_file in images_src.glob("*"):
            if image_file.is_file():
                target_file = images_target / image_file.name
                shutil.copy2(image_file, target_file)
                copied_count += 1

        logger.info(f"Copied {copied_count} images to {images_target}")
        return copied_count

    def _update_image_paths(self, content: str) -> str:
        """
        Update image paths in markdown from local to frontend-accessible paths.

        Args:
            content: Original markdown content

        Returns:
            Updated markdown content
        """
        # Match pattern: ![](images/filename.ext)
        pattern = r"!\[\]\(images/([^)]+)\)"

        def replace_path(match):
            filename = match.group(1)
            return f"![]({self.settings.frontend_image_prefix}/{filename})"

        updated = re.sub(pattern, replace_path, content)
        replaced_count = len(re.findall(pattern, content))
        logger.info(f"Updated {replaced_count} image path references")

        return updated

    def _split_content(self, content: str, source_name: str) -> List[Document]:
        """
        Split markdown content into chunks.

        Args:
            content: Markdown content
            source_name: Source document name for metadata

        Returns:
            List of Document objects
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
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

        texts = splitter.split_text(content)
        documents = []

        for i, text in enumerate(texts):
            doc = Document(
                page_content=text,
                metadata={
                    "source": source_name,
                    "chunk_id": i,
                    "document_type": "mineru_markdown",
                    "total_chunks": len(texts),
                },
            )
            documents.append(doc)

        logger.info(f"Split content into {len(documents)} chunks")
        return documents

    def _embed_documents(self, documents: List[Document], collection_name: str) -> None:
        """
        Embed documents and store in vector database.

        Args:
            documents: List of Document objects to embed
            collection_name: Vector store collection name
        """
        vector_store = get_vector_store(collection_name)
        vector_store.add_documents(documents)
        logger.info(f"Embedded {len(documents)} documents to {collection_name}")


__all__ = ["MineruProcessor", "ProcessingRequest", "ProcessingResponse"]
