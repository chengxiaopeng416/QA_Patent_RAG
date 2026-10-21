import hashlib

from langchain_core.documents import Document

from utils.config import snippet_max_chars

"""
将检索到的文档映射一个id，将id和文档保存到字典中
作用：
当检索工具执行时，将文档映射为ID保存到doc_store
当重排工具执行时，则根据ID获取完整文档，然后进行重排。
目的是减少文档在工具之间传递时消耗大量token，减少token消耗
"""

class DocStore:
    def __init__(self):
        self._docs: dict[str, Document] = {}

    # 根据文档内容生成一个文档ID
    def make_doc_id(self, content: str):
        return hashlib.md5(content.strip().encode("utf-8")).hexdigest()[:16]

    # 添加文档到存储（进行映射）中
    def add_doc(self, doc: Document):
        doc_id = self.make_doc_id(doc.page_content)
        # 如果希望新值覆盖旧值
        self._docs[doc_id] = doc

        # 如果不希望新值覆盖旧值
        # if doc_id not in self._docs:
        #     self._docs[doc_id] = doc
        return doc_id
    # 进行批量添加文档和ID的映射关系
    def add_all(self, docs: list[Document]):
        return [self.add_doc(doc) for doc in docs]

    # 根据一个文档id获取一个文档
    def get_doc(self, doc_id: str):
        return self._docs[doc_id]

    # 根据文档ID批量获取文档
    def get_batch(self, doc_ids: list[str]):
        return [self.get_doc(doc_id) for doc_id in doc_ids]

    # 截取文档前100个字符作为文档的摘要信息
    def get_snippet(self, doc: Document):
        content = doc.page_content.strip().replace("\n", " ")

        # 如果文档长度大于100，截取前100个字符，否则直接返回content
        if len(content) > snippet_max_chars:
            content = content[:snippet_max_chars] + "..."

        return content

    def items(self):
        return self._docs.items()








