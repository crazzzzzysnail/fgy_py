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
STATUS_FILE = os.path.join(BASE_DIR, 'status.json')

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


def load_status():
    """
    从status.json加载状态信息，主要是成功签到天数。
    """
    try:
        with open(STATUS_FILE, 'r', encoding='utf-8') as f:
            status = json.load(f)
        return status.get('successful_days', 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0


def save_status(successful_days):
    """
    将更新后的状态信息（成功签到天数）保存到status.json。
    """
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump({'successful_days': successful_days}, f, indent=4)


def run_task(task):
    """
    执行单个任务，此函数将在单独的线程中运行。
    """
    task_start_time = time.time()
    task_name = task.get('name', '未命名任务')
    har_file = os.path.join(BASE_DIR, task.get('har_file', ''))
    count = task.get('count', 1)
    interval = task.get('interval_seconds', 0)

    logger.info(f"--- [线程开始] 任务: {task_name} ---")

    if not har_file or not os.path.exists(har_file):
        logger.error(f"任务 '{task_name}' 的HAR文件未找到或未配置: {har_file}")
        return False

    request_details = parse_har(har_file)
    if not request_details:
        logger.error(f"无法为任务 '{task_name}' 解析HAR文件，跳过此任务。")
        return False

    task_fully_successful = True
    for i in range(count):
        logger.info(f"任务 '{task_name}': 正在进行第 {i + 1}/{count} 次发送。")
        
        max_retries = 3
        request_successful = False
        for attempt in range(max_retries):
            if send_request(request_details):
                request_successful = True
                break
            else:
                logger.warning(f"任务 '{task_name}' 第 {i + 1}/{count} 次发送失败 (尝试 {attempt + 1}/{max_retries})。")
                if attempt < max_retries - 1:
                    time.sleep(1)  # 重试前等待1秒

        if not request_successful:
            logger.error(f"任务 '{task_name}' 第 {i + 1}/{count} 次发送连续失败 {max_retries} 次。中止此任务。")
            task_fully_successful = False
            break  # 中止当前任务的后续发送

        if i < count - 1 and interval > 0:
            logger.info(f"任务 '{task_name}': 等待 {interval} 秒...")
            time.sleep(interval)
    
    duration = time.time() - task_start_time
    logger.info(f"--- [线程结束] 任务: {task_name} 执行完毕, 耗时: {duration:.2f} 秒 ---")
    return task_fully_successful


def main():
    """
    脚本主入口函数，使用线程池并行执行任务。
    """
    overall_start_time = time.time()
    logger.info(f"================ 自动化任务开始 (多线程模式) ================")
    
    # 加载历史成功天数
    total_successful_days = load_status()
    logger.info(f"已累计成功签到 {total_successful_days} 天。")

    tasks = load_tasks()
    
    if not tasks:
        logger.warning("没有加载到任何任务，脚本退出。")
        return

    current_run_successful_tasks = 0
    any_task_failed = False

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_to_task = {executor.submit(run_task, task): task for task in tasks}
        
        for future in concurrent.futures.as_completed(future_to_task):
            task = future_to_task[future]
            try:
                is_successful = future.result()
                if is_successful:
                    current_run_successful_tasks += 1
                else:
                    any_task_failed = True
            except Exception as exc:
                any_task_failed = True
                logger.error(f"任务 '{task.get('name')}' 在执行期间产生异常: {exc}", exc_info=DEBUG_MODE)

    total_duration = time.time() - overall_start_time
    logger.info(f"所有发送任务已完成。总耗时: {total_duration:.2f} 秒")

    if not any_task_failed and current_run_successful_tasks > 0:
        total_successful_days += current_run_successful_tasks
        save_status(total_successful_days)
        
        total_reward_days = 3 * total_successful_days
        total_reward_minutes = 65 * total_successful_days
        hours, minutes = divmod(total_reward_minutes, 60)
        total_reward_time = f"{hours}小时{minutes}分钟"

        logger.info("************************************************")
        logger.info("*************** 获得3天VIP，65分钟时长 ***************")
        logger.info(f"*** 成功签到{total_successful_days}天，累计获得{total_reward_days}天VIP，{total_reward_time}时长 ***")
        logger.info("************************************************")
    elif any_task_failed:
        logger.warning("一个或多个任务执行失败或未完全成功，请检查以上日志获取详细信息。")
        logger.info(f"本次运行前已累计成功签到 {total_successful_days} 天，本次运行未增加天数。")
    else:
        logger.info("本次运行没有成功完成任何任务。")


    logger.info(f"================ 自动化任务结束 (总耗时: {total_duration:.2f} 秒) ================")


if __name__ == "__main__":
    main()
