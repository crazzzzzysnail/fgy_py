import logging
import sys
import re
import os
import config

class ConsoleFilter(logging.Filter):
    """
    一个自定义过滤器，用于控制台的简洁模式。
    """
    def __init__(self, concise_mode=False):
        super().__init__()
        self.concise_mode = concise_mode
        if self.concise_mode:
            # 将多个模式合并为一个，用 | (或) 分隔
            self.allowed_pattern = re.compile(
                r"^(日志系统初始化完成|--- \[线程结束\]|所有发送任务已完成|\*+|\*\*\* 成功签到|WxPusher)"
            )

    def filter(self, record):
        # 如果不是简洁模式，允许所有日志通过
        if not self.concise_mode:
            return True

        # 在简洁模式下，总是允许ERROR及以上级别的日志
        if record.levelno >= logging.ERROR:
            return True

        # 检查消息是否匹配合并后的模式
        if self.allowed_pattern.search(record.getMessage()):
            return True
        
        # 其他所有消息在简洁模式下被过滤掉
        return False

class FlushingFileHandler(logging.FileHandler):
    """
    一个自定义的文件处理器，在每次写入日志后强制刷新缓冲区并同步到磁盘。
    """
    def emit(self, record):
        super().emit(record)
        self.flush()
        # 强制将文件写入磁盘
        if self.stream and hasattr(self.stream, 'fileno'):
            os.fsync(self.stream.fileno())

def setup_logger():
    """
    配置日志记录器，同时输出到控制台和文件。
    配置从 config 模块加载。
    """
    logger = logging.getLogger('CheckinTask')
    level = logging.DEBUG if config.DEBUG_MODE else logging.INFO
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
    if config.CONSOLE_CONCISE_MODE:
        stream_handler.addFilter(ConsoleFilter(concise_mode=True))
    logger.addHandler(stream_handler)

    # --- 文件处理器 (不受简洁模式影响) ---
    # 使用自定义的 FlushingFileHandler 来防止文件损坏
    file_handler = FlushingFileHandler('task.log', 'w', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    modes = []
    if config.DEBUG_MODE:
        modes.append("调试")
    if config.CONSOLE_CONCISE_MODE:
        modes.append("简洁")
    
    mode_str = "、".join(modes) if modes else "普通"
    logger.info(f"日志系统初始化完成。日志模式: {mode_str}")
    return logger