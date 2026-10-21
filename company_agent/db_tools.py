"""
定义工具
"""
from typing import Annotated, List, Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from auth_load.permission import doc_permission_levels, get_role_levels
from company_agent.mysql_manager import MysqlManager
from database.models import User, init_session
from utils.env_utils import connection_string


def _permission_where_sql(user: User) -> Optional[str]:
    """
    根据用户角色生成 t_document 的权限过滤SQL条件
    super_admin 返回 None（不需要过滤）
    """
    level = get_role_levels(user.role)
    if level >= 4:
        return None
    dept = user.department.replace("'", "''")
    # 部门管理员：本部门所有文档 + 其他部门公开文档
    if level >= 3:
        return f"(department = '{dept}' OR permission = 'public')"
    # 其他角色：角色等级 >= 文档密级，且（公开 或 同部门）
    allowed = [p for p, l in doc_permission_levels.items() if 0 < l <= level]
    if not allowed:
        return "permission = 'public'"
    allowed_str = "','".join(p.replace("'", "''") for p in allowed)
    return f"(permission = 'public' OR (permission IN ('{allowed_str}') AND department = '{dept}'))"


def _inject_permission_where(sql: str, cond: str) -> str:
    """在select语句中注入权限过滤条件，防止查询到无权限的文档"""
    sql = sql.strip().rstrip(";").strip()
    low = sql.lower()
    idx = low.find(" where ")
    if idx != -1:
        before = sql[:idx + 7]
        after = sql[idx + 7:]
        return before + cond + (" AND " + after if after else "")
    return sql + " WHERE " + cond


#定义获取表名的工具
# 定义获取表名的工具
@tool
def list_table_tool():
    """
    获取表名和注释
    """
    try:
        # 初始化MysqlManager
        db_manager = MysqlManager(connection_string)
        if not db_manager:
            return "初始化MysqlManager失败"

        table_info = db_manager.get_table_name()

        if not table_info:
            return "数据库中没有表"

        # 使用列表收集结果，比 += 拼接字符串更高效
        result_lines = [f"从数据库中获取到{len(table_info)}张数据表"]

        for i, item in enumerate(table_info, start=1):
            table_name = item.get("table_name", "未知表名")

            # 安全处理注释：先取值，如果为None则设为空字符串，再strip()，最后判断
            raw_comment = item.get("table_comment") or ""
            table_comment = raw_comment.strip() if raw_comment.strip() else "无表注释"

            result_lines.append(f"{i}.表名:{table_name} 表注释:{table_comment}")

        return "\n".join(result_lines)

    except Exception as e:
        # 记录真实的异常信息 e 供开发者排查，同时给用户返回友好提示
        # 实际开发中建议使用 logging.error(f"获取表名失败: {e}", exc_info=True)
        print(f"Error: {e}")
        return "获取表名失败，请查看后台日志"


#获取表结构的工具
@tool
def table_schema_tool(
        table_name: Annotated[List[str], " 表名列表 "]
):
    """
    根据表名,获取表结构
    """
    try:
        # 初始化MysqlManager
        db_manager = MysqlManager(connection_string)
        if not db_manager:
            return "初始化MysqlManager失败"
        table_schema = db_manager.get_table_schema(table_name)

        return table_schema
    except Exception as e:
        return "获取表结构失败"


#执行SQL
@tool
def execute_sql_tool(
        query: Annotated[str, "需要执行的select sql语句"],
        config: RunnableConfig
):
    """执行select sql语句的工具"""
    try:
        # 初始化MysqlManager
        db_manager = MysqlManager(connection_string)
        if not db_manager:
            return "初始化MysqlManager失败"

        # 从运行配置中获取当前用户
        user_id = int(config.get("configurable", {}).get("user_id", 0) or 0)
        db = init_session()()
        try:
            user = db.query(User).get(user_id)
        finally:
            db.close()

        # 查询文档表时注入权限过滤，防止查到无权限的文档
        permission_filtered = False
        if user and "t_document" in query.lower():
            cond = _permission_where_sql(user)
            if cond:
                query = _inject_permission_where(query, cond)
                permission_filtered = True

        result = db_manager.execute_query(query)

        # 权限过滤生效时附加提示，避免LLM误认为"文件不存在"
        if permission_filtered:
            result += "\n[权限提示] 查询结果已按当前用户的角色/部门权限自动过滤，可能存在您无权访问的文档；若结果为空，说明该级别的文档需要更高权限，请勿回复'文件不存在'。"

        return result
    except Exception as e:
        return "执行SQL失败"


#验证SQl
@tool
def check_sql_tool(
        query: Annotated[str, "需要验证的select sql语句,该语句在执行前通过EXPLAIN进行验证"]
):
    """验证select SQL的工具,在执行execute_sql_tool前，需要先检查sql是否有语法错误"""
    try:
        # 初始化MysqlManager
        db_manager = MysqlManager(connection_string)
        if not db_manager:
            return "初始化MysqlManager失败"

        result = db_manager.validate_query(query)
        return result
    except Exception as e:
        return "验证SQL失败"
