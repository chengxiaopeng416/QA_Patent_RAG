"""
生成JET token
解析JWT token，验证有效性
"""
import jwt
from datetime import timedelta, datetime


from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database.models import User, get_db
from utils.config import secret_key, algorithm
from service.redis_service import RedisService


def create_token(user: User, db: Session | None = None):
    # 封装pay_load：iat 为签发时间，用于"改密后强制下线"判断
    now = datetime.now()
    pay_load = {
        "user_id": user.id,
        "username": user.username,
        "iat": int(now.timestamp()),
        "exp": now + timedelta(hours=24)
    }
    # 生成token
    token = jwt.encode(pay_load, secret_key, algorithm)
    return token


# 记录密码变更时间：之后在此时间之前签发的token全部失效
def mark_password_changed(user_id: int) -> None:
    try:
        RedisService().client.setex(
            f"auth:pwd_change:{user_id}",
            86400 * 2,  # 有效期2天（token过期时间为24小时，足够覆盖）
            int(datetime.now().timestamp())
        )
    except Exception:
        # Redis不可用时降级：放弃强制下线，保证登录能用
        pass


# 从http请求头中获取token，通过前端请求中的authorization字段中获取
http_bearer = HTTPBearer()


#验证 JWT token
def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
        db: Session = Depends(get_db)
):
    # 获取前端请求的token
    token = credentials.credentials
    if not token:
        raise HTTPException(401, "token不存在")

    pay_load = jwt.decode(token, secret_key, algorithm)

    if not pay_load:
        raise HTTPException(401, "非法token")

    username = pay_load["username"]

    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise HTTPException(401, "非法token")

    # ===== 修改密码后强制下线 =====
    # 若 token 签发时间早于用户密码的最近修改时间，则该 token 失效
    try:
        pwd_change = RedisService().client.get(f"auth:pwd_change:{user.id}")
        if pwd_change is not None:
            iat = pay_load.get("iat")
            if iat is not None and int(iat) < int(pwd_change):
                raise HTTPException(401, "密码已修改，请重新登录")
    except HTTPException:
        raise
    except Exception:
        # Redis异常时降级为放行，保证登录可用
        pass

    return user, token









































