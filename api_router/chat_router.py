import json

from fastapi import APIRouter, Query, Depends
from starlette.responses import StreamingResponse

from auth_load.jwt_util import get_current_user
from database.models import User
from graph.agent_graph import stream_graph

chat_router = APIRouter(prefix="/chat")


async def _generate(question, user_id, token, filename_id, session_id):
    """
    异步生成响应流
    Args:
        question: 用户输入的问题
        user_id: 用户标识ID
        token: 用户访问令牌
        filename_id: 文件名标识符
    Yields:
        str: 每个处理后的JSON格式字符串，后跟换行符
    异常处理:
        捕获所有异常并以错误信息JSON格式返回
    """
    try:
        # 遍历流式生成的结果
        async for chunk in stream_graph(question, user_id, token, filename_id, session_id):
            # 将每个处理结果转换为JSON格式并添加换行符
            yield json.dumps({"c": chunk}) + "\n"
    except Exception as e:
        # 捕获异常并返回错误信息
        yield json.dumps({"err": str(e)}) + "\n"


@chat_router.get("/stream")
async def stream_chat(question: str = Query(...), user_token: tuple[User, str] = Depends(get_current_user),
                      filename_id: str = Query(""), session_id: str = Query("")):
    user, token = user_token

    user_id = user.id
    return StreamingResponse(_generate(question, user_id, token, filename_id, session_id))
