from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from api_router.auth_api_router import auth_router
from api_router.chat_api_router import chat_router
from api_router.doc_api_router import doc_router

from api_router.file_upload_api_router import file_upload_router
from database.models import init_db, init_data, init_tables
from utils.logger import setup_logger

logger = setup_logger(__name__)
#api调用窗口（命令：fastapi dev）
app = FastAPI()


#在系统启动时创建数据库(如有足够权限)
#@asynccontextmanager：异步上下文管理器，提交给fastapi，在系统fastapi启动时执行
# contextmanager：同步上下文管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        init_tables()
        init_data()
    except Exception as e:
        raise Exception("数据库初始化失败", e)
    yield




logger.info("FastAPI启动成功")

# 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(file_upload_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(doc_router, prefix="/api")
