import json
import time
import os
import concurrent.futures
from logger_setup import setup_logger
from har_parser import parse_har
from request_sender import send_request

# --- 全局配置 ---
# 是否开启调试模式。True: 记录详细请求和响应信息; False: 只记录基本信息。
DEBUG_MODE = True

# 初始化日志系统
logger = setup_logger(debug=DEBUG_MODE)

# 脚本根目录，用于构建绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(BASE_DIR, 'tasks.json')

def load_tasks():
    """
    从tasks.json加载任务列表。
    """
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
        logger.info("成功加载任务配置文件。")
        return tasks
    except FileNotFoundError:
        logger.error(f"任务配置文件未找到: {TASKS_FILE}")
        return []
    except json.JSONDecodeError:
        logger.error(f"任务配置文件格式错误: {TASKS_FILE}")
        return []

def run_task(task):
    """
    执行单个任务，此函数将在单独的线程中运行。
    """
    task_name = task.get('name', '未命名任务')
    har_file = os.path.join(BASE_DIR, task.get('har_file', ''))
    count = task.get('count', 1)
    interval = task.get('interval_seconds', 0)

    logger.info(f"--- [线程开始] 任务: {task_name} ---")

    if not har_file or not os.path.exists(har_file):
        logger.error(f"任务 '{task_name}' 的HAR文件未找到或未配置: {har_file}")
        return

    request_details = parse_har(har_file)
    if not request_details:
        logger.error(f"无法为任务 '{task_name}' 解析HAR文件，跳过此任务。")
        return

    for i in range(count):
        logger.info(f"任务 '{task_name}': 正在进行第 {i + 1}/{count} 次发送。")
        send_request(request_details)
        
        if i < count - 1 and interval > 0:
            logger.info(f"任务 '{task_name}': 等待 {interval} 秒...")
            time.sleep(interval)
    
    logger.info(f"--- [线程结束] 任务: {task_name} 执行完毕 ---")


def main():
    """
    脚本主入口函数，使用线程池并行执行任务。
    """
    logger.info(f"================ 自动化任务开始 (多线程模式) ================")
    tasks = load_tasks()
    
    if not tasks:
        logger.warning("没有加载到任何任务，脚本退出。")
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_to_task = {executor.submit(run_task, task): task for task in tasks}
        
        for future in concurrent.futures.as_completed(future_to_task):
            task = future_to_task[future]
            try:
                future.result()
            except Exception as exc:
                logger.error(f"任务 '{task.get('name')}' 在执行期间产生异常: {exc}", exc_info=DEBUG_MODE)

    logger.info("所有发送任务已完成。")
    logger.info("************************************************")
    logger.info("*************** 获得3天VIP ***************")
    logger.info("************************************************")
    logger.info("================ 自动化任务结束 ================")


if __name__ == "__main__":
    main()
