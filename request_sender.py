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
    post_data = request_details['post_data']

    parsed_url = urlparse(url)
    host = parsed_url.netloc
    path = parsed_url.path + ('?' + parsed_url.query if parsed_url.query else '')
    
    # 确定连接类型 (HTTP vs HTTPS)
    connection_class = http.client.HTTPSConnection if parsed_url.scheme == 'https' else http.client.HTTPConnection
    
    body = None
    if post_data:
        # 如果 post_data 是字符串并且 header 表明是 JSON，则编码为 bytes
        if isinstance(post_data, str) and 'application/json' in headers.get('Content-Type', ''):
            body = post_data.encode('utf-8')
        elif isinstance(post_data, bytes):
            body = post_data
        else:
            # 对于其他情况，例如表单数据，需要更复杂的处理，这里我们假设它是字符串
            body = str(post_data).encode('utf-8')

    conn = None
    try:
        logger.debug(f"准备发送请求: {method} {url}")
        logger.debug(f"请求头: {json.dumps(headers, indent=2)}")
        if body:
            # 尝试解码为UTF-8以进行日志记录，如果失败则记录原始字节信息
            try:
                log_data = body.decode('utf-8')
                logger.debug(f"请求体: \n{log_data}")
            except UnicodeDecodeError:
                logger.debug(f"请求体: 二进制数据, 长度: {len(body)} bytes")

        conn = connection_class(host)
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()

        logger.debug(f"收到响应: 状态码 {resp.status}")
        
        response_body = resp.read()
        
        if 200 <= resp.status < 300:
            logger.info(f"请求成功: {method} {url} - 状态码: {resp.status}")
            try:
                response_json = json.loads(response_body)
                logger.debug(f"响应内容 (JSON): \n{json.dumps(response_json, indent=2, ensure_ascii=False)}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                logger.debug(f"响应内容 (原始): {response_body.decode('utf-8', errors='ignore')}")
            return True
        else:
            logger.warning(f"请求失败: {method} {url} - 状态码: {resp.status}")
            logger.warning(f"响应内容: {response_body.decode('utf-8', errors='ignore')}")
            return False

    except (http.client.HTTPException, ConnectionError, TimeoutError) as e:
        logger.error(f"发送请求时发生网络错误: {method} {url} - 错误: {e}")
        return False
    except Exception as e:
        logger.error(f"发送请求时发生未知错误: {method} {url} - 错误: {e}", exc_info=True)
        return False
    finally:
        if conn:
            conn.close()
