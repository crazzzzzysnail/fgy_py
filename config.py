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
                    value = value.strip()
                    # 自动去除值两端的引号 (单引号或双引号)
                    if len(value) >= 2 and value[0] in ('"', "'") and value[0] == value[-1]:
                        value = value[1:-1]
                    env_config[key.strip()] = value
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

# --- 奖励规则配置 ---
# 定义奖励计算规则，key 为变量名，value 为计算表达式 (字符串)
# 表达式中可以使用 'days' 代表 successful_days
REWARD_RULES = {
    "reward_days": "days * 3",
    "reward_minutes": "format_minutes(days * 65)"
}

# HTML报告顶部的汇总显示模板
# 可以使用 {successful_days} 以及 REWARD_RULES 中定义的变量
# SUMMARY_TEMPLATE = "累计签到: {successful_days}天 (获得 {reward_days}天, 时长 {reward_minutes})"