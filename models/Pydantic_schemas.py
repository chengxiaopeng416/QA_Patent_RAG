"""
Pydantic请求/响应模型
"""
from datetime import datetime
import re
from typing import Optional, Any, List

from pydantic import BaseModel, Field, field_validator

# ========== 通用响应 ==========
class NeedResponseModel(BaseModel):
    """
    需求响应模型
    """
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None

# ========== 用户相关 ==========
class UserCreateRequest(BaseModel):
    """
    用户创建请求模型类，用于接收创建用户时的请求数据
    继承自BaseModel，提供数据验证和序列化功能
    """
    username: str
    email: str
    password: str = Field(min_length=6, max_length=32)
    role: str
    department: str

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('邮箱格式不正确')
        return v

class UserLoginRequest(BaseModel):
    """
    用户登录请求模型类，用于接收用户登录时的请求数据
    继承自BaseModel，提供数据验证和序列化功能
    """
    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=32)

class UserTokenResponse(BaseModel):
    """
    用户登录响应模型类，用于返回用户登录后的token信息
    继承自BaseModel，提供数据验证和序列化功能
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    """
    用户响应模型类，用于返回用户信息
    继承自BaseModel，提供数据验证和序列化功能
    """
    id: int
    username: str
    email: str
    department: str
    role: str
    created_at: Optional[datetime] = None

# ========== 文档相关 ==========
class DocumentCreateRequest(BaseModel):
    """上传文档"""
    filename: str
    permission: str = Field(default="internal")  # public/internal/confidential/secret
    department: str
    tags: List[str] = []

class DocumentResponse(BaseModel):
    """文档信息返回"""
    doc_id: int
    filename: str
    permission: str
    department: str
    tags: List[str]
    status: str
    uploader_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ========== 对话历史相关 ==========
class ChatRequest(BaseModel):
    """发送问题"""
    question: str
    session_id: Optional[str] = None  # 没有则新建会话

class ChatResponse(BaseModel):
    """问答返回"""
    session_id: str
    answer: str
    citations: Optional[List[dict]] = None

class ChatHistoryResponse(BaseModel):
    """对话历史列表"""
    session_id: str
    role: str
    content: str
    citations: Optional[List[dict]] = None
    created_at: Optional[datetime] = None


# ========== 操作日志相关 ==========
class OperationLogResponse(BaseModel):
    """操作日志返回"""
    id: int
    user_id: int
    action: str
    target: Optional[str] = None
    detail: str
    ip_address: str
    created_at: Optional[datetime] = None
