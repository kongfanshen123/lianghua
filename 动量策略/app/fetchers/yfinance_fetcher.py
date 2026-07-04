from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
import logging
import yfinance as yf
from .base_fetcher import BaseFetcher, FetcherResult

logger = logging.getLogger(__name__)


class YFinanceFetcher(BaseFetcher):
    def __init__(self, request_interval: float = 1.0, max_retry: int = 3, retry_delay: int = 10):
        super().__init__(request_interval, max_retry, retry_delay)
        self.data_source = "yfinance"

    def fetch_daily_price(self, symbol: str, trade_date: Optional[date] = None) -> FetcherResult:
        result = FetcherResult()
        result.data_source = self.data_source

        if trade_date is None:
            trade_date = date.today()

        try:
            start_date = trade_date.strftime("%Y-%m-%d")
            end_date = (trade_date + timedelta(days=1)).strftime("%Y-%m-%d")

            df = yf.download(symbol, start=start_date, end=end_date, auto_adjust=True)

            if df is None or df.empty:
                result.success = False
                result.error_message = f"No data found for {symbol} on {trade_date}"
                return result

            result.data = self._df_to_dict(df)
            result.success = True
            return result

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"YFinance fetch_daily_price failed for {symbol}: {e}")
            return result

    def fetch_price_history(self, symbol: str, start_date: date, end_date: date) -> FetcherResult:
        result = FetcherResult()
        result.data_source = self.data_source

        try:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")

            df = yf.download(symbol, start=start_str, end=end_str, auto_adjust=True)

            if df is None or df.empty:
                result.success = False
                result.error_message = f"No data found for {symbol} from {start_date} to {end_date}"
                return result

            result.data = self._df_to_dict(df)
            result.success = True
            return result

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"YFinance fetch_price_history failed for {symbol}: {e}")
            return result

    def _df_to_dict(self, df) -> List[Dict]:
        data = []
        for idx, row in df.iterrows():
            data.append({
                "trade_date": idx.strftime("%Y-%m-%d"),
                "close_price": float(row.get("Close", 0)),
                "open_price": float(row.get("Open", 0)),
                "high_price": float(row.get("High", 0)),
                "low_price": float(row.get("Low", 0)),
                "volume": int(row.get("Volume", 0)),
                "amount": 0.0,
                "adjusted_factor": 1.0,
                "is_suspended": 0,
                "is_ex_dividend": 0,
            })
        return data
