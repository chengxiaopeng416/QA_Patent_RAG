"""
根据用户问题检索三元组：
1.大模型从用户问题中提取实体
2.根据提取的实体在neo4j中检索三元组
3.对检索到的三元组去重
4.将三元组转换为文本，作为大模型回答的上下文
"""
import random

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_neo4j import Neo4jGraph

from models.my_llm import qwen_llm
from utils.config import neo4j_url, neo4j_username, neo4j_password, neo4j_database

class Neo4jRetriever:
    def __init__(self, top_k=5):
        self.graph = Neo4jGraph(
            url=neo4j_url,
            username=neo4j_username,
            password=neo4j_password,
            database=neo4j_database
        )
        self.top_k = top_k

# 从用户问题中提取实体
    def extract(self, query: str):
        prompt = ChatPromptTemplate.from_template("""
            从以下专利或技术文献相关问题中提取关键实体，返回JSON数组。
            实体类型包括：专利名称、技术方案、发明人、申请人、技术领域、IPC分类号、技术问题、技术效果等。

            例如：["卷积神经网络", "图像识别", "医学影像"]

            问题：{query}
            """)
        chain = prompt | qwen_llm | JsonOutputParser()

        result = chain.invoke({"query": query})

        return result if isinstance(result, list) else [result]


    # 根据实体检索
    def retrieve_triples(self, entity_list: list[str]):
        if len(entity_list) == 0:
            return None
        triples = []
        for entity in entity_list:
            # 只检索特定关系类型的三元组
            result = self.graph.query(
                """
                MATCH (s:ENTITY {name: $entity_name}) - [r] -> (o:ENTITY)
                WHERE type(r) IN ['采用', '解决', '应用于', '提出', '改进']
                RETURN s.name AS subject,
                type(r) AS predicate,
                o.name AS object,
                r.constraint AS constraint
                UNION
                MATCH (s:ENTITY) <- [r] - (o:ENTITY {name: $entity_name})
                WHERE type(r) IN ['采用', '解决', '应用于', '提出', '改进']
                RETURN s.name AS subject,
                type(r) AS predicate,
                o.name AS object,
                r.constraint AS constraint       
                """,
                params={"entity_name": entity}
            )
            triples.extend(result)
        return triples

    # 把检索到三元组去重，转成字符串，作为大模型的上下文
    # def get_context(self, query: str):
    # # 提取用户问题中的实体
    # entity_list = self.extract(query)
    # # 根据实体检索三元组
    # triples = self.retrieve_triples(entity_list)
    # # 去重
    # unique_triples = []
    # filter_set = set()
    # for t in triples:
    #     s = (t['subject'], t['predicate'], t['object'], t['constraint'])
    #     if s not in filter_set:
    #         filter_set.add(s)
    #         unique_triples.append(t)
    # 转成字符串
    # random.shuffle(unique_triples)
    # context = "\n".join([
    #     f"- {t['subject']} → {t['predicate']} → {t['object']}" +
    #     (f" (条件: {t['constraint']})" if t['constraint'] else "")
    #     for t in unique_triples[:self.top_k]
    # ])
    # return context
    """
    将原get_context函数拆分成以下三个函数
    """

    # 三元组去重
    def deduplicate_triples(self, triples: list):
        # 去重
        unique_triples = []
        filter_set = set()
        for t in triples:
            s = (t['subject'], t['predicate'], t['object'], t['constraint'])
            if s not in filter_set:
                filter_set.add(s)
                unique_triples.append(t)

        return unique_triples

    # 三元组封装
    def get_paths(self, query: str):
        # 提取用户问题中的实体
        entity_list = self.extract(query)
        # 根据实体检索三元组
        triples = self.retrieve_triples(entity_list)

        unique_triples = self.deduplicate_triples(triples)
        # 将三元组封装成字典
        paths = []

        for t in unique_triples:
            content = f"- {t['subject']} → {t['predicate']} → {t['object']}" + \
                      (f" (条件: {t['constraint']})" if t['constraint'] else "")
            paths_dict = {
                "content": content,
                "metadata": {
                    "source": "neo4j",
                    "subject": t['subject'],
                    "predicate": t['predicate'],
                    "object": t['object'],
                    "constraint": t.get('constraint', "")
                }
            }
            paths.append(paths_dict)

        return paths

    def get_context(self, query: str):
        """
        根据查询获取上下文内容
        参数:
            query (str): 用户查询字符串
        返回:
            str: 由路径内容组成的上下文字符串
        """
        # 获取查询相关的路径
        paths = self.get_paths(query)
        # 将路径内容合并为一个字符串，每个路径内容占一行
        context = "\n".join(['content'] for path in paths)
        return context
