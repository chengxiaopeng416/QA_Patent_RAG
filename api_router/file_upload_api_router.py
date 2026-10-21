"""
文件上传，创建向量数据库索引

【我新加的功能】：
1. 查重：先按文件名去 t_patent 表查一遍，已存在就直接返回"已存在该专利文档"，
   不再重复建索引（原版会报 resource_already_exists_exception / 重复入库）。
2. 解析 .md 元数据：从专利文档里提取 申请人/发明人/摘要/状态/标题 存进数据库，
   这样前端"详情"页才能显示（原版这些字段存的全是空）。
3. 重复上传时补全字段：老记录缺失的字段，重复上传时自动填上。
"""
import os

from fastapi import APIRouter, UploadFile, File, Depends

from PA_RAG_indexer.total_rag_index import create_index
from api_router.response import ApiResponse
from database.models import User, Patent, get_db
from service.doc_service import DocService

from utils.jwt_util import get_current_user
from utils.logger import setup_logger

file_upload_router = APIRouter(prefix="/admin")

logger = setup_logger(__name__)

@file_upload_router.post("/upload")
async def upload_file(
        file: UploadFile = File(...),
        vector_delete_flag: bool = False,
        bm25_delete_flag: bool = False,
        neo4j_delete_flag: bool = False,
        user_token: tuple[User, str] = Depends(get_current_user)
):
    try:
        file_name = file.filename

        # ===== 查重：判断该专利文档是否已上传过 =====
        # 先用"文件名"去 t_patent 表里找，找到了说明重复上传
        db = next(get_db())
        try:
            exists = db.query(Patent).filter(Patent.patent_no == file_name).first()
        finally:
            db.close()
        if exists is not None:
            # ===== 重复上传：补全之前缺失的字段（申请人/发明人/摘要/状态） =====
            # 老的记录上传时没有解析 .md 里的字段，这里读文件把空字段填上
            meta = DocService.parse_patent_meta(os.path.join("tmp_upload", file_name))
            updated = DocService.complete_patent(
                db=next(get_db()),
                patent_id=exists.id,
                applicant=meta.get("applicant"),
                inventor=meta.get("inventor"),
                abstract=meta.get("abstract"),
                status=meta.get("status"),
            )
            return ApiResponse(
                code=200,
                message="已存在该专利文档" + ("，已补全详情字段" if updated else "")
            )

        # 创建保存文件到临时目录，如该目录已存在则不重复创建
        dir_path = "tmp_upload"
        os.makedirs(dir_path, exist_ok=True)

        #读取file中的内容
        content = await file.read()

        # 将上传文件的内容写入到临时文件中
        file_path = os.path.join(dir_path, file_name)

        with open(file_path, "wb") as f:
            f.write(content)

        # 解析 .md 里的申请人/发明人/摘要/状态，存进数据库
        meta = DocService.parse_patent_meta(file_path)

        create_index(
            file_path,
            vector_delete_flag=vector_delete_flag,
            bm25_delete_flag=bm25_delete_flag,
            neo4j_delete_flag=neo4j_delete_flag
        )
        user = user_token[0]
        DocService.save_patent(
            db=next(get_db()),
            patent_no=file_name,
            title=meta.get("title") or file_name,
            user_id=user.id,
            applicant=meta.get("applicant"),
            inventor=meta.get("inventor"),
            abstract=meta.get("abstract"),
            status=meta.get("status"),
            source_file=file_path
        )

        return ApiResponse(code=200, message="文件上传,创建索引成功")
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        return ApiResponse(code=500, message=f"上传失败: {str(e)[:200]}")




































