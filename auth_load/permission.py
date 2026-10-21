"""
4级角色权限体系 + 文档级权限检查 + 部门隔离
"""
from database.models import User, Document

role_levels = {
    'super_admin': 4,  # 超级管理员
    'manager': 3,  # 管理员
    'member': 2,  # 成员
    'guest': 1  # 访客
}

doc_permission_levels = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "secret": 3,
    "top_secret": 4
}


def get_role_levels(role: str) -> int:
    """获取角色对应的权限层级"""
    # get(role, 0)的意思是：role在字典里存在 → 返回对应等级
    #                     role不存在 → 返回0（兜底默认值）
    return role_levels.get(role, 0)


def can_access_document(user: User, document: Document) -> bool:
    """
    判断用户是否有权访问某文档
    规则：
    1. 超级管理员可访问所有文档
    2. 部门管理员可访问本部门所有文档
    3. 其他角色：角色层级 >= 文档权限级别 且 同部门或文档为公开
    """
    user_level = get_role_levels(user.role)
    doc_level = doc_permission_levels.get(document.permission, 0)

    # 超级管理员：全部放行
    if user_level >= 4:
        return True

    # 部门管理员：本部门所有文档
    if user_level >= 3 and user.department == document.department:
        return True

    # 角色层级够 且 （同部门 或 公开文档）
    if user_level >= doc_level:
        if document.permission == "public" or user.department == document.department:
            return True

    return False


def filter_accessible_documents(user: User, documents: list) -> list:
    """从文档列表中过滤出用户有权限访问的文档"""
    return [doc for doc in documents if can_access_document(user, doc)]
