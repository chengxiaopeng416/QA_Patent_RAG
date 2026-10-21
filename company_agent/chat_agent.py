"""
构建agent
"""
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from company_agent.db_tools import list_table_tool, execute_sql_tool, table_schema_tool, check_sql_tool
from models.my_llm import qwen_llm

_chain = None

def get_agent():
    global _chain  # 声明使用全局变量_chain
    # 如果_chain为空，则创建chain，否则表示已经创建，直接返回_chain
    if _chain is None:  # 检查_chain是否未被初始化
        # 创建AI代理实例，配置模型、工具和系统提示
        _agent = create_agent(
            model=qwen_llm,  # 指定使用的语言模型
            tools=[list_table_tool,  # 工具列表：列出表格，看有哪些表
                   table_schema_tool,  # 工具列表：获取表格结构，看表结构
                   check_sql_tool, # 工具列表：生成 SQL,检查SQL语句
                   execute_sql_tool # 工具列表：执行SQL查询
                   ],
            # 系统提示词，定义AI助手的角色和功能
            system_prompt="""
            你是一个TEXT_TO_SQL的AI助手，
            能够根据用户的问题查询数据库并返回结果。
            在执行查询之前必须先检查SQL是否正确。
            同时如果用户问题中引用了文档，请在回答末尾附上链接，格式为：完整文档链接：http://localhost:8000/api/docstore/文件名

            重要：数据库文档有权限级别（public、internal、confidential、secret、top_secret），查询结果已按当前用户的角色和部门自动过滤。
            如果用户询问高权限级别的文档（如secret、top_secret）而查询结果为空或未出现该类文档，请回复：'该级别文档属于更高权限，您当前账号无权访问，如需查看请联系管理员授权'，
            不要回复'文件不存在'、'未入库'、'没有该文件'等误导性内容。
            """,
            # debug=True  # 启用调试模式
        )
        #提示词模版
        # chat_history：插入多轮对话历史，实现短期记忆
        prompt_template = ChatPromptTemplate.from_messages([
            MessagesPlaceholder("chat_history", optional=True), # 历史消息占位
            ("human", "{question}")
        ])
        _chain = prompt_template | _agent
    return _chain

async def run_recommend_agent(question: str, chat_history: list = None):

    """
    运行推荐代理函数，处理用户输入的问题并返回结果
    参数:
        question (str): 用户输入的问题字符串
        chat_history (list): 多轮对话历史消息列表
    返回:
        最后一条消息内容
    """
    # 获取代理实例
    chain = get_agent()  # 通过get_agent()函数获取代理实例对象
    # 调用代理处理问题，将历史消息与当前问题一起传入
    result = await chain.ainvoke({
        "question": question,
        "chat_history": chat_history or []
    })  # 使用invoke方法处理用户输入的问题，传入问题参数
    # 获取结果中的最后一条消息
    message = result["messages"][-1]  # 从结果字典中获取消息列表的最后一项
    # 返回消息内容
    return message  # 将最后一条消息内容作为函数返回值


