"""
意图识别工具：根据用户的问题，通过大模型推理，判断应该调用哪些工具执行检索
"""
import hashlib
from typing import Annotated

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from pydantic import BaseModel

from PARAG_agent.prompt import ANALYZE_PROMPT
from models.my_llm import qwen_llm
from service.redis_service import RedisService

class StrategyAnalyzer(BaseModel):
    retrieval_types: list[str] = ["vector"]
    need_decomposition: bool = False
    sub_queries_hint: list[str]
    reasoning: str

@tool
def strategy_tool(query: Annotated[str, "用户的问题"]):
    """
    分析用户问题的检索策略。
    由LLM判断需要哪种检索方式（vector/bm25/hybrid/graph），以及是否需要拆分子问题。
    根据用户的问题，通过大模型推理，判断应该调用哪些工具执行检索
    """
    # 引入redis缓存机制，如果用户的问题在缓存中能命中则直接返回缓存中保存的识别结果
    # 如果用户的问题在缓存中无法命中，则调用大模型进行推理，并将推理结果保存到redis缓存中
    # 最后返回推理结果

    # 初始化redis对象
    redis_service = RedisService()

    # 根据用户问题生成redis缓存的key
    cache_key = hashlib.md5(query.strip().encode('utf-8')).hexdigest()

    # 如果缓存命中，从缓存中获取key对应的value
    cache_result = redis_service.get_strategy(cache_key)
    if cache_result is not None:
        return cache_result

    # 如果缓存中没有命中，则调用大模型进行推理
    prompt_template = ChatPromptTemplate.from_template(ANALYZE_PROMPT)

    chain = prompt_template | qwen_llm.with_structured_output(StrategyAnalyzer)

    #得到的对象的数据类型： StrategyAnalyzer
    result = chain.invoke({"query": query})

    if isinstance(result, StrategyAnalyzer):
        result = result.model_dump()

    # 将大模型识别的结果存入redis缓存中
    redis_service.set_strategy(cache_key, result)

    return result














