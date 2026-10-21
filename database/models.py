from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from utils.config import connection_string, connection_string_url
from utils.logger import setup_logger
from utils.security import hash_password

# 日志打印
logger = setup_logger(__name__)

# 创建user表
#declarative_base：创建数据表和python类之间的映射关系
Base = declarative_base()

_session = None


class User(Base):
    """
    用户表模型类
    继承自Base类，用于定义用户表的结构和字段
    """
    #定义数据表名称
    __tablename__ = 't_user'
    #定义表注释
    __table_args__ = {"comment": "用户表"}
    #定义表字段
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")  # 整型主键，自增
    username = Column(String(32), nullable=False, unique=True, comment="用户名")  # 用户名字段，32字符长度，非空且唯一
    password = Column(String(255), nullable=False, comment="密码（bcrypt加盐哈希，非明文）")  # 密码字段，255长度，用于存放bcrypt哈希
    email = Column(String(32), nullable=False, unique=True, comment="邮箱")  # 邮箱字段，32字符长度，非空且唯一
    organization = Column(String(128), comment="所属机构/公司")  # 所属机构
    role = Column(String(32), comment="角色：研究员/专利代理人/审查员/管理员")  # 用户角色
    research_field = Column(String(128), comment="研究领域")  # 研究领域
    patent_focus = Column(String(256), comment="专利关注方向（IPC分类号/技术领域）")  # 专利关注方向

    def to_dict(self):
        """
        将用户对象转换为字典格式
        返回包含所有用户字段键值对的字典
        """
        return {
            "id": self.id,
            "username": self.username,
            "password": self.password,
            "email": self.email,
            "organization": self.organization,
            "role": self.role,
            "research_field": self.research_field,
            "patent_focus": self.patent_focus
        }

class Patent(Base):
    __tablename__ = 't_patent'
    __table_args__ = {"comment": "专利文档表"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    patent_no = Column(String(64), nullable=False, unique=True, comment="专利号/申请号")
    title = Column(String(256), nullable=False, comment="专利名称")
    applicant = Column(String(128), comment="申请人/权利人")
    inventor = Column(String(256), comment="发明人")
    filing_date = Column(String(16), comment="申请日期")
    publication_date = Column(String(16), comment="公开日期")
    ipc_code = Column(String(64), comment="IPC分类号")
    abstract = Column(String(2048), comment="摘要")
    status = Column(String(32), comment="专利状态：有效/失效/审查中")
    source_file = Column(String(256), comment="源文件路径")
    user_id = Column(Integer, ForeignKey("t_user.id"), comment="上传用户ID")

    def to_dict(self):
        """
        将专利对象转换为字典格式
        """
        return {
            "id": self.id,
            "patent_no": self.patent_no,
            "title": self.title,
            "applicant": self.applicant,
            "inventor": self.inventor,
            "filing_date": self.filing_date,
            "publication_date": self.publication_date,
            "ipc_code": self.ipc_code,
            "abstract": self.abstract,
            "status": self.status,
            "source_file": self.source_file,
            "user_id": self.user_id
        }


class SearchHistory(Base):
    __tablename__ = 't_search_history'
    __table_args__ = {"comment": "检索历史表"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    user_id = Column(Integer, ForeignKey("t_user.id"), nullable=False, comment="用户ID")
    query = Column(String(512), nullable=False, comment="检索问题")
    strategy = Column(String(32), comment="检索策略：vector/bm25/hybrid/graph")
    result_count = Column(Integer, comment="检索结果数量")
    created_at = Column(DateTime, default=datetime.now, comment="检索时间")

    def to_dict(self):
        """
        将检索历史对象转换为字典格式
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "query": self.query,
            "strategy": self.strategy,
            "result_count": self.result_count,
            "created_at": self.created_at
        }


class AnalysisReport(Base):
    __tablename__ = 't_analysis_report'
    __table_args__ = {"comment": "分析报告表"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    user_id = Column(Integer, ForeignKey("t_user.id"), nullable=False, comment="用户ID")
    title = Column(String(256), nullable=False, comment="报告标题")
    report_type = Column(String(32), comment="报告类型：专利对比/领域分析/趋势总结")
    patent_list = Column(String(1024), comment="涉及专利号列表")
    content = Column(String(8192), comment="报告内容")
    created_at = Column(DateTime, default=datetime.now, comment="生成时间")

    def to_dict(self):
        """
        将分析报告对象转换为字典格式
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "report_type": self.report_type,
            "patent_list": self.patent_list,
            "content": self.content,
            "created_at": self.created_at
        }

# 初始化引擎
# 单例(进行封装)
_engine = None

# pool_size：连接池的大小，默认为5
# max_overflow：连接池中连接用完后的最大溢出数，默认为10
# pool_pre_ping：是否在每次连接使用前进行ping操作，默认为False
# pool_recycle：连接池中连接的回收时间超时回收，默认为-1，表示不回收
def init_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            connection_string,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600
        )
    return _engine

def init_session():
    global _session
    if _session is None:
        engine = init_engine()
        _session = sessionmaker(autoflush=False, autocommit=False, bind=engine)
    return _session

def init_data():
    SessionLocal = init_session()
    db: Session = SessionLocal()
    # 先检查是否已有数据
    try:
        if db.query(User).first() is not None:
            # 如果有数据，则跳过初始化
            print("[SKIP] 数据已存在，跳过初始化")
            return
        else:
            #  初始化用户表
            users = [
                User(
                    username="researcher1",
                    password=hash_password("123456"),
                    email="researcher@example.com",
                    organization="XX知识产权研究院",
                    role="研究员",
                    research_field="新能源汽车",
                    patent_focus="H01M, B60L"
                )
            ]
            db.add_all(users)
            db.commit()
            logger.info("初始化表数据启动成功")
    except Exception as e:
        #数据控制回滚到未操作
        db.rollback()
        logger.error("初始化表数据启动失败", e)
    finally:
        db.close()


# 初始化数据表
def init_tables():
    try:
        engine = init_engine()
        Base.metadata.create_all(engine)
        # 执行密码列迁移：兼容旧版明文存储
        # 1. 把 password 列宽扩到可容纳 bcrypt(60字符)；旧表是 VARCHAR(32) 放不下
        # 2. 历史明文密码就地转成 bcrypt 哈希（明文值本身还在列里，可直接哈希）
        migrate_user_password()
        logger.info("创建数据表成功")
    except Exception as e:
        logger.error("创建数据表失败", e)


def migrate_user_password():
    """轻量迁移：把 t_user.password 扩宽并把历史明文密码哈希化（幂等，可反复执行）"""
    try:
        engine = init_engine()
        with engine.begin() as conn:
            # 扩宽列（MYSQL 重复执行相同 DDL 不会报错，具备幂等性）
            conn.execute(text("ALTER TABLE t_user MODIFY password VARCHAR(255) NOT NULL COMMENT '密码（bcrypt加盐哈希，非明文）'"))
        # 把存量明文密码就地转成 bcrypt（不是 $2... 开头的一律视为历史明文）
        SessionLocal = init_session()
        db = SessionLocal()
        try:
            rows = db.query(User).all()
            changed = False
            for u in rows:
                if u.password and not u.password.startswith('$2'):
                    u.password = hash_password(u.password)
                    changed = True
            if changed:
                db.commit()
                logger.info("已将历史明文密码迁移为 bcrypt 哈希")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"密码列迁移失败（可忽略，如为全新库则无需迁移）: {e}")

# 创建数据库
def init_db():
    # 初始化数据库引擎
    engine = create_engine(
        url=connection_string_url
    )

    try:
        with engine.connect() as conn:
            conn.execute(text(
                "CREATE DATABASE IF NOT EXISTS PatentRAG_DB CHARACTER SET utf8mb4"
                )
            )
            logger.info("创建数据库成功")
    except Exception as e:
        logger.error("创建数据库失败", e)

def get_db():
    SessionLocal = init_session()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == '__main__':
    init_db()
    init_tables()
    init_data()
