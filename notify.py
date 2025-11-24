import os
import http.client
import json
import logging

import config

# 获取在 main.py 中配置的同一个 logger 实例
logger = logging.getLogger('CheckinTask')

def send_notification(title, content):
    """
    通过 WxPusher 发送通知 (使用 http.client)。
    配置从 config 模块加载。

    :param title: 通知的标题 (在 WxPusher 中用作摘要)。
    :param content: 通知的主要内容。
    """
    app_token = config.WXPUSHER_APP_TOKEN
    uids = config.WXPUSHER_UIDS

    if not app_token or not uids:
        logger.info("WXPUSHER_APP_TOKEN 或 WXPUSHER_UIDS 未配置，跳过发送通知。")
        return

    # 将逗号分隔的UID字符串转换为列表
    uid_list = [uid.strip() for uid in uids.split(',')]

    payload = {
        "appToken": app_token,
        "content": content,
        "summary": title,
        "contentType": 1,  # 1 表示纯文本
        "uids": uid_list,
    }
    
    body = json.dumps(payload).encode('utf-8')

    conn = None
    try:
        conn = http.client.HTTPConnection("wxpusher.zjiecode.com")
        headers = {'Content-Type': 'application/json'}
        conn.request("POST", "/api/send/message", body, headers)
        
        response = conn.getresponse()
        response_data = response.read().decode('utf-8')
        
        if 200 <= response.status < 300:
            result = json.loads(response_data)
            if result.get("code") == 1000:
                logger.info("WxPusher 通知已成功发送。")
            else:
                logger.error(f"WxPusher 通知发送失败: {result.get('msg', '未知错误')}")
        else:
            logger.error(f"WxPusher API 请求失败，状态码: {response.status}, 响应: {response_data}")

    except (http.client.HTTPException, ConnectionError, TimeoutError) as e:
        logger.error(f"连接到 WxPusher API 时发生网络错误: {e}")
    except json.JSONDecodeError:
        logger.error("解析 WxPusher API 响应时出错。")
    except Exception as e:
        logger.error(f"发送通知时发生未知错误: {e}")
    finally:
        if conn:
            conn.close()
