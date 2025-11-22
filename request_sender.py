import requests
import time
from logger_setup import logger

def send_request(request_details):
    """
    根据提供的请求详情发送HTTP请求。

    :param request_details: 包含'method', 'url', 'headers', 'post_data'的字典。
    :return: 成功时返回True，失败时返回False。
    """
    method = request_details['method'].upper()
    url = request_details['url']
    headers = request_details['headers']
    data = request_details['post_data']

    try:
        # 根据请求方法发送请求
        if method == 'POST':
            if isinstance(data, dict):
                response = requests.post(url, headers=headers, json=data, timeout=10)
            else:
                response = requests.post(url, headers=headers, data=data, timeout=10)
        elif method == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        else:
            logger.error(f"不支持的HTTP方法: {method}")
            return False

        # 检查响应状态码
        if response.status_code == 200:
            logger.info(f"请求成功: {method} {url} - 状态码: {response.status_code}")
            # 尝试打印JSON响应，如果失败则打印文本
            try:
                logger.info(f"响应内容: {response.json()}")
            except ValueError:
                logger.info(f"响应内容 (非JSON): {response.text[:200]}...") # 避免日志过长
            return True
        else:
            logger.warning(f"请求失败: {method} {url} - 状态码: {response.status_code}")
            logger.warning(f"响应内容: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"发送请求时发生网络错误: {method} {url} - 错误: {e}")
        return False
    except Exception as e:
        logger.error(f"发送请求时发生未知错误: {method} {url} - 错误: {e}")
        return False
