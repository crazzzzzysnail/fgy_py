import json
import logging
import base64

logger = logging.getLogger('CheckinTask')

def _parse_post_data(post_data_info):
    """辅助函数，用于解析 postData 字段。"""
    mime_type = post_data_info.get('mimeType', '')
    text = post_data_info.get('text', '')
    encoding = post_data_info.get('encoding', '')

    if encoding == 'base64':
        try:
            return base64.b64decode(text)
        except (ValueError, TypeError) as e:
            logger.error(f"无法对请求体进行Base64解码: {text} - 错误: {e}")
            return text  # 解码失败时回退
    
    # 如果是JSON，则直接返回文本，让请求发送者处理序列化
    if 'application/json' in mime_type:
        return text
    
    # 如果是二进制流且没有指定编码（通常意味着是latin-1编码的字符串），尝试将其转换为bytes
    if 'application/octet-stream' in mime_type:
        try:
            # HAR文件中的二进制数据如果作为字符串存储，通常是Latin-1编码
            return text.encode('latin1')
        except UnicodeEncodeError:
            logger.warning(f"尝试将application/octet-stream数据编码为latin1失败，回退到原始文本。")
            return text
        
    return text

def parse_har(har_file_path: str) -> list[dict] | None:
    """
    解析HAR文件，提取所有有效的HTTP请求条目。

    :param har_file_path: HAR文件的路径。
    :return: 包含请求信息字典的列表，如果解析失败或无有效请求则返回None。
    """
    try:
        with open(har_file_path, 'r', encoding='utf-8') as f:
            har_data = json.load(f)

        requests_list = []
        entries = har_data.get('log', {}).get('entries', [])
        
        for entry in entries:
            request_info = entry.get('request')
            if not request_info:
                continue

            # 提取核心请求信息
            method = request_info.get('method')
            url = request_info.get('url')
            # 过滤掉以 : 开头的伪头 (如 :method, :path 等，常见于 HTTP/2 HAR)
            headers = {
                header['name']: header['value']
                for header in request_info.get('headers', [])
                if not header['name'].startswith(':')
            }

            # 如果缺少方法或URL，则跳过此条目
            if not method or not url:
                continue

            # 忽略静态资源请求 (可选优化，防止请求图片/CSS等)
            # 这里简单过滤常见静态资源后缀
            path = url.split('?')[0].lower()
            if path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js', '.ico', '.woff', '.ttf')):
                continue

            post_data = None
            if 'postData' in request_info:
                post_data = _parse_post_data(request_info['postData'])
            
            request_details = {
                'method': method,
                'url': url,
                'headers': headers,
                'post_data': post_data
            }
            requests_list.append(request_details)

        if requests_list:
            logger.debug(f"成功从 '{har_file_path}' 解析出 {len(requests_list)} 个请求。")
            # 仅打印第一个请求作为示例，避免日志过长
            logger.debug(f"第一个请求详情: {json.dumps(requests_list[0], indent=2, ensure_ascii=False, default=lambda o: '<bytes>' if isinstance(o, bytes) else str(o))}")
            return requests_list
        else:
            logger.error(f"在HAR文件 '{har_file_path}' 中未找到有效的请求条目。")
            return None

    except FileNotFoundError:
        logger.error(f"HAR文件未找到: {har_file_path}")
        return None
    except json.JSONDecodeError:
        logger.error(f"解析HAR文件时出错: '{har_file_path}' 不是一个有效的JSON文件。")
        return None
    except Exception as e:
        logger.error(f"解析HAR文件 '{har_file_path}' 时发生未知错误: {e}", exc_info=True)
        return None
