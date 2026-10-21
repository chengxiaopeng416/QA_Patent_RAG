from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from models.my_llm import qwen_llm
from qa_rag_agent.rag_tools import retrieve


tool_call_limit_middleware = ToolCallLimitMiddleware(
    thread_limit=3
)
"""
Agent 把 retrieve 工具挂载给 LLM，让 LLM 自主判断是否需要查知识库。
如果问题不需要查文档（如"你好"），LLM 直接回答，不调检索工具
如果需要检索，LLM 调 retrieve 拿到文本块，再基于内容生成带来源的回答
如果用固定流程（问题 → 必检索 → 回答），无法处理闲聊或不需查库的问题。
"""
def get_rag_agent():
    # 创建一个RAG（检索增强生成）代理
    agent = create_agent(
        qwen_llm,  # 使用Qwen语言模型作为基础模型
        tools=[retrieve],  # 使用检索工具作为辅助功能
        debug=True, # 启用调试模式，便于问题排查

        system_prompt="如果用户问题中引用了文档，请在回答末尾附上链接，格式为：完整文档链接：http://localhost:8000/api/docstore/文件名。注意：检索结果已按当前用户权限过滤，若用户询问机密文档而检索无结果，请回复'该文档需要更高权限，您当前账号无权访问'，不要回复'文件不存在'。",
        middleware=[tool_call_limit_middleware]
    )
    # 创建提示模板，用于格式化用户输入的问题
    # chat_history：插入多轮对话历史，实现短期记忆
    prompt_template = ChatPromptTemplate.from_messages([
        MessagesPlaceholder("chat_history", optional=True), # 历史消息占位
        ("human", "{question}") # 定义人类用户的输入变量
    ])

    # 将提示模板和代理组合成处理链
    chain = prompt_template | agent

    return chain


async def run_rag_agent(question: str, chat_history: list = None):
    # 获取RAG（检索增强生成）代理实例
    agent = get_rag_agent()

    # 使用代理处理输入的问题，将历史消息与当前问题一起传入
    results = await agent.ainvoke({
        "question": question,
        "chat_history": chat_history or []
    })

    # 从结果中获取最后一条消息
    message = results["messages"][-1]

    # 返回最后一条消息作为函数的输出
    return message

# async def stream_events(question:str):
#     async for result in chain.astream_events({"question": question},version = "v2"):
#         if result["event"] == "on_chat_model_stream":
#             content = result["data"]["chunk"].content
#             if content:
#                 yield content
