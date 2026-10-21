"""
创建chroma向量索引
"""

from typing import List

from langchain_core.documents import Document

from utils.logger import setup_logger

logger = setup_logger(__name__)


class VectorIndex:
    """
    向量索引类，用于存储和检索文档向量
    """

    def __init__(self, chunks: List[Document], vectorstore, delete_flag: bool = False):
        """
        初始化DocumentIndex类
        参数:
            chunks: 文档块列表，每个元素是一个Document对象
            vectorstore: 向量存储对象，用于存储和检索文档向量
            delete_flag: 布尔值，表示是否在添加新文档前删除现有向量数据，默认为False
        """
        self.chunks = chunks
        self.vectorstore = vectorstore
        self.delete_flag = delete_flag

    #删除向量数据库中的数据
    def delete_vectors(self):
        """
        从向量数据库中删除所有现有数据
        首先获取向量数据库中所有文档的ID，然后使用这些ID删除对应的向量数据
        """
        ids = self.vectorstore.get()["ids"]
        if len(ids) > 0:
            self.vectorstore.delete(ids=ids)
            logger.info("已删除向量数据库中的所有数据")

    #添加数据到向量数据库
    def add_documents(self):
        """
        将文档块添加到向量数据库中
        如果delete_flag为True，则在添加新文档前会先删除向量数据库中的所有现有数据
        最后将所有文档块添加到向量数据库中
        """
        if self.delete_flag:  # 检查是否设置了删除标志
            self.delete_vectors()  # 如果设置了删除标志，则先删除向量数据库中的所有现有数据
        #chunks数量太多，造成chroma链接失败的问题
        # self.vectorstore.add_documents(self.chunks)  # 首先尝试一次性添加所有文档块
        batch_size = 200  # 如果报错再设小一点
        for i in range(0, len(self.chunks), batch_size):
            batch = self.chunks[i:i + batch_size]
            self.vectorstore.add_documents(batch)
            logger.info(f"已导入 {i + len(batch)}/{len(self.chunks)}")

        logger.info("向量数据库索引创建完成")
