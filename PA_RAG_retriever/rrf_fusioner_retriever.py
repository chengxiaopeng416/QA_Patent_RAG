from collections import defaultdict
from itertools import chain
from langchain_core.documents import Document


class RRFFusioner:
    """RRF（Reciprocal Rank Fusion）融合器：把多路检索结果按排名加权合并成一份统一排序"""

    def __init__(self, weights: list[float], c: int = 60):
        # weights：每路检索的权重，比如 [0.5, 0.5] 表示向量和BM25各占一半
        # c：平滑常数，防止排名靠前的文档分数差距过大，默认60是论文推荐值
        self.weights = weights
        self.c = c

    def fuse(self, doc_lists: list[list[Document]]) -> list[Document]:
        """
        核心方法：把多路检索结果融合成一份排序结果
        输入：[[向量检索的文档], [BM25检索的文档], [图检索的文档]]
        输出：融合排序后的文档列表
        """

        # --- 第一步：给每个文档算融合分数 ---
        # 公式：score += 权重 / (排名 + c)
        # 举例：某文档在向量路排第1、BM25路排第3，权重都是0.5，c=60
        #   向量贡献：0.5 / (1+60) = 0.0082
        #   BM25贡献：0.5 / (3+60) = 0.0079
        #   总分：0.0161
        scores = defaultdict(float)
        for doc_list, weight in zip(doc_lists, self.weights):
            for rank, doc in enumerate(doc_list, start=1):
                key = self._make_key(doc)
                scores[key] += weight / (rank + self.c)

        # --- 第二步：去重 ---
        # 同一篇文档可能被多路检索同时命中，只保留一份
        seen: dict[str, Document] = {}
        for doc in chain(*doc_lists):
            key = self._make_key(doc)
            if key not in seen:
                seen[key] = doc

        # --- 第三步：按融合分数从高到低排序 ---
        ranked = sorted(
            seen.values(),
            key=lambda d: scores[self._make_key(d)],
            reverse=True,
        )

        # --- 第四步：把分数写进每个文档的 metadata ---
        # 这样下游工具（比如 rerank）能直接读到融合分数
        for doc in ranked:
            doc.metadata["rrf_score"] = round(scores[self._make_key(doc)], 6)

        return ranked

    def _make_key(self, doc: Document) -> str:
        """给文档生成唯一标识，用于去重和查分数"""
        # 优先用 doc_id（如果有），否则用文档内容做 key
        return doc.metadata.get("doc_id", doc.page_content)