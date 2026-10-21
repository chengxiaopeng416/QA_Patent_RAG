"""
自定义类，继承ElasticSearchBM25Retriever
自定义删除索引，索引是否存在判断，创建索引
重写父类的_get_relevant_documents方法,添加检索返回的数据条数
"""
from typing import List, Optional

from elasticsearch import Elasticsearch
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document

from langchain_community.retrievers import ElasticSearchBM25Retriever

from utils.logger import setup_logger

logger = setup_logger(__name__)

class CustomElasticSearchBM25Retriever(ElasticSearchBM25Retriever):
    # 实例初始化
    def __init__(self, es_url: str, index_name: str, current_size: Optional[int] = None, **kwargs):
        client = Elasticsearch(es_url)
        super().__init__(client=client, index_name=index_name, **kwargs)
        object.__setattr__(self, "index_name", index_name)
        object.__setattr__(self, "current_size", current_size)
        object.__setattr__(self, "client", client)

    # 判断es索引是否存在
    def check_index_exists(self):
        if self.client.indices.exists(index=self.index_name):
            return True
        return False
    # 先判断es索引是否不存在，存在返回False，不存在返回True

    # 删除索引
    # 不存在返回True执行删除索引（清空为创建做准备），存在返回False不执行
    def delete_index(self):
        if self.check_index_exists():
            self.client.indices.delete(index=self.index_name)
            logger.info("ES索引删除成功")
        return

    # 创建索引
    # 【我新加的容错逻辑】：
    # 原因：用户可能重复上传同一个文件，如果每次上传都重新创建 ES 索引，
    #        会抛 "resource_already_exists_exception" 报错。
    #        加了下面的判断后：索引已存在就直接跳过创建，改为往里增量加文档，更稳妥。
    def create_index(self, k1=1.5, b=0.75):
        try:
            # 索引已存在则跳过创建，直接增量添加文档
            if self.check_index_exists():
                logger.info("ES索引已存在，跳过创建")
                return
            settings = {
                "index": {
                    "similarity": {
                        "my_bm25": {
                            "type": "BM25",
                            "k1": k1,
                            "b": b
                        }
                    }
                }
            }
            mappings = {
                "properties": {
                    "content": {
                        "type": "text",
                        "analyzer": "ik_max_word",
                        "search_analyzer": "ik_max_word",
                        "similarity": "my_bm25"
                    }
                }
            }
            self.client.indices.create(index=self.index_name, settings=settings, mappings=mappings)
            logger.info("ES索引创建成功")
        except Exception as e:
            logger.error("ES索引创建失败")
            raise Exception("ES索引创建失败", e)

    # 重写父类的_get_relevant_documents方法,添加检索返回的数据条数
    def _get_relevant_documents(
            self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        size = self.current_size if self.current_size else 10

        query_dict = {
            "query": {
                "match": {
                    "content": query
                }
            },
            "size": size
        }
        results = self.client.search(
            index=self.index_name,
            body=query_dict
        )
        document_list = []
        for hit in results['hits']['hits']:
            content = hit['_source']['content']
            metadata = {
                "doc_id": hit['_id'],
                "score": hit['_score']
            }
            doc = Document(page_content=content, metadata=metadata)
            document_list.append(doc)

        return document_list
    # 清除索引文档
    def clear_documents(self):
        response = self.client.delete_by_query(
            index=self.index_name,
            body={
                "query": {
                    "match_all": {}
                }
            },
            refresh=True
        )

        deleted = response.get('deleted', 0)
        logger.info(f"清除{deleted} 条数据")
        return deleted

