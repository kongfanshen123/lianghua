from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class NotificationResult:
    def __init__(self):
        self.success = False
        self.message_id = ""
        self.error_message = ""


class BaseNotifier(ABC):
    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    def send(self, message: str, msg_type: str = "text") -> NotificationResult:
        pass

    @abstractmethod
    def send_card(self, card_data: Dict) -> NotificationResult:
        pass
