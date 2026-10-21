import os
from typing import Literal

import aiosqlite
from langchain_core.messages import HumanMessage, AIMessage, RemoveMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.constants import START, END
from langgraph.graph import MessagesState, StateGraph
from pydantic import BaseModel, Field

from company_agent import chat_agent
from models.my_llm import qwen_llm
from qa_rag_agent import rag_agent

#短期记忆窗口：注入给大模型的最近消息条数（不含当前问题），防止历史无限膨胀
MAX_HISTORY_MESSAGES = 10


#创建共享状态(STATE)
class CompanyState(MessagesState):
    classify_result: Literal["agent_qa", "recommend"]
    current_question: str


#定义粗分类评估器的PydanticOutputParser输出格式验证
class ClassifyResult(BaseModel):
    # 定义分类结果类，继承自BaseModel
    # 使用字面量类型确保category只能是特定值之一
    classify_name: Literal['agent_qa', 'recommend'] = Field(
        # 为category字段添加描述说明
        description="分类结果，只能是agent_qa,recommend之一",
        examples=['agent_qa', 'recommend']
    )


#获取用户问题的方法：
def get_question(state: CompanyState):
    # 获取用户最新问题（只读，不删除消息，保证历史进入短期记忆）
    messages = state["messages"]

    # 从后往前找最后一个 HumanMessage
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            return messages[i].content

    # 没有找到 HumanMessage
    return " "


#创建粗分类节点
async def classify_node(state: CompanyState):
    # PydanticOutputParser:符合pydantic格式的输出解析器
    out_parser = PydanticOutputParser(pydantic_object=ClassifyResult)

    # 获取用户问题
    question = get_question(state)

    # 大模型根据问题内容进行粗分类
    # 这里需要调用大模型进行分类
    template = """
     你是AI助手请根据用户问题进行分类\n
     用户问题：{question}\n
     分类结果为：“agent_qa”，“recommend”\n
     重要规则：
     1. 只输出分类标签，不要任何解释
     2. 输出必须是小写的 agent_qa 或 recommend 之一
     examples:\n
     用户问题：我想询问/查询/查看公司的年假政策 回答： agent_qa\n
     用户问题： 给我推荐一些文章/文档/方案 回答： recommend\n
     {format_instructions}
    """

    prompt_template = PromptTemplate(
        template=template,
        input_variables=["question"],
        partial_variables={"format_instructions": out_parser.get_format_instructions()}
    )

    chain = prompt_template | qwen_llm | out_parser

    result = await chain.ainvoke({"question": question})

    return {
        "classify_result": result.classify_name,
        "current_question": question,  # 保存给后续节点使用
        "messages": state["messages"]
    }


#创建智能问答节点
async def agent_qa_node(state: CompanyState):
    # 获取用户问题
    question = state.get("current_question", "")

    if not question.strip():  # 安全处理
        return {"messages": AIMessage(content="没有获取到您的问题，请重新提问。")}

    # 取当前问题之前的最近N条对话历史作为短期记忆，注入给RAG agent
    history = state["messages"][-MAX_HISTORY_MESSAGES - 1:-1]

    # 执行订单查询rag的agent，获取结果（AIMessage）
    result = await rag_agent.run_rag_agent(question, history)

    return {"messages": [result]}


# 创建文档推荐节点
async def recommend_node(state: CompanyState, config: RunnableConfig):
    """
    推荐节点函数，根据用户问题和当前文件ID执行订单查询agent，并返回结果
    参数:
        state (CompanyState): 订单状态对象，包含当前对话的状态信息
        config (RunnableConfig): 可运行配置对象，包含可配置的参数信息
    返回:
        Command: 包含更新消息的命令对象
    """
    # 获取用户问题
    question = state.get("current_question", "")

    if not question.strip():  # 安全处理
        return {"messages": AIMessage(content="没有获取到您的问题，请重新提问。")}

    # 从config配置中获取文件名ID
    filename = config.get("configurable").get("filename_id")
    # 更新问题，添加当前文件信息
    # 将文件名信息追加到原始问题中，形成新的问题
    new_question = question + f"当前文件:{filename}"

    # 取当前问题之前的最近N条对话历史作为短期记忆，注入给推荐agent
    history = state["messages"][-MAX_HISTORY_MESSAGES - 1:-1]

    # 执行订单查询的agent，获取结果（AIMessage）
    result = await chat_agent.run_recommend_agent(new_question, history)

    return {"messages": [result]}


#创建状态图langraph关键操作（先节点后加边）


#定义条件边判断函数
def should_router(state: CompanyState):
    classify_result = state.get("classify_result")
    if classify_result == "agent_qa":
        return "agent_qa"
    else:
        return "recommend"


def create_qa_graph(checkpointer):
    """
    创建聊天状态图函数
    该函数初始化一个状态图，并添加节点和边，用于构建聊天流程的状态机

    参数:
        checkpointer: 会话记忆检查点，负责短期记忆的持久化与读取

    返回:
        编译后的状态图对象
    """
    #初始化状态图，使用CompanyState作为状态类型
    graph = StateGraph(CompanyState)

    #添加节点
    graph.add_node("classify", classify_node)
    graph.add_node("agent_qa", agent_qa_node)
    graph.add_node("recommend", recommend_node)

    #添加边
    graph.add_edge(START, "classify")
    #条件边
    graph.add_conditional_edges(
        "classify",
        should_router,
        {"agent_qa": "agent_qa", "recommend": "recommend"}
    )
    graph.add_edge("agent_qa", END)
    graph.add_edge("recommend", END)
    return graph.compile(checkpointer=checkpointer)


#初始化编译好的状态图
#单例
_graph = None
_checkpointer = None
#短期记忆数据库文件路径（项目根目录下）
_CHECKPOINT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chat_memory.db")


async def init_graph():
    global _graph, _checkpointer
    if _graph is None:
        if _checkpointer is None:
            #持久化短期记忆：以 session_id 为 thread_id 保存多轮对话，服务重启后记忆不丢失
            _checkpointer = AsyncSqliteSaver(aiosqlite.connect(_CHECKPOINT_DB))
        _graph = create_qa_graph(_checkpointer)
    return _graph


async def stream_graph(question: str, user_id: int, token: str, filename_id: str, session_id: str):
    """
    异步流式处理图结构中的对话请求
    参数:
        question (str): 用户输入的问题内容
        user_id (int): 用户的唯一标识符
        token (str): 用于标识会话的令牌
    返回:
        generator: 生成流式响应内容
    """
    # 初始化图结构
    graph = await init_graph()

    # 配置可运行参数，包括用户ID和线程ID
    config = RunnableConfig(
        configurable={
            "user_id": str(user_id),
            "thread_id": session_id,
            "filename_id": str(filename_id)
        }
    )

    # 异步遍历图结构中的事件流
    async for event in graph.astream_events(
            {"messages": [HumanMessage(content=question)]},  # 传入用户问题
            config=config,  # 使用配置参数
            version="v2"  # 指定版本为v2
    ):
        # 检查是否是聊天模型流式事件
        if event["event"] == "on_chat_model_stream":
            # 获取事件元数据中的节点信息
            node = event.get("metadata", {}).get("langgraph_node", "")
            if node in ("agent_qa", "recommend", "model"):
                content = event["data"]["chunk"].content
                if content:
                    yield content
