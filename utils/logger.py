"""
日志打印工具
"""
import logging


# 全局日志打印器
def setup_logger(name: str = "rag_system") -> logging.Logger:
    """初始化logger对象"""
    logger = logging.getLogger(name)
    # 设置日志级别
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # StreamHandle:创建一个handler，初始化控制台（终端）日志打印，用于写入日志文件
        # FileHandler:文件日志控制器，将日志保存到本地文件中
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        # Formatter：设置日志打印格式
        # asctime：时间
        # levelname：日志级别
        # name：程序执行的文件名
        # message：日志内容
        # datefmt： 日期格式化
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger