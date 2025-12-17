import time
import logging
import json
import http.client
from urllib.parse import urlparse

logger = logging.getLogger('CheckinTask')

def _merge_cookies(existing_cookies: str, new_set_cookie_headers: list[str]) -> str:
    """
    合并 Cookie 字符串。
    :param existing_cookies: 现有的 Cookie 字符串 (key=value; key2=value2)
    :param new_set_cookie_headers: 响应头中的 Set-Cookie 列表
    :return: 合并后的 Cookie 字符串
    """
    cookies = {}
    
    # 解析现有的 Cookie
    if existing_cookies:
        for item in existing_cookies.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies[key] = value
    
    # 解析 Set-Cookie 并覆盖/添加
    for header in new_set_cookie_headers:
        # Set-Cookie 格式通常是: key=value; Path=/; HttpOnly
        # 我们只需要第一部分 key=value
        parts = header.split(';')
        if parts and '=' in parts[0]:
            key, value = parts[0].strip().split('=', 1)
            cookies[key] = value
            
    # 重新组合
    return "; ".join([f"{k}={v}" for k, v in cookies.items()])

def send_request(request_details: dict, session_cookies: str = "") -> tuple[bool, str, str]:
    """
    根据提供的请求详情发送HTTP请求，支持 Cookie 保持和简单的重定向。

    :param request_details: 包含'method', 'url', 'headers', 'post_data'的字典。
    :param session_cookies: 上一次请求返回的 Cookie 字符串，用于维持会话。
    :return: (bool, str, str) 元组。
             (是否成功, 消息/响应内容, 新的Cookie字符串)
    """
    method = request_details['method'].upper()
    url = request_details['url']
    headers = request_details['headers'].copy() # 复制一份以免修改原字典
    post_data = request_details['post_data']

    # 如果有会话 Cookie，合并到请求头中
    if session_cookies:
        current_cookie = headers.get('Cookie', '')
        if current_cookie:
            # 如果请求头里本来就有 Cookie，则追加
            headers['Cookie'] = current_cookie + "; " + session_cookies
        else:
            headers['Cookie'] = session_cookies

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
        # logger.debug(f"请求头: {json.dumps(headers, indent=2)}") # 调试时可开启，注意脱敏
        
        conn = connection_class(host)
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()

        logger.debug(f"收到响应: 状态码 {resp.status}")
        
        # 处理 Set-Cookie
        # http.client 的 getheader 只返回最后一个同名头，getheaders 返回所有
        set_cookie_headers = [v for k, v in resp.getheaders() if k.lower() == 'set-cookie']
        new_cookies = _merge_cookies(session_cookies, set_cookie_headers)

        response_body = resp.read()
        
        # 处理重定向 (301, 302, 303, 307, 308)
        if resp.status in (301, 302, 303, 307, 308):
            redirect_url = resp.getheader('Location')
            if redirect_url:
                logger.info(f"检测到重定向 ({resp.status}) -> {redirect_url}")
                # 递归调用，传递更新后的 Cookie
                # 注意：这里简单处理，如果是相对路径需要拼接，这里假设是完整URL或简单路径
                if not redirect_url.startswith('http'):
                    # 简单拼接
                    redirect_url = f"{parsed_url.scheme}://{parsed_url.netloc}{redirect_url}"
                
                new_details = request_details.copy()
                new_details['url'] = redirect_url
                new_details['method'] = 'GET' # 大多数重定向转为 GET
                new_details['post_data'] = None # 重定向通常不带 Body
                
                return send_request(new_details, new_cookies)

        if 200 <= resp.status < 300:
            logger.info(f"请求成功: {method} {url} - 状态码: {resp.status}")
            try:
                response_json = json.loads(response_body)
                # logger.debug(f"响应内容 (JSON): \n{json.dumps(response_json, indent=2, ensure_ascii=False)}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
                # logger.debug(f"响应内容 (原始): {response_body.decode('utf-8', errors='ignore')}")
            return True, "OK", new_cookies
        else:
            logger.warning(f"请求失败: {method} {url} - 状态码: {resp.status}")
            logger.warning(f"响应内容: {response_body.decode('utf-8', errors='ignore')}")
            return False, f"状态码: {resp.status}", new_cookies

    except (http.client.HTTPException, ConnectionError, TimeoutError) as e:
        logger.error(f"发送请求时发生网络错误: {method} {url} - 错误: {e}")
        return False, f"网络错误: {e}", session_cookies
    except Exception as e:
        logger.error(f"发送请求时发生未知错误: {method} {url} - 错误: {e}", exc_info=True)
        return False, f"未知错误: {e}", session_cookies
    finally:
        if conn:
            conn.close()
