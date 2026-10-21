"""
RAG 第一阶段的文档加载和文档分割
"""
from pathlib import Path
from langchain_community.document_loaders import UnstructuredMarkdownLoader, TextLoader, PyMuPDFLoader, Docx2txtLoader, \
    UnstructuredPowerPointLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

#多格式文档加载器
def load_document(filepath: str):
    # 如果filepath是一个目录，则遍历目录下的所有文件
    if Path(filepath).is_dir():
        # 获取目录下所有文档
        paths = [p for p in Path(filepath).rglob("*") if p.is_file()]
    else:
        # 如果filepath是一个文件，则直接获取文件路径
        paths = [Path(filepath)]
    all_docs = []
    for fp in paths:
        suffix = fp.suffix.lower()
        #条件语句判断文档后缀名
        if suffix == ".md":
            loader = UnstructuredMarkdownLoader(str(fp))
        elif suffix == ".txt":
            loader = TextLoader(str(fp), encoding="utf-8")
        elif suffix == ".pdf":
            loader = PyMuPDFLoader(str(fp))
        elif suffix == ".docx":
            loader = Docx2txtLoader(str(fp))
        elif suffix == ".pptx":
            loader = UnstructuredPowerPointLoader(str(fp))
        else:
            print(f"跳过 {fp.name}：不支持 {suffix}")
            continue
        # 调用loader的load方法获取文档内容
        docs = loader.load()
        # 将文档内容添加到all_docs列表中
        all_docs.extend(docs)
    # 返回加载的文档列表
    return all_docs


#文档分割
#chunk_size:分割文档的最大token数
#chunk_overlap:相邻两个文档片段共享的token数
#separators:按照指定的分割符去分割文档（separators的优先级高于chunk_size）
def split_document(docs: list[Document]):
    """
    将文档分割成较小的文本块，便于后续处理和分析
    :param docs: 需要分割的文档列表，每个元素为Document对象
    :return: 分割后的文本块列表，每个元素为Document对象
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=20,
        separators=["\n\n", "\n", "  ", "？", "--"]
    )
    chunks = splitter.split_documents(docs)

    return chunks


if __name__ == '__main__':
    docs = load_document(r"D:\ai250801\程崤鹏\大项目\docs")
    chunks = split_document(docs)
    for chunk in chunks:
        print(chunk)
