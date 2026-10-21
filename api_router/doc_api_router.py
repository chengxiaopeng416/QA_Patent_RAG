"""
专利文档管理接口（路由层）
作用：定义"前端可以通过哪个网址来管理专利"
比如：查看专利列表、看某篇专利详情、删除某篇专利

路由就是"地址"，比如：
  GET  /api/docs       → 查看专利列表
  GET  /api/docs/123   → 查看 id=123 的专利详情
  DELETE /api/docs/123 → 删除 id=123 的专利
"""


# 引入 FastAPI 的路由、依赖注入、查询参数工具
from fastapi import APIRouter, Depends, Query

# 引入数据库会话（用来连接数据库）
from sqlalchemy.orm import Session

# 引入统一响应格式（每个接口返回的数据都套上 code + message + data）
from api_router.response import ApiResponse

# 引入数据库模型：User（用户表）、get_db（获取数据库连接的函数）
from database.models import User, get_db

# 引入我们刚写的专利管理服务（所有业务逻辑都在 DocService 里）
from service.doc_service import DocService

# 引入 JWT 鉴权工具（验证用户是否登录）
from utils.jwt_util import get_current_user

# 创建一个路由对象，prefix="/docs" 表示这个模块下所有接口的地址都以 /docs 开头
doc_router = APIRouter(prefix="/docs")


# ==================== GET /api/docs → 专利列表 ====================
# 比喻：前端说"我要看我的专利列表"，后端就去数据库里翻，把结果返回
@doc_router.get("")
async def list_patents(
        # page：第几页，默认第1页，最小是1
        page: int = Query(1, ge=1),
        # page_size：每页看几条，默认10条，最小1条，最大100条
        page_size: int = Query(10, ge=1, le=100),
        # Depends(get_current_user)：先验证 JWT token，通过了才执行这个函数
        # user_token 是一个元组：(User对象, token字符串)
        user_token: tuple[User, str] = Depends(get_current_user),
        # Depends(get_db)：自动获取数据库连接，用完自动关闭
        db: Session = Depends(get_db)
):
    # 从 user_token 里取出当前登录的用户对象
    user = user_token[0]
    # 调用服务层的方法，查出这个用户的专利列表
    result = DocService.list_patents(db, user.id, page, page_size)
    # 把结果套上统一格式返回给前端
    return ApiResponse(code=200, message="success", data=result)


# ==================== GET /api/docs/{patent_id} → 专利详情 ====================
# 比喻：前端说"我要看第123号专利的详细信息"，后端就去数据库里找，找到了就返回
@doc_router.get("/{patent_id}")
async def get_patent(
        # patent_id：从网址里提取的专利id，比如 /api/docs/123 中的 123
        patent_id: int,
        user_token: tuple[User, str] = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # 调用服务层，根据 id 去数据库里找这条专利
    result = DocService.get_patent(patent_id, db)
    # 如果没找到（返回 None），就告诉前端"专利不存在"
    if result is None:
        return ApiResponse(code=4004, message="专利不存在")
    # 找到了就返回专利详情
    return ApiResponse(code=200, message="success", data=result)


# ==================== DELETE /api/docs/{patent_id} → 删除专利 ====================
# 比喻：前端说"帮我把第123号专利扔掉"，后端就去数据库里删掉它
@doc_router.delete("/{patent_id}")
async def delete_patent(
        patent_id: int,
        user_token: tuple[User, str] = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # 调用服务层执行删除
    result = DocService.delete_patent(patent_id, db)
    # 如果删除失败（比如专利不存在），返回错误提示
    if not result["success"]:
        return ApiResponse(code=4004, message=result["msg"])
    # 删除成功，返回成功提示
    return ApiResponse(code=200, message=result["msg"])