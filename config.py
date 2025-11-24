import os

def _load_env_once():
    """
    在模块加载时读取一次 .env 文件并返回其内容。
    """
    env_config = {}
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_config[key.strip()] = value.strip()
    return env_config

# 在模块加载时执行一次，将结果缓存到 _env_cache 中
_env_cache = _load_env_once()

def get_config(key, default=None):
    """
    获取配置项。
    优先级: 环境变量 > .env 文件 > 默认值。
    """
    # 1. 尝试从环境变量获取
    value = os.environ.get(key)
    if value is not None:
        return value

    # 2. 尝试从缓存的 .env 配置获取
    value = _env_cache.get(key)
    if value is not None:
        return value

    # 3. 返回默认值
    return default

# --- 对外暴露的配置项 ---

# 布尔值配置项
DEBUG_MODE = get_config('DEBUG_MODE', 'False').lower() in ('true', '1', 't')
CONSOLE_CONCISE_MODE = get_config('CONSOLE_CONCISE_MODE', 'True').lower() in ('true', '1', 't')

# WxPusher 配置
WXPUSHER_APP_TOKEN = get_config('WXPUSHER_APP_TOKEN')
WXPUSHER_UIDS = get_config('WXPUSHER_UIDS')

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(BASE_DIR, 'tasks.json')
STATUS_FILE = os.path.join(BASE_DIR, 'status.json')