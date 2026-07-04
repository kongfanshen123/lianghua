import requests
import time
import logging
from datetime import date, datetime
from typing import List, Dict, Optional
from .base_fetcher import BaseFetcher, FetcherResult

logger = logging.getLogger(__name__)


class SinaFetcher(BaseFetcher):
    BASE_URL = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
    
    def __init__(self, request_interval: float = 1.0, max_retry: int = 3, retry_delay: int = 5):
        super().__init__(request_interval, max_retry, retry_delay)
        self.data_source = "sina"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "*/*",
            "Referer": "https://finance.sina.com.cn",
        })
        # Sina K线数据为不复权数据，需标记
        self.is_adjusted = False

    def fetch_daily_price(self, symbol: str, trade_date: Optional[date] = None) -> FetcherResult:
        result = FetcherResult()
        result.data_source = self.data_source

        if trade_date is None:
            trade_date = date.today()

        sina_symbol = self._format_symbol(symbol)
        if not sina_symbol:
            result.success = False
            result.error_message = f"Invalid symbol format: {symbol}"
            return result

        try:
            df = self._fetch_sina_data(sina_symbol, datalen=30)
            
            if df is None or df.empty:
                result.success = False
                result.error_message = f"No data found for {symbol}"
                return result

            target_date_str = trade_date.strftime("%Y-%m-%d")
            df_filtered = df[df['trade_date'] == target_date_str]

            if df_filtered.empty:
                result.success = False
                result.error_message = f"No data found for {symbol} on {trade_date}"
                return result

            result.data = self._df_to_dict(df_filtered)
            result.success = True
            return result

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"Sina fetch_daily_price failed for {symbol}: {e}")
            return result

    def fetch_price_history(self, symbol: str, start_date: date, end_date: date) -> FetcherResult:
        result = FetcherResult()
        result.data_source = self.data_source

        sina_symbol = self._format_symbol(symbol)
        if not sina_symbol:
            result.success = False
            result.error_message = f"Invalid symbol format: {symbol}"
            return result

        try:
            df = self._fetch_sina_data(sina_symbol, datalen=1000)
            
            if df is None or df.empty:
                result.success = False
                result.error_message = f"No data found for {symbol}"
                return result

            df_filtered = df[(df['trade_date'] >= start_date.strftime("%Y-%m-%d")) & 
                            (df['trade_date'] <= end_date.strftime("%Y-%m-%d"))]

            if df_filtered.empty:
                result.success = False
                result.error_message = f"No data found for {symbol} from {start_date} to {end_date}"
                return result

            result.data = self._df_to_dict(df_filtered)
            result.success = True
            return result

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"Sina fetch_price_history failed for {symbol}: {e}")
            return result

    def _fetch_sina_data(self, sina_symbol: str, datalen: int = 500) -> Optional:
        import pandas as pd
        
        params = {
            'symbol': sina_symbol,
            'scale': '240',
            'ma': '5,10,20',
            'datalen': str(datalen)
        }
        
        for attempt in range(self.max_retry):
            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        df = pd.DataFrame(data)
                        df['trade_date'] = df['day']
                        df['close_price'] = df['close'].astype(float)
                        df['open_price'] = df['open'].astype(float)
                        df['high_price'] = df['high'].astype(float)
                        df['low_price'] = df['low'].astype(float)
                        df['volume'] = df['volume'].astype(int)
                        df['amount'] = df['close_price'] * df['volume']
                        return df
                time.sleep(self.retry_delay)
            except requests.exceptions.RequestException as e:
                logger.warning(f"Sina request attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retry - 1:
                    time.sleep(self.retry_delay)

        return None

    def _format_symbol(self, symbol: str) -> str:
        if symbol.startswith(("sh", "sz")):
            return symbol
        
        index_codes = {"000001", "000300", "000905", "000852", "399006", "399001"}
        if symbol in index_codes:
            if symbol.startswith("0"):
                return f"sh{symbol}"
            elif symbol.startswith("3"):
                return f"sz{symbol}"
        
        if symbol.startswith(("510", "511", "512", "513", "515", "516", "517", "518", "588", "6")):
            return f"sh{symbol}"
        
        if symbol.startswith(("159", "160", "161", "162", "163", "164", "165", "501", "0")):
            return f"sz{symbol}"
        
        return ""

    def _df_to_dict(self, df) -> List[Dict]:
        data = []
        for _, row in df.iterrows():
            data.append({
                "trade_date": str(row.get("trade_date", "")),
                "close_price": float(row.get("close_price", row.get("close", 0))),
                "open_price": float(row.get("open_price", row.get("open", 0))),
                "high_price": float(row.get("high_price", row.get("high", 0))),
                "low_price": float(row.get("low_price", row.get("low", 0))),
                "volume": int(row.get("volume", 0)),
                "amount": float(row.get("amount", 0)),
                # Sina K线数据为不复权数据，adjusted_factor 固定为 1.0
                # 后续计算需注意：跨除权除息日时动量计算会失真
                "adjusted_factor": 1.0,
                "is_suspended": 0,
                "is_ex_dividend": 0,
                "data_source_note": "unadjusted",
            })
        return data

    def validate_symbol(self, symbol: str, expected_name: str = None) -> Dict:
        sina_symbol = self._format_symbol(symbol)
        if not sina_symbol:
            return {
                'valid': False,
                'real_name': '',
                'match': False,
                'error': f"Invalid symbol format: {symbol}"
            }

        try:
            url = f"https://hq.sinajs.cn/list={sina_symbol}"
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return {
                    'valid': False,
                    'real_name': '',
                    'match': False,
                    'error': f"HTTP request failed: {response.status_code}"
                }

            content = response.text
            if '=' not in content or '"' not in content:
                return {
                    'valid': False,
                    'real_name': '',
                    'match': False,
                    'error': "Cannot parse response"
                }

            data_part = content.split('=')[1].strip().strip('"')
            if not data_part:
                return {
                    'valid': False,
                    'real_name': '',
                    'match': False,
                    'error': "Empty response"
                }

            real_name = data_part.split(',')[0]
            if not real_name or real_name == 'null':
                return {
                    'valid': False,
                    'real_name': '',
                    'match': False,
                    'error': "Symbol not found"
                }

            match = True
            if expected_name:
                match = (expected_name in real_name) or (real_name in expected_name)

            return {
                'valid': True,
                'real_name': real_name,
                'match': match,
                'error': ''
            }

        except Exception as e:
            logger.error(f"Failed to validate symbol {symbol}: {e}")
            return {
                'valid': False,
                'real_name': '',
                'match': False,
                'error': str(e)
            }
