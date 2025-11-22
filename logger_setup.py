import logging
import sys

def setup_logger():
    """
    配置日志记录器，同时输出到控制台和文件。
    """
    # 创建一个日志记录器
    logger = logging.getLogger('QingLongTask')
    logger.setLevel(logging.INFO)

    # 如果已经有处理器，则不再添加，防止重复记录
    if logger.hasHandlers():
        return logger

    # 创建一个格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 创建一个处理器，用于将日志输出到控制台
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # 创建一个处理器，用于将日志写入文件
    file_handler = logging.FileHandler('task.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# 初始化并获取日志记录器实例
logger = setup_logger()