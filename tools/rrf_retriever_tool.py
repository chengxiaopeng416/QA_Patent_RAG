"""
定义检索相关的工具：
向量，BM25，图知识库，混合检索
"""
from __future__ import annotations

from typing import Annotated

from langchain_core.documents import Document
from langchain_core.tools import tool

from PA_RAG_retriever.ES_bm25_retriever import CustomElasticSearchBM25Retriever
from PA_RAG_retriever.neo4j_retriever import Neo4jRetriever
from PA_RAG_retriever.rrf_fusioner_retriever import RRFFusioner
from PA_RAG_retriever.vector_retriever import VectorRetriever
from models.chroma import vectorstore
from tools.doc_store import DocStore
from utils.config import default_top_k, es_url, es_index_name


def create_retriever_tools(doc_store: DocStore):
    """
    创建检索相关的工具
    """

    # 工具执行完成后得到相关文档，将文档进行ID映射，统一返回一个字典数据，字典会在工具调用之间共享
    # route：路由，表示哪个工具执行的结果
    # score：检索到的文档得出的分数
    def to_compact(doc: Document, route: str, score: float | None = None):
        doc_id = doc_store.add_doc(doc)

        snippet = doc_store.get_snippet(doc)

        items = {
            "doc_id": doc_id,
            "snippet": snippet,
            "route": route
        }

        if score is not None:
            items["score"] = score
        return items

    # 定义向量检索工具
    @tool
    def vector_retriever(
            query: Annotated[str, "用户的问题"],
            top_k: Annotated[int, "检索到的文档取前k个"] = default_top_k
    ):
        """
        向量检索工具：
        1. 根据用户的问题，进行向量检索，从向量库中检索出相关的文档
        2. 将检索到的文档进行ID映射，统一返回一个字典数据，字典会在工具调用之间共享
        3. 返回一个列表，其中的元素为字典数据
        4. 返回的字典数据中包含文档的ID，文档的摘要，文档的分数
        5. 当需要进行向量检索时调用该工具
        """
        retriever = VectorRetriever(
            vectorstore=vectorstore,
            top_k=top_k,
            score_threshold=0.7

        )
        # 进行相似度计算，得到一个列表，其中的元素为元组：(Document, score)
        chunks = retriever.vector_retrieve_with_score(query)
        results = []
        # 越大越相似
        for doc, score in chunks:
            similar_score = 1 - score
            result = to_compact(doc, "vector", score=similar_score)
            results.append(result)

        return results

    # 定义BM25检索工具
    @tool
    def bm25_retriever(
            query: Annotated[str, "用户的问题"],
            size: Annotated[int, "从检索结果中取前k个"] = default_top_k
    ):
        """
        BM25检索工具：
        1. 根据用户的问题，进行BM25检索，从文档库中检索出k个相关的文档片段
        2. 当需要进行BM25检索时调用该工具

        """
        retriever = CustomElasticSearchBM25Retriever(
            es_url=es_url,
            index_name=es_index_name,
            current_size=size
        )

        chunks = retriever.invoke(query)

        results = []

        for doc in chunks:
            result = to_compact(doc, "bm25", score=doc.metadata.get("score"))
            results.append(result)

        return results

    # 定义混合检索工具
    @tool
    def hybrid_retriever(
            query: Annotated[str, "用户的问题"],
            vector_top_k: Annotated[int, "从向量检索结果中取前k个"] = default_top_k,
            bm25_top_k: Annotated[int, "从BM25检索结果中取前k个"] = default_top_k,
            final_top_k: Annotated[int, "从混合检索的最终结果中取前k个"] = default_top_k
    ):
        """
        混合检索工具：
        1. 根据用户的问题，进行混合检索，从向量库和文档库中检索出final_top_k个相关的文档
        2. 当需要进行混合检索时调用该工具
        """
        # 初始化向量检索器
        vector_retriever = VectorRetriever(
            vectorstore=vectorstore,
            top_k=vector_top_k,
            score_threshold=0.5
        )

        # 初始化BM25检索器
        bm25_retriever = CustomElasticSearchBM25Retriever(
            es_url=es_url,
            index_name=es_index_name,
            current_size=bm25_top_k
        )

        # 初始化混合检索器
        # 用独立融合器合并两路结果
        fusioner = RRFFusioner(weights=[0.5, 0.5], c=60)
        chunks = fusioner.fuse([
            vector_retriever.get_retriever().invoke(query),
            bm25_retriever.invoke(query)
        ])
        chunks = chunks[:final_top_k]

        results = []

        for doc in chunks:
            result = to_compact(doc, "hybrid", score=doc.metadata.get("rrf_score"))
            results.append(result)

        return results

    #图知识库检索器
    @tool
    def graph_retriever(
            query: Annotated[str, "用户的问题"],
            top_k: Annotated[int, "图知识库检索得到前k个结果"] = default_top_k
    ):
        """
        图知识库检索工具：
        1. 根据用户的问题，进行图知识库检索，获取结果中的前k个结果的工具
        2. 当需要进行图知识库检索时调用该工具
        """
        retriever = Neo4jRetriever(
            top_k=top_k,
        )

        triples = retriever.get_paths(query)

        results = []

        for triple in triples:
            doc = Document(
                page_content=triple["content"],
                metadata=triple.get("metadata", {})
            )
            result = to_compact(doc, "graph")
            results.append(result)

        return results

    return [vector_retriever, bm25_retriever, hybrid_retriever, graph_retriever]
