import logging
import sys
import re

class ConsoleFilter(logging.Filter):
    """
    一个自定义过滤器，用于控制台的简洁模式。
    """
    def __init__(self, concise_mode=False):
        super().__init__()
        self.concise_mode = concise_mode
        if self.concise_mode:
            # 预编译正则表达式以提高效率
            self.allowed_patterns = [
                re.compile(r"^日志系统初始化完成"),
                re.compile(r"^--- \[线程结束\]"),
                re.compile(r"^所有发送任务已完成"),
                re.compile(r"^\*+"),
                re.compile(r"^\*\*\* 成功签到"),
            ]

    def filter(self, record):
        # 如果不是简洁模式，允许所有日志通过
        if not self.concise_mode:
            return True

        # 在简洁模式下，总是允许ERROR及以上级别的日志
        if record.levelno >= logging.ERROR:
            return True

        # 检查消息是否匹配允许的模式之一
        message = record.getMessage()
        for pattern in self.allowed_patterns:
            if pattern.search(message):
                return True
        
        # 其他所有消息在简洁模式下被过滤掉
        return False

def setup_logger(debug=False, concise_mode=False):
    """
    配置日志记录器，同时输出到控制台和文件。

    :param debug: 如果为True，日志级别将设置为DEBUG，否则为INFO。
    :param concise_mode: 如果为True，控制台将只输出关键信息。
    """
    logger = logging.getLogger('CheckinTask')
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    # 如果已经有处理器，则清空以重新配置，防止重复记录
    if logger.hasHandlers():
        logger.handlers.clear()

    # 创建一个格式化器
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # --- 控制台处理器 ---
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except (TypeError, AttributeError):
            pass
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    # 如果开启简洁模式，则为控制台处理器添加过滤器
    if concise_mode:
        stream_handler.addFilter(ConsoleFilter(concise_mode=True))
    logger.addHandler(stream_handler)

    # --- 文件处理器 (不受简洁模式影响) ---
    file_handler = logging.FileHandler('task.log', 'w', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    modes = []
    if debug:
        modes.append("调试")
    if concise_mode:
        modes.append("简洁")
    
    mode_str = "、".join(modes) if modes else "普通"
    logger.info(f"日志系统初始化完成。日志模式: {mode_str}")
    return logger