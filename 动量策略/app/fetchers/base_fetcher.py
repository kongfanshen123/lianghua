from abc import ABC, abstractmethod
from datetime import date
from typing import List, Dict, Optional
import time
import logging

logger = logging.getLogger(__name__)


class FetcherResult:
    def __init__(self):
        self.success = False
        self.data: List[Dict] = []
        self.error_message: str = ""
        self.data_source: str = ""


class BaseFetcher(ABC):
    def __init__(self, request_interval: float = 1.0, max_retry: int = 3, retry_delay: int = 10):
        self.request_interval = request_interval
        self.max_retry = max_retry
        self.retry_delay = retry_delay
        self.data_source = self.__class__.__name__

    @abstractmethod
    def fetch_daily_price(self, symbol: str, trade_date: Optional[date] = None) -> FetcherResult:
        pass

    @abstractmethod
    def fetch_price_history(self, symbol: str, start_date: date, end_date: date) -> FetcherResult:
        pass

    def _retry(self, func, *args, **kwargs) -> FetcherResult:
        result = FetcherResult()
        result.data_source = self.data_source

        for attempt in range(self.max_retry):
            try:
                time.sleep(self.request_interval)
                func_result = func(*args, **kwargs)
                result.success = True
                result.data = func_result
                return result
            except Exception as e:
                error_msg = f"Attempt {attempt + 1}/{self.max_retry} failed: {str(e)}"
                logger.warning(error_msg)
                if attempt < self.max_retry - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))

        result.success = False
        result.error_message = f"All {self.max_retry} attempts failed"
        return result

    def _normalize_data(self, raw_data: List[Dict]) -> List[Dict]:
        normalized = []
        for item in raw_data:
            normalized.append({
                "trade_date": item.get("trade_date", ""),
                "close_price": item.get("close_price", 0.0),
                "open_price": item.get("open_price", 0.0),
                "high_price": item.get("high_price", 0.0),
                "low_price": item.get("low_price", 0.0),
                "volume": item.get("volume", 0),
                "amount": item.get("amount", 0.0),
                "adjusted_factor": item.get("adjusted_factor", 1.0),
                "is_suspended": item.get("is_suspended", 0),
                "is_ex_dividend": item.get("is_ex_dividend", 0),
            })
        return normalized
