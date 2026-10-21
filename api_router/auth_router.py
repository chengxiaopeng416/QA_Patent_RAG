"""
用户登录：
登录成功，生成jwt token，返回给前端
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth_load.jwt_util import create_token
from auth_load.password_util import verify_password
from database.models import get_db, User
from models.Pydantic_schemas import NeedResponseModel

auth_router = APIRouter(prefix='/auth')

#用户参数类
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=32)


#Depends：fastapi提供的依赖注入机制，将get_db函数返回的db对象注入到login函数中，在接口方法执行之前来执行依赖的方法
@auth_router.post('/login')
async def login(loginUeser: LoginRequest, db: Session = Depends(get_db)):
    username = loginUeser.username
    password = loginUeser.password
    # 相当于：select * from user u where u.username = ?
    # sqlalchemy是懒加载机制，有实际的执行函数被调用时才执行sql语句
    # 如：first()：获取第一条数据
    #   scalar（）：获取第一行第一列数据
    #   all（）：获取所有数据
    #   count（）:统计数据条数
    #   delete():删除
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        return NeedResponseModel(code=1001, message="用户名不存在")
    if not verify_password(password, user.password):
        return NeedResponseModel(code=1002, message="密码错误")

    # 登录成功，生成jwt token，返回给前端
    token = create_token(user)

    return NeedResponseModel(code=200, message="登录成功", data=token)
