"""
专利文档管理服务
作用：负责对"专利记录"做增删改查（就像管理一个专利文件柜）
"""


# 引入数据库会话（相当于拿到数据库的"操作权限"）
from sqlalchemy.orm import Session

# 引入 Patent 模型（定义了 t_patent 这张表长什么样）
from database.models import Patent

# 引入日志工具（用来在控制台打印"做了什么事"）
from utils.logger import setup_logger

# 创建日志对象
logger = setup_logger(__name__)


class DocService:
    """文档服务类：所有关于专利记录的操作都写在这里"""

    # ==================== 解析专利元数据（申请人/发明人/摘要/状态） ====================
    # 比喻：从专利的 md 原始文件里"抠"出关键信息，单独存到数据库，
    #       这样前端详情页才能直接显示，不用每次重读文件
    # .md 里的字段格式长这样：
    #   **申请人**：中国科学院深圳先进技术研究院
    #   **发明人**：郭子豪、廖思思、牛奔
    #   **摘要**：涉及……
    #   **状态**：审查中
    @staticmethod
    def parse_patent_meta(file_path: str) -> dict:
        meta = {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"读取文件失败，无法解析专利字段: {file_path} - {e}")
            return meta

        # 支持两种写法："**标题**：内容" 或 "**标题**： 内容"（中间可能有空格）
        import re
        for field in ["申请人", "发明人", "摘要", "状态"]:
            match = re.search(rf"\*\*{field}\*\*\s*[:：]\s*(.+)", content)
            if match:
                # 取到该行内容，去掉行尾可能的换行符
                value = match.group(1).strip()
                # 中文关键词 -> 英文列名
                meta_key = {
                    "申请人": "applicant",
                    "发明人": "inventor",
                    "摘要": "abstract",
                    "状态": "status",
                }[field]
                meta[meta_key] = value

        # 顺便解析标题："### 标题内容"
        title_match = re.search(r"^#+\s+(.+)$", content, re.MULTILINE)
        if title_match:
            meta["title"] = title_match.group(1).strip()
        return meta

    # ==================== 保存一条专利记录 ====================
    # 比喻：往文件柜里放一份新的专利文件
    @staticmethod
    def complete_patent(db: Session, patent_id: int,
                        applicant: str = None, inventor: str = None,
                        abstract: str = None, status: str = None) -> bool:
        """补全一条已存在专利记录的元数据字段（重复上传时会用到）。"""
        patent = db.query(Patent).filter(Patent.id == patent_id).first()
        if patent is None:
            return False
        changed = False
        # 只在"原来为空"的情况下填充，避免覆盖现有数据
        if applicant and not patent.applicant:
            patent.applicant = applicant
            changed = True
        if inventor and not patent.inventor:
            patent.inventor = inventor
            changed = True
        if abstract and not patent.abstract:
            patent.abstract = abstract
            changed = True
        if status and not patent.status:
            patent.status = status
            changed = True
        if changed:
            db.commit()
            logger.info(f"专利记录字段补全成功: patent_id={patent_id}")
        return changed

    # ==================== 保存一条专利记录 ====================
    # 比喻：往文件柜里放一份新的专利文件
    @staticmethod
    def save_patent(db: Session, patent_no: str, title: str, user_id: int,
                    applicant: str = None, inventor: str = None,
                    filing_date: str = None, publication_date: str = None,
                    ipc_code: str = None, abstract: str = None,
                    status: str = None, source_file: str = None) -> Patent:
        # 创建一个 Patent 对象（就像填一张专利登记表）
        patent = Patent(
            patent_no=patent_no,          # 专利号，比如 "CN202410123456.7"
            title=title,                  # 专利名称
            applicant=applicant,          # 谁申请的
            inventor=inventor,            # 谁发明的
            filing_date=filing_date,      # 什么时候申请的
            publication_date=publication_date,  # 什么时候公开的
            ipc_code=ipc_code,            # IPC分类号（专利的"分类标签"）
            abstract=abstract,            # 摘要（专利的简介）
            status=status,                # 状态：有效/失效/审查中
            source_file=source_file,      # 原始文件存在哪里
            user_id=user_id               # 是哪个用户上传的
        )
        # 把这张"登记表"交给数据库保管
        db.add(patent)
        # 确认保存（类似点"提交"按钮）
        db.commit()
        # 刷新一下，让数据库把自动生成的 id 回填给我们
        db.refresh(patent)
        # 打印日志：告诉后台"成功保存了一条专利"
        logger.info(f"专利记录保存成功: {patent_no}")
        return patent

    # ==================== 分页查询专利列表 ====================
    # 比喻：打开文件柜，按顺序翻看里面的专利文件，每次只看10份
    @staticmethod
    def list_patents(db: Session, user_id: int, page: int = 1, page_size: int = 10) -> dict:
        # 先找出这个用户上传的所有专利（相当于数一数文件柜里有多少份）
        query = db.query(Patent).filter(Patent.user_id == user_id)
        # total = 文件总份数
        total = query.count()
        # 按照 id 从大到小排（最新的排前面），然后截取第 page 页的 page_size 条
        # 比喻：翻到第几页，每页看几份
        records = query.order_by(Patent.id.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()
        # 返回一个字典：总共多少份、当前第几页、每页几份、这一页的数据
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            # to_dict() 把每条记录变成字典，方便返回给前端
            "records": [p.to_dict() for p in records]
        }

    # ==================== 查询单条专利详情 ====================
    # 比喻：从文件柜里找到某一份特定的专利文件，打开看里面的内容
    @staticmethod
    def get_patent(patent_id: int, db: Session) -> dict | None:
        # 根据 id 去数据库里找这条专利
        patent = db.query(Patent).filter(Patent.id == patent_id).first()
        # 如果没找到，返回 None（表示"没有这份文件"）
        if patent is None:
            return None
        # 找到了，把专利信息转成字典返回
        return patent.to_dict()

    # ==================== 删除一条专利 ====================
    # 比喻：从文件柜里抽出一份专利文件，扔掉，然后把柜子整理一下
    @staticmethod
    def delete_patent(patent_id: int, db: Session) -> dict:
        # 先根据 id 找到要删除的专利
        patent = db.query(Patent).filter(Patent.id == patent_id).first()
        # 没找到就告诉调用方："不存在这份文件"
        if patent is None:
            return {"success": False, "msg": "专利记录不存在"}

        # 记住专利号和文件路径（删除后就找不到了）
        patent_no = patent.patent_no
        source_file = patent.source_file

        # 从数据库里删掉这条记录
        db.delete(patent)
        # 确认删除
        db.commit()

        # 如果之前上传过原始文件，也把它从硬盘上删掉
        if source_file:
            import os
            if os.path.exists(source_file):
                os.remove(source_file)

        # 打印日志
        logger.info(f"专利记录已删除: {patent_no}")

        # 返回结果，特别提醒：向量索引（Chroma/ES/Neo4j 里的数据）没有删
        # 因为当前索引没有记录"这条数据属于哪篇专利"，没法精确删除
        return {
            "success": True,
            "msg": f"专利 {patent_no} 已删除，向量索引需手动重建"
        }