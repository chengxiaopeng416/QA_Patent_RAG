"""
RAG检索获取相关文档
"""
import os
from typing import Annotated

from langchain_chroma import Chroma
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from auth_load.permission import filter_accessible_documents
from database.models import Document, User, init_session
from models.my_llm import embeddings
from qa_rag_agent.document_utils import load_document, split_document
from utils.logger import setup_logger

retrieve_vector_store = Chroma(
    persist_directory=os.path.join(os.path.dirname(__file__), "..", "chroma_index"),
    collection_name="exchange_rag",
    embedding_function=embeddings
)

logger = setup_logger(__name__)


def _get_visible_sources(user_id: int) -> set:
    """
    获取用户有权限访问的文档文件名集合（去掉扩展名）
    用于RAG检索后过滤无权限的文档片段
    """
    db = init_session()()
    try:
        user = db.query(User).get(user_id)
        if user is None:
            return set()
        docs = db.query(Document).filter(Document.status == "active").all()
        allowed = filter_accessible_documents(user, docs)
        return {os.path.splitext(d.filename)[0] for d in allowed}
    finally:
        db.close()


def ingest_documents(directory: str):
    """
    加载目录下所有支持的文档 → 分割 → 向量化入库
    支持 .md .txt .pdf .docx 等多种格式
    """

    docs = load_document(directory)
    if not docs:
        print("未加载到任何文档")
        return 0

    chunks = split_document(docs)
    retrieve_vector_store.add_documents(chunks)
    print(f"入库完成：{len(chunks)} 个文本块")
    return len(chunks)


@tool
def retrieve(query: Annotated[str, "用户要检索的问题"], config: RunnableConfig):
    """进行RAG检索获取相关文档片段的工具"""

    # 从运行配置中获取当前用户，检索后过滤无权限的文档
    user_id = int(config.get("configurable", {}).get("user_id", 0) or 0)
    visible_sources = _get_visible_sources(user_id)

    retrieve_chunks = retrieve_vector_store.similarity_search(query, k=8)

    # 按用户权限过滤文档片段（来源文件名不在可见集合内的剔除）
    if visible_sources:
        retrieve_chunks = [
            chunk for chunk in retrieve_chunks
            if os.path.splitext(os.path.basename(chunk.metadata.get("source", "")))[0] in visible_sources
        ]
    retrieve_chunks = retrieve_chunks[:3]

    # 权限过滤后无结果时明确提示，避免LLM误认为"文件不存在"
    if not retrieve_chunks:
        return "未找到您有权访问的相关文档。注意：部分机密文档（如secret、top_secret级别）需要更高权限才能查看。"

    logger.info(f"检索到文档：{retrieve_chunks}")


    content = "\n\n".join(
        [f"【来源：{os.path.basename(chunk.metadata.get('source', ''))}】\n{chunk.page_content}" for chunk in retrieve_chunks])
    return content