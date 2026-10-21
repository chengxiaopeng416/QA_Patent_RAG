"""
创建Agent智能体
"""
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware

from PARAG_agent.prompt import AGENT_SYSTEM_PROMPT
from models.my_llm import qwen_llm
from tools.doc_store import DocStore
from tools.reranker_tool import create_rerank_tool
from tools.rrf_retriever_tool import create_retriever_tools
from tools.strategy_tool import strategy_tool


def build_chat_agent(doc_store: DocStore):
    # 检索工具
    retriever_tools = create_retriever_tools(doc_store)
    # 重排工具
    reranker_tool = create_rerank_tool(doc_store)

    agent = create_agent(
        qwen_llm,
        tools=[
            strategy_tool,
            *retriever_tools,
            reranker_tool,

        ],
        system_prompt = AGENT_SYSTEM_PROMPT,
        middleware = [TodoListMiddleware()],
    )
    return agent




















