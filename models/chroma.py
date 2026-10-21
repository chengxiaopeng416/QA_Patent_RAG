"""
创建chroma数据库
"""
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from utils.config import embeddings_model_name

embeddings = OllamaEmbeddings(
    model = embeddings_model_name
)

vectorstore = Chroma(
    host="localhost",
    port=8081,
    embedding_function=embeddings,
    collection_name="PatentRAG_default",  # 换一个新名字
    collection_metadata={"host_space": "default", "hnsw:space": "cosine"}
)