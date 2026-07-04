import requests
import json
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime
from .base_notifier import BaseNotifier, NotificationResult
from app.config import config

logger = logging.getLogger(__name__)


class FeishuNotifier(BaseNotifier):
    def __init__(self):
        super().__init__()
        self.app_id = config.FEISHU_APP_ID
        self.app_secret = config.FEISHU_APP_SECRET
        self.chat_id = config.FEISHU_CHAT_ID
        self.token_expire_minutes = config.FEISHU_TOKEN_EXPIRE_MINUTES
        self.webhook_url = config.FEISHU_WEBHOOK_URL
        self.token = None
        self.token_expire_time = 0

    def send(self, message: str, msg_type: str = "text") -> NotificationResult:
        result = NotificationResult()

        if msg_type == "card":
            return self.send_card({"content": message})

        if self.webhook_url:
            return self._send_via_webhook(message, "text")

        if not self.app_id or not self.app_secret or not self.chat_id:
            result.success = False
            result.error_message = "Feishu config not set"
            logger.warning("Feishu config not set, skipping notification")
            return result

        try:
            token = self._get_token()
            url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"

            payload = {
                "receive_id": self.chat_id,
                "msg_type": "text",
                "content": json.dumps({"text": message})
            }

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            if data.get("code") == 0:
                result.success = True
                result.message_id = data.get("data", {}).get("message_id", "")
            else:
                result.success = False
                result.error_message = data.get("msg", "Unknown error")

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"Feishu send failed: {e}")

        return result

    def send_card(self, card_data: Dict) -> NotificationResult:
        result = NotificationResult()

        if self.webhook_url:
            return self._send_via_webhook(card_data, "card")

        if not self.app_id or not self.app_secret or not self.chat_id:
            result.success = False
            result.error_message = "Feishu config not set"
            logger.warning("Feishu config not set, skipping notification")
            return result

        try:
            token = self._get_token()
            url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"

            card = self._build_card(card_data)

            payload = {
                "receive_id": self.chat_id,
                "msg_type": "interactive",
                "content": json.dumps(card)
            }

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            if data.get("code") == 0:
                result.success = True
                result.message_id = data.get("data", {}).get("message_id", "")
            else:
                result.success = False
                result.error_message = data.get("msg", "Unknown error")

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"Feishu send_card failed: {e}")

        return result

    def _send_via_webhook(self, content: Dict or str, msg_type: str = "text") -> NotificationResult:
        result = NotificationResult()

        try:
            if msg_type == "card":
                card = self._build_card(content)
                payload = {
                    "msg_type": "interactive",
                    "card": card
                }
            else:
                payload = {
                    "msg_type": "text",
                    "content": {"text": content}
                }

            headers = {
                "Content-Type": "application/json; charset=utf-8"
            }

            response = requests.post(self.webhook_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            if data.get("StatusCode") == 0:
                result.success = True
                result.message_id = data.get("StatusMessage", "")
            else:
                result.success = False
                result.error_message = data.get("StatusMessage", "Unknown error")

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"Feishu webhook send failed: {e}")

        return result

    def _get_token(self) -> str:
        now = time.time()
        if self.token and now < self.token_expire_time:
            return self.token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"

        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 0:
                self.token = data.get("tenant_access_token", "")
                expire = data.get("expire", 7200)
                self.token_expire_time = now + expire - 600
                return self.token
            else:
                raise Exception(f"Token request failed: {data.get('msg')}")

        except Exception as e:
            logger.error(f"Failed to get Feishu token: {e}")
            raise

    def _build_card(self, card_data: Dict) -> Dict:
        trade_date = card_data.get("trade_date", datetime.now().strftime("%Y-%m-%d"))
        strong_stocks = card_data.get("strong_stocks", [])
        weak_stocks = card_data.get("weak_stocks", [])
        total_count = card_data.get("total_count", 0)
        abnormal_count = card_data.get("abnormal_count", 0)

        card = {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📊 每日动量策略报告"
                },
                "template": "blue"
            },
            "elements": []
        }

        card["elements"].append({
            "tag": "div",
            "text": {
                "tag": "plain_text",
                "content": f"📅 {trade_date} | 📈 有效标的：{total_count}只 | ⚠️ 异常：{abnormal_count}只"
            }
        })

        card["elements"].append({"tag": "hr"})

        card["elements"].append({
            "tag": "div",
            "text": {
                "tag": "plain_text",
                "content": "🏆 强势标的TOP5"
            }
        })

        for stock in strong_stocks:
            change_icon = "→"
            if stock.get("ranking_change", 0) > 0:
                change_icon = f"↑{stock['ranking_change']}"
            elif stock.get("ranking_change", 0) < 0:
                change_icon = f"↓{abs(stock['ranking_change'])}"

            card["elements"].append({
                "tag": "div",
                "fields": [
                    {
                        "text": {
                            "tag": "plain_text",
                            "content": f"{stock.get('name', '')} ({stock.get('symbol', '')})"
                        }
                    },
                    {
                        "text": {
                            "tag": "plain_text",
                            "content": f"动量: {stock.get('momentum_20d', 0):+.2f}%"
                        }
                    },
                    {
                        "text": {
                            "tag": "plain_text",
                            "content": f"趋势: {stock.get('trend_strength', '')}"
                        }
                    },
                    {
                        "text": {
                            "tag": "plain_text",
                            "content": f"排名: {change_icon}"
                        }
                    }
                ]
            })

        card["elements"].append({"tag": "hr"})

        card["elements"].append({
            "tag": "div",
            "text": {
                "tag": "plain_text",
                "content": "📉 弱势标的TOP5"
            }
        })

        for stock in weak_stocks:
            change_icon = "→"
            if stock.get("ranking_change", 0) > 0:
                change_icon = f"↑{stock['ranking_change']}"
            elif stock.get("ranking_change", 0) < 0:
                change_icon = f"↓{abs(stock['ranking_change'])}"

            card["elements"].append({
                "tag": "div",
                "fields": [
                    {
                        "text": {
                            "tag": "plain_text",
                            "content": f"{stock.get('name', '')} ({stock.get('symbol', '')})"
                        }
                    },
                    {
                        "text": {
                            "tag": "plain_text",
                            "content": f"动量: {stock.get('momentum_20d', 0):+.2f}%"
                        }
                    },
                    {
                        "text": {
                            "tag": "plain_text",
                            "content": f"趋势: {stock.get('trend_strength', '')}"
                        }
                    },
                    {
                        "text": {
                            "tag": "plain_text",
                            "content": f"排名: {change_icon}"
                        }
                    }
                ]
            })

        card["elements"].append({"tag": "hr"})

        card["elements"].append({
            "tag": "div",
            "text": {
                "tag": "plain_text",
                "content": "💡 策略说明：基于20日动量策略计算，采用前复权价格"
            }
        })

        card["elements"].append({
            "tag": "div",
            "text": {
                "tag": "plain_text",
                "content": "⚠️ 免责声明：本报告仅供参考，不构成投资建议"
            }
        })

        return card
