import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from api_router.auth_router import auth_router
from api_router.chat_router import chat_router
from api_router.docstore_router import docstore_router
from api_router.recommend_router import recommend_router
from database.models import init_db, init_data, init_tables
from utils.logger import setup_logger

logger = setup_logger(__name__)


#在系统启动时创建数据库(如有足够权限)
#@asynccontextmanager：异步上下文管理器，提交给fastapi，在系统fastapi启动时执行
# contextmanager：同步上下文管理器

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        init_tables()
        try:
            init_data()
        except:
            pass
    except Exception as e:
        logger.error("数据库初始化失败", e)
        raise Exception("数据库初始化失败", e)
    yield


#api调用窗口（命令：fastapi dev）
app = FastAPI(lifespan=lifespan)

# RAG回答里的文档链接走带鉴权的 /api/docstore 路由（见 docstore_router.py）
# 配置 CORS，允许跨域配置
# allow_origins: 允许请求源跨域访问，https://localhost:8080等等。“*”表示允许所有请求源
# allow_credentials: 是否允许请求携带凭证（认证信息）（如cookies）
# allow_methods: 允许的请求方法，如GET、POST、PUT、DELETE等
# allow_headers: 允许请求携带的头部信息
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth_router, prefix="/api")

app.include_router(chat_router, prefix="/api")

app.include_router(recommend_router, prefix="/api")

app.include_router(docstore_router, prefix="/api")
