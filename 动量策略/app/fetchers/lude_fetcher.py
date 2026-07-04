import requests
import time
import logging
from datetime import date, timedelta
from typing import List, Dict, Optional
from .base_fetcher import BaseFetcher, FetcherResult

logger = logging.getLogger(__name__)


class LudeFetcher(BaseFetcher):
    BASE_URL = "https://api.lude.site/v2/quant"
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

    def __init__(self):
        super().__init__(request_interval=1, max_retry=3, retry_delay=5)
        self.data_source = "lude"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def fetch_daily_price(self, symbol: str, trade_date: Optional[date] = None) -> FetcherResult:
        result = FetcherResult()
        result.data_source = self.data_source

        if trade_date is None:
            trade_date = date.today()

        instrument_id = self._format_symbol(symbol)
        if not instrument_id:
            result.success = False
            result.error_message = f"Invalid symbol format: {symbol}"
            return result

        try:
            url = f"{self.BASE_URL}/fund/quote"
            params = {"instrument_id": instrument_id}
            response = self._request_with_retry(url, params=params)

            if response and response.status_code == 200:
                data = response.json()
                if data.get("code") == 0 and data.get("data"):
                    quote = data["data"]
                    result.data = [{
                        "trade_date": trade_date.strftime("%Y-%m-%d"),
                        "close_price": float(quote.get("close", quote.get("nav", 0))),
                        "open_price": float(quote.get("open", 0)),
                        "high_price": float(quote.get("high", 0)),
                        "low_price": float(quote.get("low", 0)),
                        "volume": int(quote.get("volume", 0)),
                        "amount": float(quote.get("amount", 0)),
                        "adjusted_factor": 1.0,
                        "is_suspended": 0,
                        "is_ex_dividend": 0,
                    }]
                    result.success = True
                else:
                    result.success = False
                    result.error_message = data.get("message", "No data")
            else:
                result.success = False
                result.error_message = f"API returned {response.status_code if response else 'no response'}"

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"Lude fetch_daily_price failed for {symbol}: {e}")

        return result

    def fetch_price_history(self, symbol: str, start_date: date, end_date: date) -> FetcherResult:
        result = FetcherResult()
        result.data_source = self.data_source

        instrument_id = self._format_symbol(symbol)
        if not instrument_id:
            result.success = False
            result.error_message = f"Invalid symbol format: {symbol}"
            return result

        try:
            url = f"{self.BASE_URL}/fund/nav-history"
            params = {
                "instrument_id": instrument_id,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            }
            response = self._request_with_retry(url, params=params)

            if response and response.status_code == 200:
                data = response.json()
                if data.get("code") == 0 and data.get("data"):
                    history = data["data"]
                    result.data = []
                    for item in history:
                        result.data.append({
                            "trade_date": item.get("date", ""),
                            "close_price": float(item.get("nav", item.get("close", 0))),
                            "open_price": float(item.get("open", 0)),
                            "high_price": float(item.get("high", 0)),
                            "low_price": float(item.get("low", 0)),
                            "volume": int(item.get("volume", 0)),
                            "amount": float(item.get("amount", 0)),
                            "adjusted_factor": 1.0,
                            "is_suspended": 0,
                            "is_ex_dividend": 0,
                        })
                    result.success = True
                else:
                    result.success = False
                    result.error_message = data.get("message", "No data")
            else:
                result.success = False
                result.error_message = f"API returned {response.status_code if response else 'no response'}"

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"Lude fetch_price_history failed for {symbol}: {e}")

        return result

    def _format_symbol(self, symbol: str) -> str:
        if "." in symbol:
            return symbol
        if symbol.startswith(("510", "511", "512", "513", "515", "516", "517", "518", "588")):
            return f"{symbol}.SH"
        if symbol.startswith(("159", "160", "161", "162", "163", "164", "165", "501")):
            return f"{symbol}.SZ"
        return ""

    def _request_with_retry(self, url: str, params: Dict = None) -> Optional[requests.Response]:
        for attempt in range(self.max_retry):
            try:
                response = self.session.get(url, params=params, timeout=30)
                if response.status_code == 401:
                    logger.warning(f"Lude API unauthorized, trying again")
                else:
                    return response
            except requests.exceptions.RequestException as e:
                logger.warning(f"Lude request attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retry - 1:
                    time.sleep(self.retry_delay)

        return None

    def get_instrument_list(self) -> List[Dict]:
        try:
            response = self.session.get(f"{self.BASE_URL}/fund/instruments", timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    return data.get("data", [])
        except Exception as e:
            logger.error(f"Lude get_instrument_list failed: {e}")
        return []
