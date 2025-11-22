import json
import logging
import base64

logger = logging.getLogger('CheckinTask')

def parse_har(har_file_path):
    """
    解析HAR文件，提取第一个条目中的请求信息。

    :param har_file_path: HAR文件的路径。
    :return: 包含请求信息的字典，如果解析失败则返回None。
    """
    try:
        with open(har_file_path, 'r', encoding='utf-8') as f:
            har_data = json.load(f)

        entries_list = har_data['log']['entries']
        if not entries_list:
            logger.error(f"HAR文件 '{har_file_path}' 的 'entries' 列表为空。")
            return None
        
        first_entry = entries_list[0]
        
        request_info = first_entry['request']

        method = request_info['method']
        url = request_info['url']
        headers = {header['name']: header['value'] for header in request_info['headers']}

        post_data = None
        if 'postData' in request_info:
            post_data_info = request_info['postData']
            mime_type = post_data_info.get('mimeType', '')
            text = post_data_info.get('text', '')
            encoding = post_data_info.get('encoding', '')

            if encoding == 'base64':
                try:
                    post_data = base64.b64decode(text)
                except (ValueError, TypeError) as e:
                    logger.error(f"无法对请求体进行Base64解码: {text} - 错误: {e}")
                    post_data = text # 解码失败时回退
            elif 'application/json' in mime_type:
                try:
                    post_data = json.loads(text)
                except json.JSONDecodeError:
                    logger.error(f"无法将请求体解码为JSON: {text}")
                    post_data = text
            else:
                post_data = text
        
        request_details = {
            'method': method,
            'url': url,
            'headers': headers,
            'post_data': post_data
        }

        logger.debug(f"成功解析HAR文件: {har_file_path}")
        logger.debug(f"解析出的请求详情: {json.dumps(request_details, indent=2, ensure_ascii=False)}")
        return request_details

    except FileNotFoundError:
        logger.error(f"HAR文件未找到: {har_file_path}")
        return None
    except (KeyError, IndexError) as e:
        logger.error(f"解析HAR文件时出错: {har_file_path}。无效的HAR结构或'entries'列表为空: {e}")
        return None
    except Exception as e:
        logger.error(f"解析HAR文件时发生未知错误: {har_file_path}。错误: {e}", exc_info=True)
        return None
