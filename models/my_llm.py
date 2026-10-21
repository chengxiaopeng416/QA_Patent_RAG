"""
创建大模型
"""
from langchain_ollama import OllamaEmbeddings
from langchain_openai import ChatOpenAI

from utils.env_utils import qwen_model_name, qwen_api_key, qwen_base_url, embeddings_model_name

qwen_llm = ChatOpenAI(
    model=qwen_model_name,
    api_key=qwen_api_key,
    base_url=qwen_base_url,
    #temperature:温度参数，取值[0-1]
    #越接近0越严谨
    #思维发散在0.7-1之间
    #公式：softmax =（result/temperature）
    temperature=0.4,
    max_tokens=1024

)

embeddings = OllamaEmbeddings(
    model = embeddings_model_name
)








