import json
from logger_setup import logger

def parse_har(har_file_path):
    """
    解析HAR文件，提取第一个条目中的请求信息。

    :param har_file_path: HAR文件的路径。
    :return: 包含请求信息的字典，如果解析失败则返回None。
    """
    try:
        with open(har_file_path, 'r', encoding='utf-8') as f:
            har_data = json.load(f)

        # 提取第一个HTTP事务条目
        entry = har_data['log']['entries'][0]
        request_info = entry['request']

        # 提取请求方法和URL
        method = request_info['method']
        url = request_info['url']

        # 提取请求头
        headers = {header['name']: header['value'] for header in request_info['headers']}

        # 提取请求体（如果存在）
        post_data = None
        if 'postData' in request_info:
            mime_type = request_info['postData'].get('mimeType', '')
            text = request_info['postData'].get('text', '')

            # 根据MIME类型处理请求体
            if 'application/json' in mime_type:
                try:
                    post_data = json.loads(text)
                except json.JSONDecodeError:
                    logger.error(f"无法将请求体解码为JSON: {text}")
                    post_data = text # 如果解码失败，则作为原始文本
            else:
                post_data = text
        
        logger.info(f"成功解析HAR文件: {har_file_path}")
        return {
            'method': method,
            'url': url,
            'headers': headers,
            'post_data': post_data
        }

    except FileNotFoundError:
        logger.error(f"HAR文件未找到: {har_file_path}")
        return None
    except (KeyError, IndexError) as e:
        logger.error(f"解析HAR文件时出错: {har_file_path}。无效的HAR结构: {e}")
        return None
    except Exception as e:
        logger.error(f"解析HAR文件时发生未知错误: {har_file_path}。错误: {e}")
        return None
