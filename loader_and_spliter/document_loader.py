"""
文档加载
"""
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_mineru import MinerULoader

from utils.logger import setup_logger

#创建日志加载器
logger = setup_logger(__name__)


class DocumentLoader:
    def __init__(self, file_path):
        """
        初始化文档加载器
        参数:
            file_path (str): 要加载的文件路径
        """
        self.file_path = file_path

    # 文档加载
    def markdown_load(self):
        """
        加载Markdown格式文档
        返回:
            list: 包含文档内容的列表
        """
        md_loader = UnstructuredMarkdownLoader(file_path=self.file_path)
        docs = md_loader.load()

        return docs

    # minerU加载器：可以加载pdf，word等
    def mineru_load(self):
        """
        使用MinerU加载器加载多种格式文档（如PDF、Word等）
        返回:
            list: 包含文档内容的列表
        """
        mu_loader = MinerULoader(source=self.file_path)
        docs = mu_loader.load()
        logger.info(f"minerU文档加载成功，共加载{len(docs)}个文档")
        return docs

    # 定义通用加载器
    def load(self):
        """
        根据文件扩展名自动选择合适地加载器
        返回:
            list: 加载的文档内容
        异常:
            Exception: 当文件格式不支持时抛出异常
        """
        # 获取文件名的后缀
        suffix = self.file_path.split(".")[-1]
        if suffix == "md":
            return self.markdown_load()
        elif suffix in ["pdf", "docx", "doc"]:
            return self.mineru_load()
        else:
            raise Exception("不支持的文件格式")
