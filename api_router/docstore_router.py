"""
文档访问接口
GET /api/docstore/{filename}   校验登录与文档权限后返回文件内容
替代无鉴权的静态文件挂载，防止未授权访问保密文档
"""
import os

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from auth_load.jwt_util import get_current_user
from auth_load.permission import filter_accessible_documents
from database.models import Document, User, get_db

docstore_router = APIRouter(prefix="/docstore")

# docs 目录：项目根目录/docs
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")


@docstore_router.get("/{filename}")
async def get_doc(filename: str,
                  current_user: tuple[User, str] = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """按用户权限返回文档内容"""
    user, token = current_user

    # 防止路径穿越：只允许文件名本身
    safe_name = os.path.basename(filename)

    # 计算用户可见文档集合（去扩展名）
    docs = db.query(Document).filter(Document.status == "active").all()
    allowed = filter_accessible_documents(user, docs)
    allowed_names = {os.path.splitext(d.filename)[0] for d in allowed}

    if os.path.splitext(safe_name)[0] not in allowed_names:
        return JSONResponse({"detail": "无权访问该文档"}, status_code=403)

    path = os.path.join(DOCS_DIR, safe_name)
    if not os.path.isfile(path):
        return JSONResponse({"detail": "文件不存在"}, status_code=404)

    return FileResponse(path, filename=safe_name)
