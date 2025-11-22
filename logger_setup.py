import logging
import sys

def setup_logger(debug=False):
    """
    配置日志记录器，同时输出到控制台和文件。

    :param debug: 如果为True，日志级别将设置为DEBUG，否则为INFO。
    """
    logger = logging.getLogger('CheckinTask')
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    # 如果已经有处理器，则清空以重新配置，防止重复记录
    if logger.hasHandlers():
        logger.handlers.clear()

    # 创建一个格式化器
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 创建一个处理器，用于将日志输出到控制台
    # On Windows, reconfigure stdout to use UTF-8 to prevent UnicodeEncodeError
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except (TypeError, AttributeError):
            # This can fail in some environments (e.g., if not running in a real console).
            pass
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # 创建一个处理器，用于将日志写入文件（每次运行时覆盖）
    file_handler = logging.FileHandler('task.log', 'w', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info(f"日志系统初始化完成。调试模式: {'开启' if debug else '关闭'}")
    return logger