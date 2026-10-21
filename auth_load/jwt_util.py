"""
生成JET token
解析JWT token，验证有效性
"""
from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database.models import User, get_db
from utils.env_utils import secret_key, algorithm


# 创建JWT token令牌
def create_token(user: User):

    """
    创建用户认证令牌

    参数:
        user (User): 用户对象，包含用户ID和用户名等信息

    返回:
        str: 生成的JWT令牌字符串
    """
    # 封装pay_load - 构建JWT令牌的负载部分
    pay_load = {
        "user_id": user.id,          # 用户ID，用于标识用户唯一身份
        "username": user.username,    # 用户名，用于显示和识别用户
        "department": user.department,  # 部门信息，用于权限控制
        "role": user.role,  # 角色
        "exp": datetime.now() + timedelta(hours=48)  # 令牌过期时间，设置为48小时后
    }
    # 生成token - 使用JWT库和预设的密钥及算法生成令牌
    token = jwt.encode(pay_load, secret_key, algorithm=algorithm)
    return token  # 返回生成的令牌


# 从http请求头中获取token，通过前端请求中的authorization字段中获取
http_bearer = HTTPBearer()


#验证 JWT token
def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(http_bearer),  # 依赖HTTP Bearer认证方式获取凭证
        db: Session = Depends(get_db)  # 依赖数据库会话
):
    """
    获取当前认证用户的函数
    该函数通过HTTP Bearer认证方式获取用户凭证，并验证其有效性，
    然后从数据库中查询对应的用户信息
    参数:
        credentials: HTTPAuthorizationCredentials - HTTP认证凭证，包含Bearer token
        db: Session - 数据库会话对象，用于执行数据库操作
    返回:
        tuple: 包含用户对象和token的元组，格式为(user, token)
    异常:
        HTTPException: 当token不存在、token非法或用户不存在时抛出401错误
    """
    # 获取前端请求的token
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="token不存在")

    pay_load = jwt.decode(token, secret_key, algorithms=[algorithm])

    if not pay_load:
        raise HTTPException(status_code=401, detail="不正确的token")

    username = pay_load["username"]

    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise HTTPException(status_code=401, detail="非法token")

    return user, token

