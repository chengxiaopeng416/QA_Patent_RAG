"""
文档拆分器
"""
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.logger import setup_logger

logger = setup_logger(__name__)
# 递归文本切割器
class DocumentSplitter:
    def __init__(self, docs: List[Document]):
        """
        初始化文档分割器
        参数:
            docs: 需要分割的文档列表，每个文档是一个Document对象
        """
        self.docs = docs

    # separators: 分割符，类型是列表，按照列表中元素的顺序进行分割
    # chunk_size: 文本块的最大长度，一般按token数来计算
    # chunk_overlap: 文本块之间的重叠的token数长度
    # 作用：防止完整句子被切割成两段，保证相邻句子有关联，能获取到连贯的上下文
    # 在切割时，先按照separators切割，如果切割后的文本块大于chunk_size，再按照chunk_size切割
    # 如果切割后的文本块小于chunk_size，则将相邻的文本块合并，直到满足chunk_size


    # # 按标题切割的切割器
    # headers_splitter_on  =[
    #     ("# ", "H1"),
    #     ("## ", "H2"),
    #     ("### ", "H3")
    # ]
    # MarkdownHeaderTextSplitter(
    #     headers_to_split_on = headers_splitter_on
    # )


    #可以先按标题切割，再把切割后的文本块按照RecursiveCharacterTextSplitter切割
    def split(self):
        """
        执行文档分割操作
        使用RecursiveCharacterTextSplitter将文档分割成指定大小的文本块，
        考虑了文本的完整性和上下文连贯性
        返回:
            分割后的文本块列表
        """
        spliter = RecursiveCharacterTextSplitter(
            chunk_size=512,      # 每个文本块的最大长度为512个token
            chunk_overlap=50,    # 相邻文本块之间重叠50个token，保证上下文连贯
            separators=["\n\n", "\n", "。", "？"]  # 按照优先级顺序分割文本的分割符
        )

        chunks = spliter.split_documents(self.docs)  # 执行文档分割

        logger.info(f"文档分割完成，共分割出{len(chunks)}个文本块")

        return chunks


































