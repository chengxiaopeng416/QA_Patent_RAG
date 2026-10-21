from PA_RAG_indexer.bm25_index import BM25Index
from PA_RAG_indexer.chroma_vector_index import VectorIndex
from PA_RAG_indexer.neo4j_index import Neo4jIndex
from loader_and_spliter.document_loader import DocumentLoader
from loader_and_spliter.document_spliter import DocumentSplitter

from models.chroma import vectorstore
from utils.logger import setup_logger

logger = setup_logger(__name__)
def create_index(
        file_path: str,
        #添加3个开关参数
        vector_delete_flag: bool = False,
        bm25_delete_flag: bool = False,
        neo4j_delete_flag: bool = False
):
    # 加载文档
    loader = DocumentLoader(file_path)
    docs = loader.load()

    # 分割文档
    splitter = DocumentSplitter(docs)
    chunks = splitter.split()

    # 创建向量数据库索引
    vector_index = VectorIndex(
        chunks,
        vectorstore=vectorstore,
        delete_flag=vector_delete_flag
    )

    if vector_index.delete_flag:
        vector_index.delete_vectors()

    vector_index.add_documents()


    # 创建bm25索引
    bm25_index = BM25Index(
        chunks,
        delete_flag= bm25_delete_flag
    )
    bm25_index.add_documents()

    # 创建neo4j索引
    neo4j_index = Neo4jIndex(
        delete_flag=neo4j_delete_flag
    )
    # 将整个文档提取三元组
    # 也可以考虑按照分割后的文档片段提取
    neo4j_index.create_neo4j_index(docs)

    logger.info("Neo4j三元组索引创建完成")
