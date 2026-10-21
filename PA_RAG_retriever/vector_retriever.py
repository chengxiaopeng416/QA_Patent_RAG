
"""
检索向量数据库
如果单独进行向量检索可使用：vector_retrieve和 vector_retrieve_with_score
混合检索只需要获取retriever即可，可以使用：get_retriever

可还以了解一下MMR检索
"""
from utils.config import default_top_k
from utils.logger import setup_logger

logger = setup_logger(__name__)

class VectorRetriever:
    def __init__(
            self, vectorstore,
            top_k: int = default_top_k,
            score_threshold: float = 0.5
    ):
        self.vectorstore = vectorstore
        self.top_k = top_k
        self.score_threshold = score_threshold

    # def vector_retrieve(self,query):
    #     # #使用向量数据库做相似度查询
    #     # self.vectorstore.similar_search(self.query,k=5)
    #
    #     # 定义一个检索器,可以在其中设置检索策略
    #     retriever = self.vectorstore.as_retriever(
    #         search_type="similarity_score_threshold",
    #         search_kwargs={
    #             "k": 5,
    #             "score_threshold": 0.5
    #         }
    #     )
    #
    #     chunks = retriever.invoke(query)
    #
    #     return chunks

    # similarity_search_with_score: 返回分数的相识度检索，返回结果是[(Document,score),(Document, score),...]
    # 根据分数可以做相对灵活的处理
    def vector_retrieve_with_score(self, query):
        results = self.vectorstore.similarity_search_with_score(
            query,
            k=self.top_k
        )

        # cosine相似度计算：计算出cosine值之后做（1-cosine).分数越小越相似
        # 判断：分数大于0.5的文档被过滤
        chunks = [(doc, score) for doc, score in results if score <= self.score_threshold]

        logger.info(f"检索到{len(chunks)}条数据")

        return chunks

    #获取相似度的检索器
    def get_retriever(self):
        # 定义一个检索器,可以在其中设置检索策略
        retriever = self.vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": self.top_k,
                "score_threshold": self.score_threshold
            }
        )
        return retriever


