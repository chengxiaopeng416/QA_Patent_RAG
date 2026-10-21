"""
从文档中提取三元组，存入neo4j数据库
1.文档加载和分割
2.三元组提取
3三元组处理
4.存入neo4j数据库
"""
from typing import List, Dict

from langchain_core.documents import Document
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_neo4j import Neo4jGraph

from models.my_llm import qwen_llm
from utils.config import neo4j_url, neo4j_username, neo4j_password, neo4j_database
from utils.logger import setup_logger

logger = setup_logger(__name__)


class Neo4jIndex:
    def __init__(self, delete_flag: bool = False):
        self.graph = Neo4jGraph(
            url=neo4j_url,
            username=neo4j_username,
            password=neo4j_password,
            database=neo4j_database
        )
        self.delete_flag = delete_flag

    # 大模型提取三元组
    def extract_triples(self, docs: list[Document]):
        # 简化处理：只处理整个文档，没有处理文档分割的情况
        content = docs[0].page_content

        prompt = ChatPromptTemplate.from_template("""
            你是一个技术专利知识提取专家。请从以下专利或技术文献中，**提取所有**核心技术信息，生成知识三元组。

            **提取规则**：
            1. 每个技术方案/发明点至少提取1-5条三元组
            2. 三元组格式：[{{"subject":"主体","predicate":"关系","object":"客体","constraint":"条件/参数"}}]
            3. 关系类型包括但不限于：采用、解决、提出、属于、包含、基于、涉及、应用于、改进、优化、解决、克服
            4. 主体通常是：专利名称、技术方案、发明人、申请人、技术领域、产品名称、材料名称、方法名称
            5. 客体通常是：技术问题、技术效果、技术方案、应用场景、分类号、参数、指标
            6. 如果有特定条件（如温度、压力、比例等工艺参数），放在constraint字段

            **输出要求**：
            - 输出一个JSON数组，包含所有三元组
            - 不要遗漏任何技术要点
            - 如果一个技术方案涉及多个方面，拆分成多条三元组
            - 实体名称尽量使用原文中的专业术语，保持准确性

            **示例**：
            文献："本发明公开了一种基于深度学习的图像识别方法，采用卷积神经网络提取特征，解决了传统方法识别准确率低的问题，在医学影像诊断中具有广泛应用。"
            提取：
            [
              {{"subject":"基于深度学习的图像识别方法","predicate":"采用","object":"卷积神经网络","constraint":""}},
              {{"subject":"基于深度学习的图像识别方法","predicate":"解决","object":"传统方法识别准确率低","constraint":""}},
              {{"subject":"基于深度学习的图像识别方法","predicate":"应用于","object":"医学影像诊断","constraint":""}},
              {{"subject":"卷积神经网络","predicate":"用于","object":"特征提取","constraint":""}}
            ]

            **待处理的文档**：
            {content}

            请开始提取，输出JSON数组：
            """)

        chain = prompt | qwen_llm | JsonOutputParser()
        return chain.invoke({"content": content})

    # 三元组数据处理
    def clean_triples(self, triples: List[Dict]) -> List[Dict]:
        """清洗提取的三元组"""
        # 停用词，用来过滤掉如语气词等不相关的三元组
        # 停用词：过滤掉通用词汇
        STOP_WORDS = {"的", "了", "是", "在", "和", "与", "或", "等", "一种", "方法", "装置", "设备", "系统", "本发明",
                      "公开", "提供"}

        # 同义词映射：统一实体名称
        SYNONYMS = {
            "本发明": "该技术方案",
            "该发明": "该技术方案",
            "此方法": "该技术方案",
            "发明人": "申请人",
            "权利要求": "技术方案",
            "具体实施方式": "实施例",
            "技术领域": "应用领域",
            "背景技术": "现有技术",
            "有益效果": "技术效果",
            "对比文件": "现有技术",
        }

        # 关系映射：统一关系名称
        REL_MAP = {
            "采用": "采用", "使用": "采用", "利用": "采用",
            "解决": "解决", "克服": "解决", "改善": "解决",
            "提出": "提出", "公开": "提出", "揭示": "提出",
            "属于": "属于", "归类于": "属于", "分类为": "属于",
            "包含": "包含", "包括": "包含", "含有": "包含",
            "基于": "基于", "根据": "基于", "依据": "基于",
            "涉及": "涉及", "关于": "涉及", "关联": "涉及",
            "应用于": "应用于", "适用于": "应用于", "用于": "应用于",
            "改进": "改进", "优化": "改进", "提升": "改进", "增强": "改进"
        }

        cleaned, seen = [], set()
        for item in triples:
            # 去掉空格
            s = item.get("subject", "").strip()
            p = item.get("predicate", "").strip()
            o = item.get("object", "").strip()
            c = item.get("constraint", "").strip()
            # 去掉空字符串，判断三元组是否完整，否则过滤
            if not all([s, p, o]) or len(s) < 2 or len(o) < 2:
                continue

            # 判断实体中是否存在停用词，如果存在则过滤掉
            if s in STOP_WORDS or o in STOP_WORDS:
                continue

            # 把三元组实体中意思相近的标签名映射为统一的标签名
            s, o = SYNONYMS.get(s, s), SYNONYMS.get(o, o)

            # 把三元组关系中意思相近的映射为统一的标签名
            p = REL_MAP.get(p, p)

            # 去重
            key = (s, p, o, c)

            # 判断三元组是否重复，如果重复则过滤掉
            if key not in seen:
                seen.add(key)
                cleaned.append({"subject": s, "predicate": p, "object": o, "constraint": c})

        # print(cleaned)
        # 供后续添加到neo4j数据库使用，也能保证数据一致性
        return cleaned

    # 存入neo4j数据库
    def add_triples(self, triples: List[Dict]):
        """将三元组导入Neo4j，返回导入统计"""
        # rel_map = {
        #     "适用于": "APPLIES_TO",
        #     "规定": "HAS_RULE",
        #     "要求": "REQUIRES",
        #     "承担": "COST_BEARER",
        #     "支持": "SUPPORTS"
        # }
        # 如果delete_flag为True，则先清空neo4j数据库
        if self.delete_flag:
            self.graph.query("MATCH (n) DETACH DELETE n")
        # 定义一个计数器，插入neo4j数据库成功的数量
        success_count = 0
        try:
            for item in triples:
                s = item.get("subject", "")
                p = item.get("predicate", "")
                o = item.get("object", "")
                c = item.get("constraint", "")

                self.graph.query(
                    f"""
                    MERGE (s:ENTITY {{name: $s_name}})
                    MERGE (o:ENTITY {{name: $o_name}})
                    MERGE (s) - [r:{p}] -> (o)
                    SET r.constraint = $c
                    """,
                    params={
                        "s_name": s,
                        "p": p,
                        "o_name": o,
                        "c": c
                    })
                success_count += 1
            return {
                "status": "success",
                "success_count": success_count,
                "total_count": len(triples),
                "message": f"成功导入 {success_count}/{len(triples)} 条三元组"
            }
        except Exception as e:
            logger.error(f"三元组保存失败: {str(e)}")
            return {
                "status": "error",
                "message": "三元组保存失败"
            }

    # 保存三元组逻辑整合
    def create_neo4j_index(self, docs: List[Document]):
        resulted = self.extract_triples(docs)
        cleaned_triples = self.clean_triples(resulted)

        add_results = self.add_triples(cleaned_triples)
        return add_results
