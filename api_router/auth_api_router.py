"""
用户登录 / 注册 / 用户资料：
- 登录成功，生成jwt token，返回给前端
- 注册：校验账号唯一性后写入 t_user，供下次登录
- 获取我的资料：返回当前登录用户的所有信息
- 更新我的资料：将编辑后的信息同步更新到 t_user
"""
from fastapi import APIRouter, Depends

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api_router.response import ApiResponse
from database.models import get_db, User

from utils.jwt_util import create_token, get_current_user, mark_password_changed
from utils.security import hash_password, verify_password

auth_router = APIRouter(prefix='/auth')

#用户参数类
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=32)

#注册参数类
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=32, description="同登录校验，长度受限")
    email: str = Field(..., min_length=1, max_length=32)

#编辑资料参数类：修改个人资料需二次验证原密码
# old_password：必填，用于确认是本人操作
class UpdateProfileRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=64, description="用于二次验证的原密码")
    organization: str | None = None
    role: str | None = None
    research_field: str | None = None
    patent_focus: str | None = None
    email: str | None = None

#Depends：fastapi提供的依赖注入机制，将get_db函数返回的db对象注入到login函数中，在接口方法执行之前来执行依赖的方法
@auth_router.post('/login')
async def login(loginUser: LoginRequest, db: Session = Depends(get_db)):
    username = loginUser.username
    password = loginUser.password
    # 相当于：select * from user u where u.username = ?
    # sqlalchemy是懒加载机制，有实际的执行函数被调用时才执行sql语句
    # 如：first()：获取第一条数据
    #   scalar（）：获取第一行第一列数据
    #   all（）：获取所有数据
    #   count（）:统计数据条数
    #   delete():删除
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        return ApiResponse(code=1001, message="用户名不存在")

    # 密码校验：统一用 verify_password 校验 bcrypt 哈希
    if not verify_password(password, user.password):
        return ApiResponse(code=1002, message="密码错误")

    # 登录成功，生成jwt token，返回给前端
    token = create_token(user)

    return ApiResponse(code=200, message="登录成功", data=token)


#注册接口：校验用户名、邮箱唯一，通过后写入 t_user 表
@auth_router.post('/register')
async def register(regUser: RegisterRequest, db: Session = Depends(get_db)):
    username = regUser.username.strip()
    password = regUser.password
    email = regUser.email.strip()

    if not username or not password or not email:
        return ApiResponse(code=1003, message="用户名、密码、邮箱均不能为空")

    # 查询用户名是否已存在（t_user.username 唯一）
    exist_name = db.query(User).filter(User.username == username).first()
    if exist_name is not None:
        return ApiResponse(code=1004, message="用户名已存在")

    # 查询邮箱是否已被占用（t_user.email 唯一）
    exist_email = db.query(User).filter(User.email == email).first()
    if exist_email is not None:
        return ApiResponse(code=1005, message="该邮箱已被注册")

    # 注册成功，插入一条新用户记录（密码用 bcrypt 加盐哈希存储）
    new_user = User(username=username, password=hash_password(password), email=email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return ApiResponse(code=200, message="注册成功，请登录")


#获取当前登录用户的完整信息（编辑资料页展示用）
@auth_router.get('/me')
async def get_me(auth=Depends(get_current_user)):
    user = auth[0]
    # 去掉密码，避免明文密码返回到前端
    data = user.to_dict()
    data.pop("password", None)
    return ApiResponse(code=200, message="获取成功", data=data)


#更新当前登录用户的个人资料，同步更新到 t_user
# 修改资料前需校验原密码（二次验证），防止账号被盗后他人随意改资料
@auth_router.put('/me')
async def update_me(req: UpdateProfileRequest, auth=Depends(get_current_user), db: Session = Depends(get_db)):
    current_user = auth[0]

    # 在当前 db 会话中重新查询用户，保证写库与查库用同一会话
    target = db.query(User).filter(User.id == current_user.id).first()
    if target is None:
        return ApiResponse(code=401, message="用户不存在")

    # 二次验证：输入的原密码必须正确（校验 bcrypt 哈希）
    if not verify_password(req.old_password, target.password):
        return ApiResponse(code=1006, message="原密码错误，无法修改资料")

    # 逐字段更新：仅当前端传了非空值才覆盖，避免误清空原有数据
    if req.organization is not None:
        target.organization = req.organization
    if req.role is not None:
        target.role = req.role
    if req.research_field is not None:
        target.research_field = req.research_field
    if req.patent_focus is not None:
        target.patent_focus = req.patent_focus
    if req.email is not None:
        # 邮箱唯一性校验：避免改成和别人重复的邮箱
        other = db.query(User).filter(User.email == req.email, User.id != target.id).first()
        if other is not None:
            return ApiResponse(code=1005, message="该邮箱已被占用")
        target.email = req.email

    db.commit()

    # 返回更新后的完整资料（去掉密码）
    data = target.to_dict()
    data.pop("password", None)
    return ApiResponse(code=200, message="更新成功", data=data)


#修改密码参数类
class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=32)
    new_password: str = Field(..., min_length=1, max_length=32)


#修改密码：校验旧密码正确后，将新密码更新到 t_user，并强制该用户所有旧token下线
@auth_router.put('/password')
async def change_password(req: ChangePasswordRequest, auth=Depends(get_current_user), db: Session = Depends(get_db)):
    current_user = auth[0]

    # 在当前 db 会话中重新查出用户，保证校验与写库用同一会话
    target = db.query(User).filter(User.id == current_user.id).first()
    if target is None:
        return ApiResponse(code=401, message="用户不存在")

    # 校验旧密码是否正确（校验 bcrypt 哈希，与登录一致）
    if not verify_password(req.old_password, target.password):
        return ApiResponse(code=1006, message="原密码错误")

    # 更新为新密码（bcrypt 加盐哈希后存储）
    target.password = hash_password(req.new_password)
    db.commit()

    # 强制下线：记录本次密码变更时间，凡早于此刻签发的token全部失效
    mark_password_changed(target.id)

    return ApiResponse(code=200, message="密码修改成功，请重新登录")


#注销参数类
class DeleteAccountRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=32)


#注销账号：校验密码后删除当前用户的 t_user 记录
@auth_router.delete('/me')
async def delete_me(req: DeleteAccountRequest, auth=Depends(get_current_user), db: Session = Depends(get_db)):
    current_user = auth[0]

    target = db.query(User).filter(User.id == current_user.id).first()
    if target is None:
        return ApiResponse(code=401, message="用户不存在")

    # 校验密码，确认是本人操作
    if not verify_password(req.password, target.password):
        return ApiResponse(code=1006, message="密码错误，无法注销")

    # 先作废其token，再删除记录
    mark_password_changed(target.id)
    db.delete(target)
    db.commit()

    return ApiResponse(code=200, message="账号已注销")


#管理员：用户列表（分页 + 关键词搜索）
@auth_router.get('/users')
async def list_users(page: int = 1, page_size: int = 10, keyword: str = "", auth=Depends(get_current_user), db: Session = Depends(get_db)):
    current_user = auth[0]
    # 仅管理员可查看用户列表
    if current_user.role != "管理员":
        return ApiResponse(code=4007, message="无权限（仅管理员可查看用户列表）")

    query = db.query(User)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            User.username.like(like) | User.email.like(like) | User.organization.like(like)
        )

    total = query.count()
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    rows = (
        query.order_by(User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    # 不向外暴露密码字段
    data = []
    for u in rows:
        item = u.to_dict()
        item.pop("password", None)
        data.append(item)

    return ApiResponse(code=200, message="获取成功", data={"total": total, "records": data, "page": page})


#修改角色参数类
class UpdateRoleRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=32)


#管理员：修改指定用户的角色
@auth_router.put('/users/{user_id}/role')
async def update_role(user_id: int, req: UpdateRoleRequest, auth=Depends(get_current_user), db: Session = Depends(get_db)):
    current_user = auth[0]
    if current_user.role != "管理员":
        return ApiResponse(code=4007, message="无权限（仅管理员可操作）")

    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        return ApiResponse(code=4001, message="用户不存在")

    # 防止管理员把最后一个管理员降级锁定（此处仅提醒，实际由前端提示）
    target.role = req.role
    db.commit()
    return ApiResponse(code=200, message="角色已更新")


#管理员：删除用户
@auth_router.delete('/users/{user_id}')
async def delete_user(user_id: int, auth=Depends(get_current_user), db: Session = Depends(get_db)):
    current_user = auth[0]
    if current_user.role != "管理员":
        return ApiResponse(code=4007, message="无权限（仅管理员可操作）")

    # 不能删除自己
    if user_id == current_user.id:
        return ApiResponse(code=4008, message="不能删除当前登录的管理员账号")

    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        return ApiResponse(code=4001, message="用户不存在")

    # 作废其token后删除
    mark_password_changed(target.id)
    db.delete(target)
    db.commit()
    return ApiResponse(code=200, message="用户已删除")





