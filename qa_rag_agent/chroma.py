"""
通过chroma将分割后的文档片段向量化并入库
ChromaDB 的作用
存文档切片的向量嵌入，用于语义检索。
用户问"年假政策"，ChromaDB 召回最相关的片段，LLM 基于其召回的片段生成回答，不依赖关键词匹配
轻量：本地持久化到 chroma_index/，不需要单独部署服务
没用 ES 或 Milvus 的原因：项目规模（13 个文档、152 个块）不需要分布式，Chroma 零配置就能跑。
"""
import os

from langchain_chroma import Chroma

from models.my_llm import embeddings
from qa_rag_agent.document_utils import load_document, split_document
from utils.logger import setup_logger

logger = setup_logger(__name__)

# persist_directory:本地持久化的目录，可以理解为数据库(本地路径)
# collection_name:集合名称，可以理解为数据表
# embedding_function:入库使用词嵌入模型向量化
vector_store = Chroma(
    persist_directory=os.path.join(os.path.dirname(__file__), "..", "chroma_index"),
    collection_name="exchange_rag",
    embedding_function=embeddings
)
def create_index(filepath: str):
    """

    :param filepath:
    """
    docs = load_document(filepath)
    chunks = split_document(docs)

    #add_documents:将文档片段向量化后入库
    vector_store.add_documents(chunks)


def delete_index():
    ids = vector_store.get()["ids"]
    vector_store.delete(ids)
    logger.info("删除成功")


# 索引创建流程：
# 1.前端页面实现文档上传功能
# 2.将上传的文档通过api接口发送给后台
# 3.后台进行文档加载、分割、向量化、入库
if __name__ == '__main__':
    delete_index()
    # create_index("../docs/2025年战略规划.docx")



