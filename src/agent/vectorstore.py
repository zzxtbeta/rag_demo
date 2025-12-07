"""Vector store utilities for RAG system."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import get_settings


def get_embeddings() -> OpenAIEmbeddings:
    """Initialize OpenAI embeddings model."""
    settings = get_settings()
    embeddings_config = {
        "model": "text-embedding-3-large",
        "openai_api_key": settings.openai_embeddings_api_key,
    }
    
    if settings.litellm_base_url:
        embeddings_config["openai_api_base"] = settings.litellm_base_url
    
    return OpenAIEmbeddings(**embeddings_config)


def initialize_vector_store(
    collection_name: str = "pdf_documents",
    connection_string: Optional[str] = None,
) -> PGVector:
    """Initialize PGVector store with embeddings.
    
    Args:
        collection_name: Name of the collection in the vector store.
        connection_string: PostgreSQL connection string. If None, reads from environment.
        
    Returns:
        PGVector: Initialized vector store.
    """
    settings = get_settings()
    if connection_string is None:
        connection_string = settings.psycopg_connection
    if collection_name == "pdf_documents":
        collection_name = settings.default_collection
    
    embeddings = get_embeddings()
    
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection_string,
        use_jsonb=True,
    )
    
    return vector_store


@lru_cache(maxsize=None)
def get_vector_store(
    collection_name: str = "pdf_documents",
) -> PGVector:
    """Return a cached PGVector instance for the given collection.
    
    Args:
        collection_name: Name of the collection in the vector store.
        
    Returns:
        PGVector: Cached vector store instance.
    """
    settings = get_settings()
    if collection_name == "pdf_documents":
        collection_name = settings.default_collection
    return initialize_vector_store(collection_name=collection_name)


def load_and_split_pdfs(
    pdf_dir: str = "./data",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> list[Document]:
    """Load PDF files from directory and split into chunks.
    
    Args:
        pdf_dir: Directory containing PDF files.
        chunk_size: Maximum size of each chunk in characters.
        chunk_overlap: Number of overlapping characters between chunks.
        
    Returns:
        List of Document objects containing chunked text.
    """
    pdf_dir_path = Path(pdf_dir)
    
    if not pdf_dir_path.exists():
        raise ValueError(f"PDF directory does not exist: {pdf_dir}")
    
    # Find all PDF files in the directory
    pdf_files = list(pdf_dir_path.glob("*.pdf"))
    
    if not pdf_files:
        raise ValueError(f"No PDF files found in directory: {pdf_dir}")
    
    # Load all PDFs
    all_docs = []
    for pdf_file in pdf_files:
        loader = PyPDFLoader(str(pdf_file))
        docs = loader.load()
        all_docs.extend(docs)
    
    settings = get_settings()
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n#", # 一级标题
            "\n##", # 二级标题
            "\n###", # 三级标题
            "\n\n",  # 段落
            "\n",   # 行
            " ",   # 词
            "",    # 字符
        ],
        add_start_index=True,
    )
    
    doc_splits = text_splitter.split_documents(all_docs)
    
    return doc_splits


def index_documents(
    pdf_dir: str = "./data",
    collection_name: str = "pdf_documents",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> PGVector:
    """Load PDFs, split them, and index into vector store.
    
    Args:
        pdf_dir: Directory containing PDF files.
        collection_name: Name of the collection in the vector store.
        chunk_size: Maximum size of each chunk in characters.
        chunk_overlap: Number of overlapping characters between chunks.
        
    Returns:
        PGVector: Vector store with indexed documents.
    """
    # Load and split documents
    doc_splits = load_and_split_pdfs(
        pdf_dir=pdf_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    
    # Initialize vector store
    settings = get_settings()
    if collection_name == "pdf_documents":
        collection_name = settings.default_collection
    
    vector_store = initialize_vector_store(collection_name=collection_name)
    
    # Add documents to vector store
    vector_store.add_documents(doc_splits)
    
    return vector_store


def get_retriever(
    collection_name: str = "pdf_documents",
    search_kwargs: Optional[dict] = None,
):
    """Get a retriever from the vector store.
    
    Args:
        collection_name: Name of the collection in the vector store.
        search_kwargs: Additional search parameters (e.g., {"k": 4}).
        
    Returns:
        VectorStoreRetriever: Configured retriever.
    """
    settings = get_settings()
    if search_kwargs is None:
        search_kwargs = {"k": settings.retriever_top_k}
    if collection_name == "pdf_documents":
        collection_name = settings.default_collection
    
    vector_store = get_vector_store(collection_name=collection_name)
    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
    
    return retriever


__all__ = [
    "get_embeddings",
    "initialize_vector_store",
    "get_vector_store",
    "load_and_split_pdfs",
    "index_documents",
    "get_retriever",
]
