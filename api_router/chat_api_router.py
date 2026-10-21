"""
Agent RAG 聊天接口：
1. GET  /api/chat/ask   SSE流式问答（JWT认证）
2. POST /api/chat/invoke 非流式问答，一次性返回答案、todo列表与引用文档
"""
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from api_router.response import ApiResponse
from database.models import User
from service.chat_service import AgentChatService
from utils.jwt_util import get_current_user

chat_router = APIRouter(prefix="/chat")


# SSE流式问答
@chat_router.get("/ask")
async def ask(query: str = Query(...), user_token: tuple[User, str] = Depends(get_current_user)):
    chat_service = AgentChatService()
    return StreamingResponse(
        chat_service.generator(query),
        media_type="text/event-stream"
    )


# 非流式问答请求体
class InvokeRequest(BaseModel):
    query: str = Field(..., min_length=1)


# 非流式问答
@chat_router.post("/invoke")
async def invoke(req: InvokeRequest, user_token: tuple[User, str] = Depends(get_current_user)):
    chat_service = AgentChatService()
    try:
        result = await chat_service.invoke(req.query)
        return ApiResponse(code=200, message="success", data=result)
    except Exception as e:
        return ApiResponse(code=500, message=f"执行失败: {str(e)[:200]}")
