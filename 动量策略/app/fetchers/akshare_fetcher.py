from datetime import date, datetime
from typing import List, Dict, Optional
import logging
import akshare as ak
from .base_fetcher import BaseFetcher, FetcherResult

logger = logging.getLogger(__name__)


class AkShareFetcher(BaseFetcher):
    def __init__(self, request_interval: float = 1.0, max_retry: int = 3, retry_delay: int = 10):
        super().__init__(request_interval, max_retry, retry_delay)
        self.data_source = "akshare"

    def fetch_daily_price(self, symbol: str, trade_date: Optional[date] = None) -> FetcherResult:
        result = FetcherResult()
        result.data_source = self.data_source

        if trade_date is None:
            trade_date = date.today()

        try:
            symbol_type = self._detect_symbol_type(symbol)
            df = None

            if symbol_type == "index":
                df = ak.stock_zh_index_daily_em(
                    symbol=symbol
                )
            elif symbol_type == "etf":
                df = ak.fund_etf_hist_em(
                    symbol=symbol,
                    period="daily",
                    start_date=trade_date.strftime("%Y%m%d"),
                    end_date=trade_date.strftime("%Y%m%d"),
                    adjust="qfq"
                )
            else:
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=trade_date.strftime("%Y%m%d"),
                    end_date=trade_date.strftime("%Y%m%d"),
                    adjust="qfq"
                )

            if df is None or df.empty:
                result.success = False
                result.error_message = f"No data found for {symbol} on {trade_date}"
                return result

            df = df[df['日期'] >= trade_date.strftime("%Y-%m-%d")]
            df = df[df['日期'] <= trade_date.strftime("%Y-%m-%d")]

            if df.empty:
                result.success = False
                result.error_message = f"No data found for {symbol} on {trade_date}"
                return result

            result.data = self._df_to_dict(df)
            result.success = True
            return result

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"AkShare fetch_daily_price failed for {symbol}: {e}")
            return result

    def fetch_price_history(self, symbol: str, start_date: date, end_date: date) -> FetcherResult:
        result = FetcherResult()
        result.data_source = self.data_source

        try:
            symbol_type = self._detect_symbol_type(symbol)
            df = None

            if symbol_type == "index":
                df = ak.stock_zh_index_daily_em(
                    symbol=symbol
                )
            elif symbol_type == "etf":
                df = ak.fund_etf_hist_em(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    adjust="qfq"
                )
            else:
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    adjust="qfq"
                )

            if df is None or df.empty:
                result.success = False
                result.error_message = f"No data found for {symbol} from {start_date} to {end_date}"
                return result

            df = df[df['日期'] >= start_date.strftime("%Y-%m-%d")]
            df = df[df['日期'] <= end_date.strftime("%Y-%m-%d")]

            if df.empty:
                result.success = False
                result.error_message = f"No data found for {symbol} from {start_date} to {end_date}"
                return result

            result.data = self._df_to_dict(df)
            result.success = True
            return result

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"AkShare fetch_price_history failed for {symbol}: {e}")
            return result

    def _detect_symbol_type(self, symbol: str) -> str:
        index_codes = {"000001", "000300", "399006", "000905", "000852"}
        if symbol in index_codes:
            return "index"

        etf_codes = {"510300", "159915", "588000", "510050", "510500", "159905"}
        if symbol in etf_codes:
            return "etf"

        return "stock"

    def _df_to_dict(self, df) -> List[Dict]:
        data = []
        for _, row in df.iterrows():
            data.append({
                "trade_date": self._parse_date(row.get("日期", "")),
                "close_price": float(row.get("收盘", 0)),
                "open_price": float(row.get("开盘", 0)),
                "high_price": float(row.get("最高", 0)),
                "low_price": float(row.get("最低", 0)),
                "volume": int(row.get("成交量", 0)),
                "amount": float(row.get("成交额", 0)),
                "adjusted_factor": 1.0,
                "is_suspended": 0,
                "is_ex_dividend": 0,
            })
        return data

    def _parse_date(self, date_str: str) -> str:
        if isinstance(date_str, datetime):
            return date_str.strftime("%Y-%m-%d")
        if isinstance(date_str, date):
            return date_str.strftime("%Y-%m-%d")
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
            try:
                return datetime.strptime(str(date_str), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return str(date_str)
