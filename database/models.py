"""
创建order_assistant_db数据库
在库中创建t_user，t_order，t_order_items，t_logistic
造假数据进行初始化（孤立系统）
"""
from datetime import datetime, timedelta

from sqlalchemy import Integer, String, Column, DATETIME, JSON, ForeignKey, Text, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from auth_load.password_util import hash_password
from utils.env_utils import connection_string
from utils.logger import setup_logger

# 日志打印
logger = setup_logger(__name__)

# 创建user表
#declarative_base：创建数据表和python类之间的映射关系
Base = declarative_base()


class User(Base):
    """
    用户表模型类
    继承自Base类，用于定义用户表的结构和字段
    """
    # 定义数据表名称
    __tablename__ = 't_user'
    # 定义表注释
    __table_args__ = {"comment": "用户表"}
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")  # 整型主键，自增
    username = Column(String(32), nullable=False, unique=True, comment="用户名")  # 用户名字段，非空且唯一
    password = Column(String(128), nullable=False, comment="密码")  # 密码字段，非空
    email = Column(String(128), nullable=False, unique=True, comment="邮箱")  # 邮箱字段，非空且唯一
    role = Column(String(16), nullable=False, comment="角色")  # 角色字段
    department = Column(String(32), nullable=False, comment="部门")  # 部门字段
    created_at = Column(DATETIME, default=datetime.now, comment="创建时间")  # 创建时间字段,非空

    def to_dict(self):
        """
                将用户对象转换为字典格式
                返回包含所有用户字段键值对的字典
                """
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "department": self.department,
            "created_at": self.created_at
        }


class Document(Base):
    """
    文档表模型类
    继承自Base类，用于定义文档表的结构和字段
    """
    # 定义数据表名称
    __tablename__ = 't_document'
    # 定义表注释
    __table_args__ = {"comment": "文档表"}
    doc_id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")  # 整型主键，自增
    filename = Column(String(256), nullable=False, comment="文件名")  # 文件名字段，非空且唯一
    permission = Column(String(16), nullable=False, comment="权限")  # 权限字段,权限控制核心
    department = Column(String(32), nullable=False, comment="部门")  # 部门字段,部门隔离核心
    tags = Column(JSON, nullable=False, default=list, comment="标签")  # 标签字段,推荐和分类用
    status = Column(String(16), nullable=False, comment="状态")  # 状态字段,知识生命周期管理
    uploader_id = Column(Integer, ForeignKey('t_user.id'), nullable=False, comment="上传者ID")  # 上传者ID字段
    created_at = Column(DATETIME, default=datetime.now, comment="创建时间")  # 创建时间字段
    updated_at = Column(DATETIME, default=datetime.now, nullable=True, comment="更新时间")  # 更新时间字段

    def to_dict(self):
        """
                将文档对象转换为字典格式
                返回包含所有文档字段键值对的字典
                """
        return {
            "doc_id": self.doc_id,  # 文档ID
            "filename": self.filename,  # 文件名
            "permission": self.permission,  # 权限
            "department": self.department,  # 部门
            "tags": self.tags,  # 标签
            "status": self.status, # 状态
            "uploader_id": self.uploader_id,  # 上传者ID
            "created_at": self.created_at,  # 创建时间
            "updated_at": self.updated_at  # 更新时间
        }

class ChatHistory(Base):
    """
    对话历史表模型类
    继承自Base类，用于定义对话历史表的结构和字段
    """
    # 定义数据表名称
    __tablename__ = 't_chat_history'
    # 定义表注释
    __table_args__ = {"comment": "对话历史表"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")  # 整型主键，自增
    session_id = Column(String(128), nullable=False, comment="会话ID")  # 会话ID字段，非空
    user_id = Column(Integer, ForeignKey('t_user.id'), nullable=False, comment="用户ID")  # 用户ID字段，整型，非空
    role = Column(String(16), nullable=False, comment="角色")  # 角色字段，非空
    content = Column(Text, nullable=False, comment="内容")  # 内容字段，非空
    citations = Column(JSON, nullable=True, comment="引用")
    created_at = Column(DATETIME, default=datetime.now, comment="创建时间")  # 创建时间字段

    def to_dict(self):
        """
                将对话历史对象转换为字典格式
                返回包含所有对话历史字段键值对的字典
                """
        return {
            "id": self.id,# 对话历史ID
            "session_id": self.session_id,  # 会话ID
            "user_id": self.user_id,  # 用户ID
            "role": self.role,  # 角色
            "content": self.content,  # 内容
            "citations": self.citations,  # 引用
            "created_at": self.created_at  # 创建时间
        }


class OperationLog(Base):
    """
    操作日志表模型类
    继承自Base类，用于定义操作日志表的结构和字段
    """
    # 定义数据表名称
    __tablename__ = 't_operation_log'
    # 定义表注释
    __table_args__ = {"comment": "操作日志表"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")  # 整型主键，自增
    user_id = Column(Integer, ForeignKey('t_user.id'), nullable=False, comment="用户ID")  # 用户ID字段，整型，非空
    action = Column(String(32), nullable=False, comment="操作")  # 操作字段,非空
    target = Column(String(128), comment="目标")
    detail = Column(Text, nullable=False, comment="详情")  # 详情字段，非空
    ip_address = Column(String(64), nullable=False, comment="IP地址")  # IP地址字段，非空
    created_at = Column(DATETIME, default=datetime.now, comment="创建时间")  # 创建时间字段

    def to_dict(self):
        """
                将操作日志对象转换为字典格式
                返回包含所有操作日志字段键值对的字典
                """
        return {
            "id": self.id,  # 操作日志ID
            "user_id": self.user_id,  # 用户ID
            "action": self.action,  # 操作
            "target": self.target,  # 目标
            "detail": self.detail,  # 详情
            "ip_address": self.ip_address,  # IP地址
            "created_at": self.created_at  # 创建时间
        }
# 初始化引擎
# 单例(进行封装)
_engine = None


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

# 初始化数据库的Session会话
# sessionmaker: 会话的工厂函数，每调用一次就会产生一个新会话
# autoflush: 控制是否刷新的开关(True,False)
# ——————————为True表示加载已修改但未提交的数据（常用）
# ——————————为False表示不刷新
# autocommit: 控制数据是否自动提交的开关(True,False)，方便数据进行回滚
# 单例(进行封装)
_session = None


def init_session():
    global _session
    if _session is None:
        engine = init_engine()
        _session = sessionmaker(autoflush=False, autocommit=False, bind=engine)
    return _session


# 初始化数据表
def init_tables():
    try:
        engine = init_engine()
        Base.metadata.create_all(engine)
        logger.info("创建数据表成功")
    except Exception as e:
        logger.error("创建数据表失败: %s", e)

#造假数据
def init_data():
    engine = init_engine()
    Session = init_session()
    db = Session()
    if db.query(User).first() is not None:
        print("[SKIP] 数据已存在，跳过初始化")
        return

    try:
        # ========== 1. 插入3个用户 ==========
        users = [
            User(
                username="admin",
                password=hash_password("123456"),  # 123456
                email="admin@company.com",
                role="super_admin",
                department="技术部"
            ),
            User(
                username="wangwu",
                password=hash_password("123456"),  # 123456
                email="wangwu@company.com",
                role="manager",
                department="技术部"
            ),
            User(
                username="zhangsan",
                password=hash_password("123456"),
                email="zhangsan@company.com",
                role="member",
                department="技术部"
            ),
            User(
                username="lisi",
                password=hash_password("123456"),
                email="lisi@company.com",
                role="guest",
                department="市场部"
            ),
        ]
        db.add_all(users)
        db.flush()  # 刷新获取id
        print(f"[OK] 插入 {len(users)} 个用户")

        # ========== 2. 插入10篇文档 ==========
        documents = [
            Document(
                filename="员工手册2024.pdf",
                permission="public",
                department="人事部",
                tags=["人事", "制度", "员工手册"],
                status="active",
                uploader_id=users[0].id
            ),
            Document(
                filename="技术架构设计.docx",
                permission="internal",
                department="技术部",
                tags=["技术", "架构", "设计文档"],
                status="active",
                uploader_id=users[1].id
            ),
            Document(
                filename="Q3财务报告.xlsx",
                permission="confidential",
                department="财务部",
                tags=["财务", "报告", "Q3"],
                status="active",
                uploader_id=users[0].id
            ),
            Document(
                filename="产品需求文档PRD.pdf",
                permission="internal",
                department="产品部",
                tags=["产品", "需求", "PRD"],
                status="active",
                uploader_id=users[1].id
            ),
            Document(
                filename="市场推广方案.pptx",
                permission="internal",
                department="市场部",
                tags=["市场", "推广", "方案"],
                status="active",
                uploader_id=users[2].id
            ),
            Document(
                filename="Python编码规范.md",
                permission="public",
                department="技术部",
                tags=["技术", "Python", "规范", "编码标准"],
                status="active",
                uploader_id=users[1].id
            ),
            Document(
                filename="客户合作协议模板.docx",
                permission="confidential",
                department="商务部",
                tags=["商务", "合同", "模板"],
                status="active",
                uploader_id=users[0].id
            ),
            Document(
                filename="服务器运维手册.pdf",
                permission="secret",
                department="技术部",
                tags=["运维", "服务器", "手册"],
                status="active",
                uploader_id=users[1].id
            ),
            Document(
                filename="新员工入职培训.pptx",
                permission="public",
                department="人事部",
                tags=["人事", "培训", "入职"],
                status="active",
                uploader_id=users[0].id
            ),
            Document(
                filename="2025年战略规划.docx",
                permission="top_secret",
                department="管理层",
                tags=["战略", "规划", "2025"],
                status="active",
                uploader_id=users[0].id
            ),
        ]
        db.add_all(documents)
        db.flush()
        print(f"[OK] 插入 {len(documents)} 篇文档")

        # ========== 3. 插入对话历史 ==========
        now = datetime.now()
        chat_histories = [
            ChatHistory(
                session_id="sess_001",
                user_id=users[1].id,
                role="user",
                content="年假有多少天？",
                citations=None,
                created_at=now - timedelta(hours=2)
            ),
            ChatHistory(
                session_id="sess_001",
                user_id=users[1].id,
                role="assistant",
                content="根据员工手册规定，正式员工享有5-15天年假，具体天数根据工龄计算。",
                citations=[{"filename": "员工手册2024.pdf", "content": "年假制度..."}],
                created_at=now - timedelta(hours=2, seconds=3)
            ),
            ChatHistory(
                session_id="sess_002",
                user_id=users[2].id,
                role="user",
                content="报销流程是什么？",
                citations=None,
                created_at=now - timedelta(hours=1)
            ),
            ChatHistory(
                session_id="sess_002",
                user_id=users[2].id,
                role="assistant",
                content="报销流程：1. 填写报销单 2. 部门主管审批 3. 财务审核 4. 打款到账。详细流程请参考员工手册。",
                citations=[{"filename": "员工手册2024.pdf", "content": "报销流程..."}],
                created_at=now - timedelta(hours=1, seconds=3)
            ),
            ChatHistory(
                session_id="sess_003",
                user_id=users[0].id,
                role="user",
                content="帮我写一份周报",
                citations=None,
                created_at=now - timedelta(minutes=30)
            ),
            ChatHistory(
                session_id="sess_003",
                user_id=users[0].id,
                role="assistant",
                content="本周完成了服务器运维手册的更新，处理了3个线上问题，参与了Q3财务报告评审。",
                citations=None,
                created_at=now - timedelta(minutes=30, seconds=3)
            ),
        ]
        db.add_all(chat_histories)
        db.flush()
        print(f"[OK] 插入 {len(chat_histories)} 条对话历史")

        # ========== 4. 插入操作日志 ==========
        operation_logs = [
            OperationLog(
                user_id=users[0].id,
                action="upload",
                target="员工手册2024.pdf",
                detail="上传文档成功",
                ip_address="192.168.1.100",
                created_at=now - timedelta(days=7)
            ),
            OperationLog(
                user_id=users[1].id,
                action="upload",
                target="技术架构设计.docx",
                detail="上传文档成功",
                ip_address="192.168.1.101",
                created_at=now - timedelta(days=5)
            ),
            OperationLog(
                user_id=users[2].id,
                action="query",
                target=None,
                detail="查询：报销流程是什么？",
                ip_address="192.168.1.102",
                created_at=now - timedelta(hours=1)
            ),
        ]
        db.add_all(operation_logs)
        db.flush()
        print(f"[OK] 插入 {len(operation_logs)} 条操作日志")

        # 提交所有数据
        db.commit()
        print("\n[SUCCESS] 所有测试数据初始化完成！")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] 初始化失败: {e}")
        raise
    finally:
        db.close()

# 创建数据库
def init_db():
    # 初始化数据库引擎
    engine = create_engine(
        url='mysql+pymysql://root:Cxp050720.@localhost:3306'
    )

    try:
        with engine.connect() as conn:
            conn.execute(text(
                "CREATE DATABASE IF NOT EXISTS company_commend_db CHARACTER SET utf8mb4"
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















