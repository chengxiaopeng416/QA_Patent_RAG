"""
创建重排器reranker
将retriever和reranker封装为混合检索器
"""
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

from utils.config import HuggingFace_Cross_Encoder_model_name
from utils.logger import setup_logger

_shared_reranker = None

logger = setup_logger(__name__)


def get_reranker():
    """全局共享同一个重排器（含 2.2GB 模型），所有入口复用"""
    global _shared_reranker
    if _shared_reranker is None:
        _shared_reranker = Reranker(HuggingFace_Cross_Encoder_model_name)
    return _shared_reranker


class Reranker:
    def __init__(self, cross_encoder_name, top_n=10):
        self.cross_encoder_name = cross_encoder_name
        self.top_n = top_n
        if not cross_encoder_name:
            raise ValueError("HUGGINGFACE_CROSS_ENCODER_MODEL_NAME 未配置")
        self.reranker = None

    # 创建并获取rerank（模型只加载一次，之后复用）
    def get_rerank(self):
        if self.reranker is None:
            # 创建交叉编码器（crossEncoder）
            cross_encoder = HuggingFaceCrossEncoder(
                model_name=self.cross_encoder_name
            )
            # 创建reranker
            self.reranker = CrossEncoderReranker(
                model=cross_encoder,
                top_n=self.top_n
            )
        return self.reranker

    def rerank(self, query, docs):
        reranker = self.get_rerank()
        chunks = reranker.compress_documents(docs, query)
        return chunks
