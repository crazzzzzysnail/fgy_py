import json
import time
import os
import concurrent.futures
from logger_setup import setup_logger
from har_parser import parse_har
from request_sender import send_request
from notify import send_notification
import config

# 初始化日志系统
logger = setup_logger()

def load_tasks() -> list[dict]:
    """
    从tasks.json加载任务列表。
    """
    try:
        with open(config.TASKS_FILE, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
        logger.info("成功加载任务配置文件。")
        return tasks
    except FileNotFoundError:
        logger.error(f"任务配置文件未找到: {config.TASKS_FILE}")
        return []
    except json.JSONDecodeError:
        logger.error(f"任务配置文件格式错误: {config.TASKS_FILE}")
        return []


def load_status() -> int:
    """
    从status.json加载状态信息，主要是成功签到天数。
    """
    try:
        with open(config.STATUS_FILE, 'r', encoding='utf-8') as f:
            status = json.load(f)
        return status.get('successful_days', 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0


def format_minutes_to_str(minutes: int) -> str:
    """将分钟数格式化为 'X小时Y分钟' 或 'Y分钟'。"""
    if minutes < 60:
        return f"{minutes}分钟"
    hours, mins = divmod(minutes, 60)
    if mins == 0:
        return f"{hours}小时"
    return f"{hours}小时{mins}分钟"


def calculate_rewards(successful_days: int) -> dict:
    """
    根据 config.REWARD_RULES 动态计算奖励。
    返回包含所有计算结果的字典。
    """
    context = {
        "days": successful_days,
        "format_minutes": format_minutes_to_str
    }
    rewards = {}
    
    # 默认规则（如果配置为空）
    rules = getattr(config, 'REWARD_RULES', {})
    
    for key, expression in rules.items():
        try:
            # 使用 eval 计算表达式，限制上下文仅为 context
            value = eval(str(expression), {"__builtins__": {}}, context)
            rewards[key] = value
            # 将计算结果也加入 context，以便后续规则引用
            context[key] = value
        except Exception as e:
            logger.error(f"计算奖励规则 '{key}' 失败: {e}")
            rewards[key] = 0
            
    return rewards

def save_status(successful_days: int, last_run_status: str, last_run_time: str = None) -> None:
    """
    将更新后的状态信息（成功签到天数、累计奖励、运行状态、时间）保存到status.json。
    """
    if last_run_time is None:
        last_run_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # 动态计算奖励
    rewards = calculate_rewards(successful_days)

    data = {
        "successful_days": successful_days,
        "last_run_status": last_run_status,
        "last_run_time": last_run_time,
        **rewards # 合并所有计算出的奖励字段
    }

    # 先写临时文件，再重命名
    temp_file = config.STATUS_FILE + '.tmp'
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno()) # 确保写入磁盘
        
        os.replace(temp_file, config.STATUS_FILE)
    except Exception as e:
        logger.error(f"保存状态文件失败: {e}")
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass


def format_duration(seconds: float) -> str:
    """将秒数格式化为 'X分Y秒' 或 'Y.YY秒'。"""
    if seconds >= 60:
        minutes, sec = divmod(int(seconds), 60)
        return f"{minutes}分{sec}秒"
    else:
        return f"{seconds:.2f}秒"


def _send_request_with_retry(task_name: str, request_details: dict, current_count: int, total_count: int, session_cookies: str = "") -> tuple[bool, str, str]:
    """
    发送单个请求，包含重试逻辑。
    返回 (True, "OK", new_cookies) 表示成功，(False, 错误信息, old_cookies) 表示失败。
    """
    max_retries = 3
    last_error_msg = "未知错误"
    
    for attempt in range(max_retries):
        success, msg, new_cookies = send_request(request_details, session_cookies)
        if success:
            return True, "OK", new_cookies
        else:
            last_error_msg = msg
            logger.warning(f"任务 '{task_name}' 第 {current_count}/{total_count} 次发送失败 (尝试 {attempt + 1}/{max_retries}): {msg}")
            if attempt < max_retries - 1:
                time.sleep(1)  # 重试前等待1秒
    
    logger.error(f"任务 '{task_name}' 第 {current_count}/{total_count} 次发送连续失败 {max_retries} 次。最后错误: {last_error_msg}")
    return False, last_error_msg, session_cookies

def run_task(task_config: dict, requests_list: list[dict]) -> dict:
    """
    执行单个任务的核心逻辑，此函数将在单独的线程中运行。
    支持多步骤请求（从 HAR 解析出的请求列表），并在步骤间保持 Cookie。
    """
    task_name = task_config.get('name', '未命名任务')
    count = task_config.get('count', 1)
    interval = task_config.get('interval_seconds', 0)
    success_msg = task_config.get('success_msg', '任务完成')
    fail_msg = task_config.get('fail_msg', '任务失败')

    task_start_time = time.time()
    logger.info(f"--- [线程开始] 任务: {task_name} ---")

    final_success = True
    final_message = success_msg
    
    # 任务级循环 (例如签到 3 次)
    for i in range(count):
        logger.info(f"任务 '{task_name}': 正在进行第 {i + 1}/{count} 轮执行。")
        
        # 每一轮任务开始前，清空 Session Cookie，确保每轮都是新的会话
        # (除非业务逻辑要求跨轮次保持，通常签到任务每轮是独立的)
        current_cookies = ""
        
        # 步骤级循环 (HAR 中的多个请求，如 登录 -> 签到)
        steps_total = len(requests_list)
        for step_idx, request_details in enumerate(requests_list):
            step_num = step_idx + 1
            
            # 如果是多步骤任务，日志显示步骤信息
            if steps_total > 1:
                logger.info(f"  -> 步骤 {step_num}/{steps_total}: {request_details['method']} {request_details['url']}")

            success, msg, new_cookies = _send_request_with_retry(
                task_name,
                request_details,
                f"{i+1}-{step_num}", # 复合计数器用于日志
                f"{count}-{steps_total}",
                current_cookies
            )
            
            # 更新 Cookie 以供下一步骤使用
            current_cookies = new_cookies

            if not success:
                final_success = False
                final_message = f"{fail_msg}: 步骤 {step_num} 失败 - {msg}"
                break  # 某个步骤失败，中止当前这一轮任务

        if not final_success:
            break # 如果某轮失败，中止整个任务配置的剩余轮次

        if i < count - 1 and interval > 0:
            logger.info(f"任务 '{task_name}': 等待 {interval} 秒...")
            time.sleep(interval)
    
    duration = time.time() - task_start_time
    logger.info(f"--- [线程结束] 任务: {task_name} 执行完毕, 耗时: {format_duration(duration)} ---")
    
    return {
        "name": task_name,
        "success": final_success,
        "duration": duration,
        "message": final_message
    }

def generate_html_report(task_results, total_duration, total_successful_days):
    """
    生成HTML格式的任务报告。
    """
    success_count = sum(1 for r in task_results if r['success'])
    fail_count = len(task_results) - success_count
    
    # 动态计算奖励并准备上下文
    rewards = calculate_rewards(total_successful_days)
    context = {
        "successful_days": total_successful_days,
        **rewards
    }
    
    # 渲染汇总信息
    summary_template = getattr(config, 'SUMMARY_TEMPLATE', "累计签到: {successful_days}天")
    try:
        summary_text = summary_template.format(**context)
    except KeyError as e:
        summary_text = f"模板渲染错误: 缺少变量 {e}"
        logger.error(summary_text)

    # 状态概览
    status_color = "#28a745" if fail_count == 0 else "#dc3545"
    status_text = "全部成功" if fail_count == 0 else f"{fail_count}个任务失败"

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; font-size: 14px; color: #333; }}
            .summary {{ margin-bottom: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 5px; border-left: 5px solid {status_color}; }}
            .summary-item {{ margin: 5px 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f2f2f2; font-weight: 600; }}
            .status-icon {{ font-size: 16px; }}
            .success {{ color: #28a745; }}
            .fail {{ color: #dc3545; font-weight: bold; }}
            .duration {{ color: #666; font-size: 12px; }}
            .message {{ font-size: 13px; }}
        </style>
    </head>
    <body>
        <div class="summary">
            <div class="summary-item"><strong>运行状态:</strong> <span style="color: {status_color}">{status_text}</span></div>
            <div class="summary-item"><strong>总耗时:</strong> {format_duration(total_duration)}</div>
            <div class="summary-item">{summary_text}</div>
        </div>
        <table>
            <thead>
                <tr>
                    <th width="25%">任务</th>
                    <th width="15%" style="text-align: center;">状态</th>
                    <th width="20%">耗时</th>
                    <th width="40%">备注</th>
                </tr>
            </thead>
            <tbody>
    """

    for res in task_results:
        icon = "✅" if res['success'] else "❌"
        msg_class = "success" if res['success'] else "fail"
        
        # 尝试对消息进行模板替换
        message = res['message']
        try:
            # 使用 format 进行替换，如果消息中包含 {} 但不是占位符则捕获异常
            if '{' in message and '}' in message:
                message = message.format(**context)
        except Exception:
            # 如果格式化失败（例如占位符不存在），则保持原样
            pass

        html += f"""
                <tr>
                    <td>{res['name']}</td>
                    <td style="text-align: center;" class="status-icon">{icon}</td>
                    <td class="duration">{format_duration(res['duration'])}</td>
                    <td class="{msg_class} message">{message}</td>
                </tr>
        """

    html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    return html

def _handle_final_notification(task_results, total_duration, total_successful_days):
    """处理最终的通知发送。"""
    any_task_failed = any(not r['success'] for r in task_results)
    
    # 确定运行状态
    run_status = "失败" if any_task_failed else "成功"

    # 如果全部成功，更新累计天数
    if not any_task_failed and task_results:
        total_successful_days += 1
        logger.info(f"*** 签到成功！累计签到 {total_successful_days} 天 ***")
    elif any_task_failed:
        logger.warning("本次运行有任务失败，不增加累计签到天数。")

    # 保存状态（无论成功失败都保存，更新时间和状态）
    save_status(total_successful_days, run_status)

    # 生成HTML报告
    html_content = generate_html_report(task_results, total_duration, total_successful_days)
    
    # 确定标题
    title = "签到任务成功" if not any_task_failed else "签到任务失败"
    
    # 发送通知
    send_notification(title, html_content, content_type=2)

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

    task_results = []

    # --- 准备并提交任务 ---
    # 限制最大并发数为 10，防止资源耗尽
    max_workers = min(len(tasks), 10)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {}
        for task in tasks:
            task_name = task.get('name', '未命名任务')
            har_file = os.path.join(config.BASE_DIR, task.get('har_file', ''))
            
            if not har_file or not os.path.exists(har_file):
                logger.error(f"任务 '{task_name}' 的HAR文件未找到或未配置: {har_file}，跳过此任务。")
                # 记录失败结果
                task_results.append({
                    "name": task_name,
                    "success": False,
                    "duration": 0,
                    "message": f"HAR文件未找到: {har_file}"
                })
                continue

            requests_list = parse_har(har_file)
            if not requests_list:
                logger.error(f"无法为任务 '{task_name}' 解析HAR文件，跳过此任务。")
                # 记录失败结果
                task_results.append({
                    "name": task_name,
                    "success": False,
                    "duration": 0,
                    "message": "HAR文件解析失败"
                })
                continue
            
            # 提交任务，传递整个 task 配置对象和请求列表
            future = executor.submit(run_task, task, requests_list)
            future_to_task[future] = task_name

        # --- 处理任务结果 ---
        for future in concurrent.futures.as_completed(future_to_task):
            task_name = future_to_task[future]
            try:
                result = future.result()
                task_results.append(result)
            except Exception as exc:
                logger.error(f"任务 '{task_name}' 在执行期间产生异常: {exc}", exc_info=config.DEBUG_MODE)
                task_results.append({
                    "name": task_name,
                    "success": False,
                    "duration": 0,
                    "message": f"执行异常: {str(exc)}"
                })

    total_duration = time.time() - overall_start_time
    logger.info(f"所有发送任务已完成。总耗时: {format_duration(total_duration)}")

    _handle_final_notification(task_results, total_duration, total_successful_days)

    logger.info(f"================ 自动化任务结束 (总耗时: {format_duration(total_duration)}) ================")



if __name__ == "__main__":
    main()
