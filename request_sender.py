import time
import logging
import json
import http.client
from urllib.parse import urlparse

logger = logging.getLogger('CheckinTask')

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

    parsed_url = urlparse(url)
    host = parsed_url.netloc
    path = parsed_url.path
    if parsed_url.query:
        path += '?' + parsed_url.query

    try:
        logger.debug(f"准备发送请求: {method} {url}")
        logger.debug(f"请求头: {json.dumps(headers, indent=2)}")
        if data:
            if isinstance(data, bytes):
                log_data = f"二进制数据, 长度: {len(data)} bytes"
            else:
                try:
                    log_data = json.dumps(data, indent=2, ensure_ascii=False)
                except (TypeError, ValueError):
                    log_data = str(data)
            logger.debug(f"请求体: \n{log_data}")

        conn = http.client.HTTPSConnection(host)
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()

        logger.debug(f"收到响应: 状态码 {resp.status}")
        logger.debug(f"响应头: {json.dumps(dict(resp.getheaders()), indent=2)}")

        if resp.status == 200:
            logger.info(f"请求成功: {method} {url} - 状态码: {resp.status}")
            response_body = resp.read()
            try:
                response_json = json.loads(response_body)
                logger.debug(f"响应内容 (JSON): \n{json.dumps(response_json, indent=2, ensure_ascii=False)}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                logger.debug(f"响应内容 (原始): {response_body}")
            return True
        else:
            logger.warning(f"请求失败: {method} {url} - 状态码: {resp.status}")
            logger.warning(f"响应内容: {resp.read()}")
            return False

    except Exception as e:
        logger.error(f"发送请求时发生错误: {method} {url} - 错误: {e}", exc_info=True)
        return False
    finally:
        if 'conn' in locals():
            conn.close()
