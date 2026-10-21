from typing import List

from langchain_core.documents import Document

from PA_RAG_retriever.ES_bm25_retriever import CustomElasticSearchBM25Retriever
from utils.config import es_index_name, es_url
from utils.logger import setup_logger

logger = setup_logger(__name__)

class BM25Index:
    def __init__(self, chunks: List[Document], delete_flag: bool = False):
        # es初始化
        self.es_retriever = CustomElasticSearchBM25Retriever(
            index_name=es_index_name,
            es_url=es_url
        )
        self.chunks = chunks
        self.delete_flag = delete_flag

    # 添加文档
    def add_documents(self):
        if self.delete_flag:
            self.es_retriever.delete_index()

        self.es_retriever.create_index()
        texts = [chunk.page_content for chunk in self.chunks if chunk.page_content]
        self.es_retriever.add_texts(texts)
        logger.info("BM25索引创建完成")
