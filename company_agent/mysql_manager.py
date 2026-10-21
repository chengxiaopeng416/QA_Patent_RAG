"""
mysql数据库操作
1.获取数据表名称
2.获取数据表结构
3.验证sql是否有语法错误
4.执行sql
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import create_engine, inspect, text


class MysqlManager:
    """
    pool_size:连接池中最大连接数
    max_overflow:当超过pool_size时，连接池中连接的最大数量，0表示无限制
    pool_Pre_ping:连接池中的连接在执行sql之前是否进行一次ping操作，True表示是，False表示否
    pool_recycle:连接池中的连接在空闲多久后自动断开进行回收，0表示不自动断开
    echo:是否打印sql语句，True表示是，False表示否
    """

    def __init__(self, connection_string):
        self.engine = create_engine(
            connection_string,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=True,
        )

    # 获取数据表名称(第一个方法)
    def get_table_name(self):
        query = """
                SELECT
                table_name,
                table_comment 
                FROM information_schema.TABLES 
                WHERE table_schema = DATABASE () 
                    AND table_type = 'BASE TABLE' 
                ORDER BY table_name
                """

        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text(query))
                    # print(result)
                    table_info = [{"table_name": row[0], "table_comment": row[1]} for row in result.fetchall()]
                    return table_info
        except Exception as e:
            raise Exception(f"获取数据表名称和注释失败：{e}")

    # 获取数据表结构(第二个方法)
    def get_table_schema(self, table_names: Optional[list[str]] = None):
        inspector = inspect(self.engine)

        #如果table_names不为空则直接使用，否则通过inspector获取所有表名
        table_names = table_names if table_names else inspector.get_table_names()

        schema_iist = []

        for table_name in table_names:
            #获取列
            columns = inspector.get_columns(table_name)
            #获取主键
            pk_constraints = inspector.get_pk_constraint(table_name)
            #获取外键
            fk_constraints = inspector.get_foreign_keys(table_name)
            #获取索引
            indices = inspector.get_indexes(table_name)

            # print(columns)
            # print(pk_constraints)
            # print(fk_constraints)
            # print(indices)

            table_schema = f"表名：{table_name}\n"

            #解析列信息
            column_info = "列名：\n"
            for column in columns:
                name = column['name']
                type = column['type']
                comment = column.get("comment", "无注释")
                column_info += f"  {name} -> {type} {comment}\n"

            table_schema += column_info

            #解析主键信息
            pk = pk_constraints['constrained_columns'][0]
            pk_info = f"主键：{pk}\n"

            table_schema += pk_info

            #解析外键信息
            if fk_constraints:
                fk_info = "外键约束: \n"
                for fk in fk_constraints:
                    fk_info += f" - {fk['constrained_columns']} -> {fk['referred_table']}({fk['referred_columns']})\n"

                table_schema += fk_info

            #解析索引信息
            if indices:
                index_info = "索引: \n"
                for index in indices:
                    index_name = index['name']
                    index_column_name = index['column_names']
                    index_type = "唯一" if index['unique'] else "非唯一"
                    index_info += f" {index_name} -> {index_column_name} ({index_type})\n"

                table_schema += index_info
            print(table_schema)
            schema_iist.append(table_schema)

        print(schema_iist)
        return "\n\n".join(schema_iist)

    #  执行sql(第三个方法)
    def execute_query(self, query: str):
        query = query.strip().lower()
        if not query.startswith("select"):
            raise Exception("不允许进行非查询操作")

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                cols = result.keys()
                rows = result.fetchall()
                #遍历行
                data_list = []
                for row in rows:
                    #遍历列
                    for i, col in enumerate(cols):
                        data = {col: row[i]}
                        data_list.append(data)

                return json.dumps(data_list, ensure_ascii=False, cls=CustomJSONEncoder)
        except Exception as e:
            raise Exception(f"执行sql查询失败：{e}")

    #sql验证
    def validate_query(self, query: str):
        query = query.strip().lower()
        if not query.startswith("select"):
            raise Exception("不允许进行非查询操作")
        try:
            with self.engine.connect() as conn:
                query = "EXPLAIN " + query
                result = conn.execute(text(query))

                return "sql语法正确，查询成功"
        except Exception as e:
            raise Exception(f"sql语法错误：{e}")


# 问题现象：执行sql时报错
# 问题原因：json不能正常解析Decimal和datetime对象
# 问题解决方案：自定义json解析器json.JSONEncoder，单独解析Decimal和datetime对象
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')

        return super().default(obj)

# if __name__ == '__main__':
#     db_manager = MysqlManager(connection_string)
#     table_info = db_manager.get_table_name()
#     print(table_info)
#
#     schema_info = db_manager.get_table_schema(["sys_user","sys_role"])
#     print(schema_info)
#
#     result = db_manager.execute_query("select * from sys_role")
#     print(result)
