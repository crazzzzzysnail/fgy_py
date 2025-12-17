import http.client
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

import config

# 获取在 main.py 中配置的同一个 logger 实例
logger = logging.getLogger('CheckinTask')

class NotifierBase(ABC):
    """
    通知渠道的抽象基类。
    所有具体的通知方式（如 WxPusher, Telegram 等）都应继承此类。
    """
    @abstractmethod
    def send(self, title: str, content: str, content_type: int = 2) -> None:
        """
        发送通知。
        :param title: 标题
        :param content: 内容
        :param content_type: 内容类型 (1:文字, 2:HTML, 3:Markdown)
        """
        pass

class WxPusherNotifier(NotifierBase):
    """
    WxPusher 通知实现。
    """
    def __init__(self):
        self.app_token = config.WXPUSHER_APP_TOKEN
        self.uids = config.WXPUSHER_UIDS

    def send(self, title: str, content: str, content_type: int = 2) -> None:
        if not self.app_token or not self.uids:
            # 如果未配置，静默跳过（初始化时已检查，这里作为双重保险）
            return

        # 将逗号分隔的UID字符串转换为列表
        uid_list = [uid.strip() for uid in self.uids.split(',')]

        payload = {
            "appToken": self.app_token,
            "content": content,
            "summary": title,
            "contentType": content_type,
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

class NotificationManager:
    """
    通知管理器，负责管理和调用所有已启用的通知渠道。
    """
    def __init__(self):
        self.notifiers: List[NotifierBase] = []
        self._init_notifiers()

    def _init_notifiers(self):
        # 1. 初始化 WxPusher
        if config.WXPUSHER_APP_TOKEN and config.WXPUSHER_UIDS:
            self.notifiers.append(WxPusherNotifier())
            logger.info("已启用 WxPusher 通知渠道。")
        else:
            logger.info("未配置 WxPusher，跳过初始化。")

        # 未来可以在这里添加其他通知渠道的初始化逻辑
        # if config.TELEGRAM_BOT_TOKEN: ...

    def send_all(self, title: str, content: str, content_type: int = 2) -> None:
        """
        向所有已启用的渠道发送通知。
        """
        if not self.notifiers:
            logger.warning("没有启用的通知渠道，无法发送通知。")
            return

        for notifier in self.notifiers:
            try:
                notifier.send(title, content, content_type)
            except Exception as e:
                logger.error(f"通过 {notifier.__class__.__name__} 发送通知时出错: {e}")

# 全局单例实例
_notification_manager = NotificationManager()

def send_notification(title: str, content: str, content_type: int = 2) -> None:
    """
    统一的对外接口，用于发送通知。
    """
    _notification_manager.send_all(title, content, content_type)
