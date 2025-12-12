"""RAG 系统的向量存储工具。

主要工作流：使用 MinerU 处理器（utils.mineru_processor）进行文档处理。
下面的遗留函数支持 PyPDFLoader 以实现向后兼容性。
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import get_settings


def get_embeddings() -> DashScopeEmbeddings:
    """初始化 DashScope Qwen 嵌入模型。"""
    settings = get_settings()
    return DashScopeEmbeddings(
        model=settings.embeddings_model,
        dashscope_api_key=settings.dashscope_api_key,
    )


def initialize_vector_store(
    collection_name: str = "pdf_documents",
    connection_string: Optional[str] = None,
) -> PGVector:
    """使用嵌入初始化 PGVector 存储。
    
    参数：
        collection_name: 向量存储中集合的名称。
        connection_string: PostgreSQL 连接字符串。如果为 None，从环境读取。
        
    返回：
        PGVector: 初始化的向量存储。
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
    """返回给定集合的缓存 PGVector 实例。
    
    参数：
        collection_name: 向量存储中集合的名称。
        
    返回：
        PGVector: 缓存的向量存储实例。
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
    """从目录加载 PDF 文件并分割成块。
    
    已弃用：改用 MinerU 处理器（utils.mineru_processor.MineruProcessor）。
    
    参数：
        pdf_dir: 包含 PDF 文件的目录。
        chunk_size: 每个块的最大大小（字符）。
        chunk_overlap: 块之间的重叠字符数。
        
    返回：
        包含分块文本的 Document 对象列表。
    """
    pdf_dir_path = Path(pdf_dir)
    
    if not pdf_dir_path.exists():
        raise ValueError(f"PDF directory does not exist: {pdf_dir}")
    
    # 在目录中查找所有 PDF 文件
    pdf_files = list(pdf_dir_path.glob("*.pdf"))
    
    if not pdf_files:
        raise ValueError(f"目录中未找到 PDF 文件：{pdf_dir}")
    
    # 加载所有 PDF
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
    """加载 PDF、分割并索引到向量存储。
    
    已弃用：改用 MinerU 处理器（utils.mineru_processor.MineruProcessor）。
    
    参数：
        pdf_dir: 包含 PDF 文件的目录。
        collection_name: 向量存储中集合的名称。
        chunk_size: 每个块的最大大小（字符）。
        chunk_overlap: 块之间的重叠字符数。
        
    返回：
        PGVector: 包含索引文档的向量存储。
    """
    # 加载和分割文档
    doc_splits = load_and_split_pdfs(
        pdf_dir=pdf_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    
    # 初始化向量存储
    settings = get_settings()
    if collection_name == "pdf_documents":
        collection_name = settings.default_collection
    
    vector_store = initialize_vector_store(collection_name=collection_name)
    
    # 将文档添加到向量存储
    vector_store.add_documents(doc_splits)
    
    return vector_store


def get_retriever(
    collection_name: str = "pdf_documents",
    search_kwargs: Optional[dict] = None,
):
    """从向量存储获取检索器。
    
    参数：
        collection_name: 向量存储中集合的名称。
        search_kwargs: 额外的搜索参数（例如，{"k": 4}）。
        
    返回：
        VectorStoreRetriever: 配置好的检索器。
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
