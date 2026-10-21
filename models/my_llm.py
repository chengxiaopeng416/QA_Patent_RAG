"""
创建大模型
"""

from langchain_ollama import OllamaEmbeddings
from langchain_openai import ChatOpenAI

from utils.config import qwen_model_name, qwen_api_key, qwen_base_url, embeddings_model_name

qwen_llm = ChatOpenAI(
    model=qwen_model_name,
    api_key=qwen_api_key,
    base_url=qwen_base_url,
    #temperature:温度参数，取值[0-1]
    #越接近0越严谨
    #思维发散在0.7-1之间
    #公式：softmax =（result/temperature）
    temperature=0.5,
    # max_tokens: 单次输出最大token数。
    # 之前是1024，但Agent工具调用时模型会复述系统提示里的工具描述，
    # 1024 经常不够，输出到一半被截断 → 工具调用JSON残缺，
    # agent拿不到完整调用只能中途结束，最终答案丢失（只剩半句过渡语）。
    # 工具调用DDL和工具描述都很长，4096 更加稳妥。
    max_tokens=4096

)

embeddings = OllamaEmbeddings(
    model = embeddings_model_name
)










