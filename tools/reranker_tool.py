"""
对检索结果进行rerank精拍

"""
from typing import Annotated

from langchain_core.tools import tool

from reranker.reranker import get_reranker
from tools.doc_store import DocStore
from utils.config import max_rerank_docs


def create_rerank_tool(
        doc_store: DocStore
):
    @tool
    def rerank_doc(
            query: Annotated[str, "用户问题"],
            doc_ids: Annotated[list[str], "doc_store中储存的文档id列表"],

    ):
        """
        根据检索的结果进行重排序，得到排序后的结果。只要进行检索后，都要调用该工具

        """
        # 根据doc_id获取原文档内容
        documents = doc_store.get_batch(doc_ids)
        # CrossEncoder 精排,如果文档个数超过设定的阈值，则将超过的文档抛弃
        if len(documents) > max_rerank_docs:
            documents = documents[:max_rerank_docs]

        # 重排
        reranker = get_reranker()
        ranked = reranker.rerank(query, documents)

        if len(ranked) == 0:
            return "没有找到相关文档"
        results = []
        for doc in ranked:
            score = doc.metadata.get("relevance_score", 0)
            dic = {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "relevance_score": score
            }
            results.append(dic)

        return results

    return rerank_doc
